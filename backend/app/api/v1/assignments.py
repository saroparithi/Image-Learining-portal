from datetime import datetime, timezone
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
from app.models import Assignment, Branch, Course, Lesson, Notification, Submission as SubmissionEntity, User

router = APIRouter()

ASSIGNMENTS = [
    {"id": "asg-1001", "title": "Brand identity moodboard", "course": "Graphic & UX / UI Design", "branch": "Salem", "due_at": "2026-11-09T23:59:00+05:30", "status": "due"},
    {"id": "asg-1002", "title": "3D character blockout", "course": "3D Animation & VFX", "branch": "Salem", "due_at": "2026-11-12T23:59:00+05:30", "status": "in_progress"},
    {"id": "asg-1003", "title": "Gen AI creative workflow", "course": "C-TECH with Gen AI", "branch": "Adyar", "due_at": "2026-11-04T23:59:00+05:30", "status": "submitted"},
]
SUBMISSIONS = []

class Submission(BaseModel):
    assignment_id: str
    submission_url: str
    notes: str = ""

class SubmissionGrade(BaseModel):
    score: float
    feedback: str = ""

class AssignmentCreate(BaseModel):
    lesson_id: str
    title: str
    description: str = ""
    due_at: datetime | None = None
    max_score: float = 100

@router.post("")
async def create_assignment(payload: AssignmentCreate, user=Depends(require_role("faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if payload.max_score <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Maximum score must be positive")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: lesson_id = uuid.UUID(payload.lesson_id)
        except ValueError: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
        lesson = (await db.execute(select(Lesson).where(Lesson.id == lesson_id))).scalar_one_or_none()
        if lesson is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
        assignment = Assignment(lesson_id=lesson.id, title=payload.title.strip(), description=payload.description.strip(), due_at=payload.due_at, max_score=payload.max_score)
        db.add(assignment); await db.commit()
        creator_branch_id = (await db.execute(select(User.branch_id).where(User.id == uuid.UUID(user.get("sub", ""))))).scalar_one_or_none()
        if creator_branch_id:
            student_ids = (await db.execute(select(User.id).where(User.role == "student", User.branch_id == creator_branch_id))).scalars().all()
            for student_id in student_ids:
                db.add(Notification(user_id=student_id, title="New assignment available", message=f"{assignment.title} is ready for your learning plan."))
            await db.commit()
        await persist_audit(db, "assignment.created", "assignment", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": "created", "assignment": {"id": str(assignment.id), "lesson_id": str(lesson.id), "title": assignment.title, "description": assignment.description, "due_at": assignment.due_at.isoformat() if assignment.due_at else None, "max_score": float(assignment.max_score)}, "created_by": user.get("sub")}
    item = {"id": "asg-demo-" + str(len(ASSIGNMENTS) + 1), "title": payload.title.strip(), "course": "General", "branch": user.get("branch", "Salem"), "due_at": payload.due_at.isoformat() if payload.due_at else None, "status": "due"}
    ASSIGNMENTS.append(item)
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "New assignment available", "message": f"{item['title']} is ready for your learning plan.", "audience": "student", "branch": item["branch"], "read": False})
    record_audit("assignment.created", "assignment", user.get("sub", "unknown"), item["branch"])
    return {"status": "created", "assignment": item, "created_by": user.get("sub")}

@router.get("")
async def list_assignments(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Assignment, Lesson, Course).join(Lesson, Assignment.lesson_id == Lesson.id).join(Course, Lesson.course_id == Course.id).order_by(Assignment.due_at)
        assignments = (await db.execute(query)).all()
        submission_query = select(SubmissionEntity)
        if role == "student":
            try: submission_query = submission_query.where(SubmissionEntity.student_id == uuid.UUID(user.get("sub", "")))
            except ValueError: submission_query = submission_query.where(SubmissionEntity.id == uuid.uuid4())
        submissions = (await db.execute(submission_query)).scalars().all()
        submission_details = {str(item.assignment_id): {"status": "graded" if item.score is not None else "submitted", "score": float(item.score) if item.score is not None else None, "feedback": item.feedback or ""} for item in submissions}
        items = [{"id": str(item.id), "title": item.title, "course": course.name, "branch": user.get("branch", "Salem"), "due_at": item.due_at.isoformat() if item.due_at else None, "max_score": float(item.max_score), "status": submission_details.get(str(item.id), {}).get("status", "due"), "score": submission_details.get(str(item.id), {}).get("score"), "feedback": submission_details.get(str(item.id), {}).get("feedback", "")} for item, lesson, course in assignments]
        return {"items": items, "total": len(items), "scope": role}
    if role in {"student", "faculty", "branch_admin"}:
        items = [item for item in ASSIGNMENTS if item["branch"] == user.get("branch", "Salem")]
    else:
        items = ASSIGNMENTS
    return {"items": items, "total": len(items), "scope": role}

@router.post("/submissions")
async def submit_assignment(payload: Submission, user=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: assignment_id = uuid.UUID(payload.assignment_id); student_id = uuid.UUID(user.get("sub", ""))
        except ValueError: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
        assignment = (await db.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
        if assignment is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
        submission = SubmissionEntity(assignment_id=assignment.id, student_id=student_id, file_url=payload.submission_url)
        db.add(submission)
        student_branch = (await db.execute(select(User.branch_id).where(User.id == student_id))).scalar_one_or_none()
        if student_branch:
            faculty_ids = (await db.execute(select(User.id).where(User.role == "faculty", User.branch_id == student_branch))).scalars().all()
            for faculty_id in faculty_ids:
                db.add(Notification(user_id=faculty_id, title="New submission received", message="A student submitted work for review."))
        await db.commit()
        result = {"id": str(submission.id), "assignment_id": str(submission.assignment_id), "submission_url": submission.file_url, "student_id": str(submission.student_id), "status": "submitted", "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None}
        await persist_audit(db, "assignment.submission.created", "submission", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": "received", "submission": result}
    assignment = next((item for item in ASSIGNMENTS if item["id"] == payload.assignment_id and item["branch"] == user.get("branch", "Salem")), None)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    submission = {"id": "sub-demo-" + str(len(SUBMISSIONS) + 1), **payload.model_dump(), "student_id": user.get("sub"), "branch": assignment["branch"], "submitted_at": datetime.now(timezone.utc).isoformat(), "status": "submitted"}
    SUBMISSIONS.append(submission)
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "New submission received", "message": f"A student submitted {assignment['title']}.", "audience": "faculty", "branch": assignment["branch"], "read": False})
    record_audit("assignment.submission.created", "submission", user.get("sub", "unknown"), assignment["branch"])
    return {"status": "received", "submission": submission}

@router.get("/submissions")
async def list_submissions(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(SubmissionEntity, Assignment, User).join(Assignment, SubmissionEntity.assignment_id == Assignment.id).join(User, SubmissionEntity.student_id == User.id)
        if role == "student":
            try: query = query.where(SubmissionEntity.student_id == uuid.UUID(user.get("sub", "")))
            except ValueError: query = query.where(SubmissionEntity.id == uuid.uuid4())
        elif role != "management":
            query = query.join(Branch, User.branch_id == Branch.id).where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": str(item.id), "assignment_id": str(item.assignment_id), "submission_url": item.file_url, "student_id": str(item.student_id), "student_name": student.full_name, "score": float(item.score) if item.score is not None else None, "feedback": item.feedback or "", "status": "graded" if item.score is not None else "submitted"} for item, assignment, student in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    if role == "student":
        items = [item for item in SUBMISSIONS if item["student_id"] == user.get("sub")]
    elif role == "management":
        items = SUBMISSIONS
    else:
        items = [item for item in SUBMISSIONS if item["branch"] == user.get("branch", "Salem")]
    return {"items": items, "total": len(items), "scope": role}

@router.patch("/submissions/{submission_id}")
async def grade_submission(submission_id: str, payload: SubmissionGrade, user=Depends(require_role("faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if payload.score < 0 or payload.score > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Score must be between 0 and 100")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: submission = (await db.execute(select(SubmissionEntity).where(SubmissionEntity.id == uuid.UUID(submission_id)))).scalar_one_or_none()
        except ValueError: submission = None
        if submission is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        if user.get("role") != "management":
            student_branch = (await db.execute(select(Branch.name).join(User, User.branch_id == Branch.id).where(User.id == submission.student_id))).scalar_one_or_none()
            if student_branch != user.get("branch", "Salem"): raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        submission.score = payload.score; submission.feedback = payload.feedback; submission.graded_at = datetime.now(timezone.utc)
        db.add(Notification(user_id=submission.student_id, title="Assignment graded", message=f"Your submission received {payload.score:g}/{float((await db.execute(select(Assignment.max_score).where(Assignment.id == submission.assignment_id))).scalar_one()):g}."))
        await db.commit()
        await persist_audit(db, "assignment.submission.graded", "submission", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": "graded", "submission": {"id": str(submission.id), "assignment_id": str(submission.assignment_id), "score": float(submission.score), "feedback": submission.feedback, "status": "graded"}}
    submission = next((item for item in SUBMISSIONS if item["id"] == submission_id), None)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    if user.get("role") != "management" and submission["branch"] != user.get("branch", "Salem"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    submission.update({"score": payload.score, "feedback": payload.feedback, "status": "graded", "graded_by": user.get("sub")})
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "Assignment graded", "message": f"Your submission received {payload.score:g}/100.", "audience": "student", "branch": submission["branch"], "read": False})
    record_audit("assignment.submission.graded", "submission", user.get("sub", "unknown"), submission["branch"])
    return {"status": "graded", "submission": submission}
