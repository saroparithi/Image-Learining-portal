import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.api.v1.notifications import NOTIFICATIONS
from app.core.database import get_db
from app.models import Batch, Branch, Course, Enrollment, Notification, User

router = APIRouter()

ENROLLMENTS = [
    {"id": "enr-1001", "student_id": "stu-1001", "student_name": "Arjun Kumar", "batch_id": "batch-salem-ux-01", "course": "Graphic & UX / UI Design", "branch": "Salem", "status": "active"},
    {"id": "enr-1002", "student_id": "stu-1002", "student_name": "Meena Raj", "batch_id": "batch-salem-vfx-01", "course": "3D Animation & VFX", "branch": "Salem", "status": "active"},
    {"id": "enr-1003", "student_id": "stu-1003", "student_name": "Vijay Anand", "batch_id": "batch-adyar-gai-01", "course": "C-TECH with Gen AI", "branch": "Adyar", "status": "active"},
]

class EnrollmentCreate(BaseModel):
    student_id: str
    batch_id: str
    course: str
    branch: str

@router.get("")
async def list_enrollments(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Enrollment, User, Batch, Course, Branch).join(User, Enrollment.student_id == User.id).join(Batch, Enrollment.batch_id == Batch.id).join(Course, Batch.course_id == Course.id).join(Branch, Batch.branch_id == Branch.id)
        if role == "student":
            try: query = query.where(Enrollment.student_id == uuid.UUID(user.get("sub", "")))
            except ValueError: query = query.where(Enrollment.id == uuid.uuid4())
        elif role in {"faculty", "branch_admin"}: query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": str(enrollment.id), "student_id": str(student.id), "student_name": student.full_name, "batch_id": str(batch.id), "course": course.name, "branch": branch.name, "status": "active"} for enrollment, student, batch, course, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    if role == "student":
        items = [item for item in ENROLLMENTS if item["student_id"] == user.get("sub", "stu-1001")]
    elif role in {"faculty", "branch_admin"}:
        items = [item for item in ENROLLMENTS if item["branch"] == user.get("branch", "Salem")]
    else:
        items = ENROLLMENTS
    return {"items": items, "total": len(items), "scope": role}

@router.post("")
async def create_enrollment(payload: EnrollmentCreate, user=Depends(require_role("branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        if user.get("role") == "branch_admin" and payload.branch != user.get("branch", "Salem"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Enrollment is outside your branch")
        try: student_id = uuid.UUID(payload.student_id); batch_id = uuid.UUID(payload.batch_id)
        except ValueError: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student or batch not found")
        student = (await db.execute(select(User).where(User.id == student_id, User.role == "student", User.status == "active"))).scalar_one_or_none()
        batch = (await db.execute(select(Batch, Branch, Course).join(Branch, Batch.branch_id == Branch.id).join(Course, Batch.course_id == Course.id).where(Batch.id == batch_id))).first()
        if student is None or batch is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student or batch not found")
        batch_row, branch_row, course_row = batch
        if branch_row.name != payload.branch or course_row.name != payload.course: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enrollment details do not match the batch")
        duplicate = (await db.execute(select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.batch_id == batch_id))).scalar_one_or_none()
        if duplicate: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student is already enrolled in this batch")
        enrollment = Enrollment(student_id=student_id, batch_id=batch_id); db.add(enrollment); db.add(Notification(user_id=student.id, title="Enrollment confirmed", message=f"You are enrolled in {course_row.name}.")); await db.commit()
        result = {"id": str(enrollment.id), "student_id": str(student.id), "student_name": student.full_name, "batch_id": str(batch_row.id), "course": course_row.name, "branch": branch_row.name, "status": "active"}
        await persist_audit(db, "enrollment.created", "enrollment", user.get("sub", "unknown"), branch_row.name)
        return {"status": "created", "enrollment": result, "created_by": user.get("sub")}
    if user.get("role") == "branch_admin" and payload.branch != user.get("branch", "Salem"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Enrollment is outside your branch")
    if any(item["student_id"] == payload.student_id and item["batch_id"] == payload.batch_id for item in ENROLLMENTS):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student is already enrolled in this batch")
    enrollment = {"id": "enr-demo-" + str(len(ENROLLMENTS) + 1), **payload.model_dump(), "student_name": payload.student_id, "status": "active"}
    ENROLLMENTS.append(enrollment)
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "Enrollment confirmed", "message": f"You are enrolled in {payload.course}.", "audience": "student", "branch": payload.branch, "read": False})
    record_audit("enrollment.created", "enrollment", user.get("sub", "unknown"), payload.branch)
    return {"status": "created", "enrollment": enrollment, "created_by": user.get("sub")}
