from datetime import datetime, timezone
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.api.v1.notifications import NOTIFICATIONS
from app.core.database import get_db
from app.models import Branch, Course, Exam, ExamAttempt, Notification, User

router = APIRouter()

EXAMS = [
    {"id": "exam-1001", "title": "Typography fundamentals quiz", "course": "Graphic & UX / UI Design", "branch": "Salem", "questions": 20, "status": "open"},
    {"id": "exam-1002", "title": "3D modelling skills check", "course": "3D Animation & VFX", "branch": "Adyar", "questions": 25, "status": "scheduled"},
]
ATTEMPTS = []

class ExamAttempt(BaseModel):
    exam_id: str
    answers: dict[str, str]

class ExamCreate(BaseModel):
    title: str
    course: str
    branch: str
    total_marks: float = 100
    status: str = "draft"

class ExamUpdate(BaseModel):
    status: str

@router.patch("/{exam_id}")
async def update_exam(exam_id: str, payload: ExamUpdate, user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if payload.status not in {"draft", "open", "scheduled", "published", "archived"}:
        raise HTTPException(status_code=422, detail="Unsupported exam status")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: exam = (await db.execute(select(Exam).where(Exam.id == uuid.UUID(exam_id)))).scalar_one_or_none()
        except ValueError: exam = None
        if exam is None: raise HTTPException(status_code=404, detail="Exam not found")
        was_available = exam.status in {"open", "published"}
        exam.status = payload.status
        if payload.status in {"open", "published"} and not was_available:
            student_ids = (await db.execute(select(User.id).where(User.role == "student", User.branch_id == exam.branch_id))).scalars().all()
            for student_id in student_ids:
                db.add(Notification(user_id=student_id, title="Exam available", message=f"{exam.title} is now available for your branch."))
        await db.commit()
        await persist_audit(db, "exam.status_updated", "exam", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": payload.status, "exam": {"id": str(exam.id), "title": exam.title, "status": exam.status}}
    exam = next((item for item in EXAMS if item["id"] == exam_id), None)
    if exam is None: raise HTTPException(status_code=404, detail="Exam not found")
    was_available = exam["status"] in {"open", "published"}
    exam["status"] = payload.status
    if payload.status in {"open", "published"} and not was_available:
        NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "Exam available", "message": f"{exam['title']} is now available for your branch.", "audience": "student", "branch": exam["branch"], "read": False})
    record_audit("exam.status_updated", "exam", user.get("sub", "unknown"), exam["branch"])
    return {"status": payload.status, "exam": exam}

