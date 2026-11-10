import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import hash_password, require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.core.database import get_db
from app.models import Branch, User

router = APIRouter()

STUDENTS = [
    {"id": "stu-1001", "name": "Arjun Kumar", "email": "arjun.kumar@example.test", "branch": "Salem", "course": "Graphic & UX / UI Design", "attendance": 96.8, "status": "active"},
    {"id": "stu-1002", "name": "Meena Raj", "email": "meena.raj@example.test", "branch": "Salem", "course": "3D Animation & VFX", "attendance": 91.4, "status": "active"},
    {"id": "stu-1003", "name": "Vijay Anand", "email": "vijay.anand@example.test", "branch": "Adyar", "course": "C-TECH with Gen AI", "attendance": 88.2, "status": "active"},
]

class StudentCreate(BaseModel):
    name: str
    email: str
    branch: str
    course: str

@router.post("")
async def create_student(payload: StudentCreate, user=Depends(require_role("branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        if (await db.execute(select(User).where(User.email == payload.email.strip().lower()))).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student email already exists")
        if user.get("role") == "branch_admin" and payload.branch != user.get("branch", "Salem"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student is outside your branch")
        branch = (await db.execute(select(Branch).where(Branch.name == payload.branch))).scalar_one_or_none()
        if branch is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        student = User(email=payload.email.strip().lower(), password_hash=hash_password("demo"), full_name=payload.name.strip(), role="student", branch_id=branch.id)
        db.add(student); await db.commit()
        result = {"id": str(student.id), "name": student.full_name, "email": student.email, "branch": payload.branch, "course": payload.course, "attendance": 0, "status": student.status}
        await persist_audit(db, "student.created", "student", user.get("sub", "unknown"), payload.branch)
        record_audit("student.created", "student", user.get("sub", "unknown"), payload.branch)
        return {"status": "created", "student": result, "created_by": user.get("sub")}
    if any(student["email"].lower() == payload.email.strip().lower() for student in STUDENTS):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student email already exists")
    if user.get("role") == "branch_admin" and payload.branch != user.get("branch", "Salem"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student is outside your branch")
    student = {"id": "stu-demo-" + str(len(STUDENTS) + 1), **payload.model_dump(), "attendance": 0, "status": "active"}
    STUDENTS.append(student)
    record_audit("student.created", "student", user.get("sub", "unknown"), payload.branch)
    return {"status": "created", "student": student, "created_by": user.get("sub")}

@router.get("")
async def list_students(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(User, Branch).join(Branch, User.branch_id == Branch.id, isouter=True).where(User.role == "student")
        if role == "student": query = query.where(User.email == user.get("email", ""))
        elif role in {"faculty", "branch_admin"}: query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": str(student.id), "name": student.full_name, "email": student.email, "branch": branch.name if branch else "", "course": "", "attendance": 0, "status": student.status} for student, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    if role == "student":
        items = [student for student in STUDENTS if student["id"] == "stu-1001"]
    elif role in {"faculty", "branch_admin"}:
        items = [student for student in STUDENTS if student["branch"] == user.get("branch", "Salem")]
    else:
        items = STUDENTS
    return {"items": items, "total": len(items), "scope": role}
