import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.api.v1.notifications import NOTIFICATIONS
from app.core.database import get_db
from app.models import Course, Notification, User
router = APIRouter()
COURSES = [{"code": "CT-GAI", "name": "C-TECH with Gen AI", "category": "Professional Programme", "status": "published"}, {"code": "3D-VFX", "name": "3D Animation & VFX", "category": "Specialization", "status": "published"}, {"code": "GUX", "name": "Graphic & UX / UI Design", "category": "Specialization", "status": "published"}, {"code": "GAD", "name": "Game Art & Design", "category": "Specialization", "status": "published"}]
@router.get("")
async def list_courses(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Course).order_by(Course.name)
        if role == "student": query = query.where(Course.status == "published")
        items = [{"code": course.code, "name": course.name, "category": course.category, "description": course.description or "", "status": course.status} for course in (await db.execute(query)).scalars()]
        return {"items": items, "total": len(items), "scope": role}
    items = COURSES if role != "student" else [course for course in COURSES if course["status"] == "published"]
    return {"items": items, "total": len(items), "scope": role}

class CourseCreate(BaseModel):
    code: str
    name: str
    category: str
    description: str = ""

class CourseUpdate(BaseModel):
    status: str

@router.post("")
async def create_course(payload: CourseCreate, user=Depends(require_role("management", "branch_admin")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        if (await db.execute(select(Course).where(Course.code == payload.code))).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course code already exists")
        course = Course(code=payload.code, name=payload.name, category=payload.category, description=payload.description, status="draft")
        db.add(course); await db.commit()
        result = {"code": course.code, "name": course.name, "category": course.category, "description": course.description or "", "status": course.status}
        record_audit("course.created", "course", user.get("sub", "unknown"), user.get("branch", "all"))
        await persist_audit(db, "course.created", "course", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": "draft_created", "course": result, "created_by": user.get("sub")}
    if any(course["code"] == payload.code for course in COURSES):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course code already exists")
    course = payload.model_dump()
    course["status"] = "draft"
    COURSES.append(course)
    record_audit("course.created", "course", user.get("sub", "unknown"), user.get("branch", "all"))
    return {"status": "draft_created", "course": course, "created_by": user.get("sub")}

@router.patch("/{course_code}")
async def update_course(course_code: str, payload: CourseUpdate, user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if payload.status not in {"published", "draft", "archived"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported course status")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        course = (await db.execute(select(Course).where(Course.code == course_code))).scalar_one_or_none()
        if course is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        was_published = course.status == "published"; course.status = payload.status
        if payload.status == "published" and not was_published:
            student_ids = (await db.execute(select(User.id).where(User.role == "student"))).scalars().all()
            for student_id in student_ids: db.add(Notification(user_id=student_id, title="New course available", message=f"{course.name} is now available in your learning catalogue."))
        await db.commit()
        result = {"code": course.code, "name": course.name, "category": course.category, "description": course.description or "", "status": course.status}
        record_audit("course.status_updated", "course", user.get("sub", "unknown"), user.get("branch", "all"))
        await persist_audit(db, "course.status_updated", "course", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": payload.status, "course": result, "updated_by": user.get("sub")}
    course = next((item for item in COURSES if item["code"] == course_code), None)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    was_published = course["status"] == "published"; course["status"] = payload.status
    if payload.status == "published" and not was_published: NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "New course available", "message": f"{course['name']} is now available in your learning catalogue.", "audience": "student", "branch": "all", "read": False})
    record_audit("course.status_updated", "course", user.get("sub", "unknown"), user.get("branch", "all"))
    return {"status": payload.status, "course": course, "updated_by": user.get("sub")}