@router.post("")
async def create_exam(payload: ExamCreate, user=Depends(require_role("faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if payload.total_marks <= 0 or payload.status not in {"draft", "open", "scheduled", "published"}:
        raise HTTPException(status_code=422, detail="Invalid exam configuration")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        course = (await db.execute(select(Course).where(Course.name == payload.course))).scalar_one_or_none()
        branch = (await db.execute(select(Branch).where(Branch.name == payload.branch))).scalar_one_or_none()
        if course is None or branch is None: raise HTTPException(status_code=404, detail="Course or branch not found")
        if user.get("role") != "management" and payload.branch != user.get("branch", "Salem"): raise HTTPException(status_code=403, detail="Exam is outside your branch")
        exam = Exam(course_id=course.id, branch_id=branch.id, title=payload.title.strip(), total_marks=payload.total_marks, status=payload.status)
        db.add(exam); await db.commit()
        await persist_audit(db, "exam.created", "exam", user.get("sub", "unknown"), payload.branch)
        return {"status": "created", "exam": {"id": str(exam.id), "title": exam.title, "course": course.name, "branch": branch.name, "total_marks": float(exam.total_marks), "status": exam.status}}
    if user.get("role") != "management" and payload.branch != user.get("branch", "Salem"): raise HTTPException(status_code=403, detail="Exam is outside your branch")
    exam = {"id": "exam-demo-" + str(len(EXAMS) + 1), "title": payload.title.strip(), "course": payload.course, "branch": payload.branch, "questions": 0, "status": payload.status, "total_marks": payload.total_marks}
    EXAMS.append(exam); record_audit("exam.created", "exam", user.get("sub", "unknown"), payload.branch)
    return {"status": "created", "exam": exam}

@router.get("")
async def list_exams(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        visible_statuses = ["draft", "published", "open", "scheduled"] if role == "management" else ["published", "open", "scheduled"]
        query = select(Exam, Course, Branch).join(Course, Exam.course_id == Course.id, isouter=True).join(Branch, Exam.branch_id == Branch.id, isouter=True).where(Exam.status.in_(visible_statuses))
        if role != "management": query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": str(exam.id), "title": exam.title, "course": course.name if course else "", "branch": branch.name if branch else "", "questions": 0, "total_marks": float(exam.total_marks), "status": exam.status} for exam, course, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    items = EXAMS if role == "management" else [exam for exam in EXAMS if exam["branch"] == user.get("branch", "Salem")]
    items = [{**exam, "total_marks": exam.get("total_marks", 100)} for exam in items]
    return {"items": items, "total": len(items), "scope": role}

@router.post("/attempts")
async def submit_attempt(payload: ExamAttempt, user=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: exam_id = uuid.UUID(payload.exam_id); student_id = uuid.UUID(user.get("sub", ""))
        except ValueError: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        exam = (await db.execute(select(Exam).where(Exam.id == exam_id, Exam.status.in_(["published", "open", "scheduled"])))).scalar_one_or_none()
        if exam is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        attempt = ExamAttempt(exam_id=exam.id, student_id=student_id)
        db.add(attempt)
        student_branch = (await db.execute(select(User.branch_id).where(User.id == student_id))).scalar_one_or_none()
        if student_branch:
            faculty_ids = (await db.execute(select(User.id).where(User.role == "faculty", User.branch_id == student_branch))).scalars().all()
            for faculty_id in faculty_ids:
                db.add(Notification(user_id=faculty_id, title="Exam attempt submitted", message=f"A student submitted an attempt for {exam.title}."))
        db.add(Notification(user_id=student_id, title="Exam attempt received", message=f"Your attempt for {exam.title} was submitted successfully."))
        try: await db.commit()
        except IntegrityError:
            await db.rollback(); raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt already submitted")
        await persist_audit(db, "exam.attempt.created", "exam_attempt", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"id": str(attempt.id), "exam_id": str(attempt.exam_id), "student_id": str(attempt.student_id), "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None, "answer_count": len(payload.answers), "status": "submitted"}
    exam = next((item for item in EXAMS if item["id"] == payload.exam_id and item["branch"] == user.get("branch", "Salem")), None)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    attempt = {"id": "attempt-demo-" + str(len(ATTEMPTS) + 1), "exam_id": payload.exam_id, "student_id": user.get("sub"), "branch": exam["branch"], "submitted_at": datetime.now(timezone.utc).isoformat(), "answer_count": len(payload.answers), "status": "submitted"}
    ATTEMPTS.append(attempt)
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "Exam attempt submitted", "message": f"A student submitted an attempt for {exam['title']}.", "audience": "faculty", "branch": exam["branch"], "read": False})
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "Exam attempt received", "message": f"Your attempt for {exam['title']} was submitted successfully.", "audience": "student", "branch": exam["branch"], "read": False})
    record_audit("exam.attempt.created", "exam_attempt", user.get("sub", "unknown"), exam["branch"])
    return attempt

@router.get("/attempts")
async def list_attempts(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(ExamAttempt).join(Exam, ExamAttempt.exam_id == Exam.id)
        if role == "student":
            try: query = query.where(ExamAttempt.student_id == uuid.UUID(user.get("sub", "")))
            except ValueError: query = query.where(ExamAttempt.id == uuid.uuid4())
        elif role != "management":
            query = query.join(Branch, Exam.branch_id == Branch.id).where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": str(item.id), "exam_id": str(item.exam_id), "student_id": str(item.student_id), "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None, "status": "submitted"} for item in (await db.execute(query)).scalars()]
        return {"items": items, "total": len(items), "scope": role}
    if role == "student":
        items = [item for item in ATTEMPTS if item["student_id"] == user.get("sub")]
    elif role == "management":
        items = ATTEMPTS
    else:
        items = [item for item in ATTEMPTS if item["branch"] == user.get("branch", "Salem")]
    return {"items": items, "total": len(items), "scope": role}
