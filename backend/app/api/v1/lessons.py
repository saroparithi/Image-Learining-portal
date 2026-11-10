import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.core.database import get_db
from app.models import Branch, Course, Lesson

router = APIRouter()

LESSONS = [
    {"id": "lesson-1001", "course": "Graphic & UX / UI Design", "module": "Design foundations", "title": "Typography fundamentals", "sequence": 1, "content_type": "video", "branch": "Salem", "published": True},
    {"id": "lesson-1002", "course": "Graphic & UX / UI Design", "module": "Brand systems", "title": "Building a visual identity", "sequence": 2, "content_type": "lesson", "branch": "Salem", "published": True},
    {"id": "lesson-1003", "course": "3D Animation & VFX", "module": "Modelling", "title": "Introduction to 3D modelling", "sequence": 1, "content_type": "video", "branch": "Salem", "published": True},
]

class LessonCreate(BaseModel):
    course: str
    module: str
    title: str
    sequence: int
    content_type: str

class LessonUpdate(BaseModel):
    published: bool

@router.get("")
async def list_lessons(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Lesson, Course).join(Course, Lesson.course_id == Course.id)
        if role == "student": query = query.where(Lesson.status == "published")
        items = [{"id": str(lesson.id), "course": course.name, "module": "", "title": lesson.title, "sequence": lesson.sequence, "content_type": lesson.content_type, "branch": user.get("branch", "Salem"), "published": lesson.status == "published"} for lesson, course in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    items = LESSONS if role == "management" else [lesson for lesson in LESSONS if lesson["branch"] == user.get("branch", "Salem")]
    if role == "student":
        items = [lesson for lesson in items if lesson["published"]]
    return {"items": items, "total": len(items), "scope": role}

@router.post("")
async def create_lesson(payload: LessonCreate, user=Depends(require_role("faculty", "branch_admin")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        course = (await db.execute(select(Course).where(Course.name == payload.course))).scalar_one_or_none()
        if course is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        lesson = Lesson(course_id=course.id, title=payload.title, sequence=payload.sequence, content_type=payload.content_type, status="draft")
        db.add(lesson); await db.commit()
        result = {"id": str(lesson.id), "course": course.name, "module": payload.module, "title": lesson.title, "sequence": lesson.sequence, "content_type": lesson.content_type, "branch": user.get("branch", "Salem"), "published": False}
        await persist_audit(db, "lesson.created", "lesson", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": "draft_created", "lesson": result, "created_by": user.get("sub")}
    lesson = {"id": "lesson-demo-" + str(len(LESSONS) + 1), **payload.model_dump(), "branch": user.get("branch", "Salem"), "published": False}
    LESSONS.append(lesson)
    record_audit("lesson.created", "lesson", user.get("sub", "unknown"), lesson["branch"])
    return {"status": "draft_created", "lesson": lesson, "created_by": user.get("sub")}

@router.patch("/{lesson_id}")
async def update_lesson(lesson_id: str, payload: LessonUpdate, user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: lesson = (await db.execute(select(Lesson).where(Lesson.id == uuid.UUID(lesson_id)))).scalar_one_or_none()
        except ValueError: lesson = None
        if lesson is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
        lesson.status = "published" if payload.published else "draft"; await db.commit()
        result = {"id": str(lesson.id), "title": lesson.title, "sequence": lesson.sequence, "content_type": lesson.content_type, "published": payload.published}
        await persist_audit(db, "lesson.status_updated", "lesson", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": "published" if payload.published else "unpublished", "lesson": result, "updated_by": user.get("sub")}
    lesson = next((item for item in LESSONS if item["id"] == lesson_id), None)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    lesson["published"] = payload.published
    record_audit("lesson.status_updated", "lesson", user.get("sub", "unknown"), lesson["branch"])
    return {"status": "published" if payload.published else "unpublished", "lesson": lesson, "updated_by": user.get("sub")}
