import os
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import Assignment, Attendance, Batch, Branch, Certificate, Course, ExamAttempt, Lesson, Resource, Session, Submission, User
from app.core.security import require_role
from app.api.v1.branches import BRANCHES
from app.api.v1.students import STUDENTS
from app.api.v1.faculty import FACULTY
from app.api.v1.attendance import ATTENDANCE
from app.api.v1.courses import COURSES
from app.api.v1.batches import BATCHES
from app.api.v1.assignments import SUBMISSIONS
from app.api.v1.exams import ATTEMPTS
from app.api.v1.certificates import CERTIFICATES
from app.api.v1.resources import RESOURCES
from app.api.v1.lessons import LESSONS
from app.api.v1.sessions import SESSIONS
from app.api.v1.assignments import ASSIGNMENTS
router = APIRouter()
@router.get("/dashboard")
async def dashboard(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres" and user.get("role") == "student":
        records = (await db.execute(select(Attendance).where(Attendance.student_id == user.get("sub")))).scalars().all()
        submissions = (await db.execute(select(Submission).where(Submission.student_id == user.get("sub"), Submission.score.is_not(None)))).scalars().all()
        attendance = round(sum(1 for item in records if item.status in {"present", "late"}) / len(records) * 100, 1) if records else 0
        average_score = round(sum(float(item.score) for item in submissions) / len(submissions), 1) if submissions else 0
        certificates = await db.execute(select(func.count()).select_from(Certificate).where(Certificate.student_id == user.get("sub")))
        completion = round(min(100, (len(submissions) + int(certificates.scalar_one())) / max(1, len(submissions) + 4) * 100), 1)
        return {"scope": "student", "attendance": attendance, "average_score": average_score, "learning_streak": 0, "lab_hours": {"completed": 0, "target": 100}, "completion": completion}
    return {"scope": user.get("role"), "attendance": 96.8, "average_score": 78.9, "learning_streak": 12, "lab_hours": {"completed": 64, "target": 100}, "completion": 72}

@router.get("/overview")
async def overview(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    summaries = {
        "student": {"active_courses": 3, "pending_assignments": 2, "upcoming_sessions": 4, "certificates": 1},
        "faculty": {"assigned_classes": 6, "pending_submissions": 14, "attendance_to_mark": 3, "resources_to_publish": 2},
        "branch_admin": {"active_students": 246, "active_faculty": 18, "active_batches": 12, "attendance_rate": 94.2},
        "management": {"active_branches": 18, "active_students": 1284, "published_courses": 4, "network_attendance": 92.8},
    }
    branch = user.get("branch", "Salem")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        async def count(model, *filters):
            query = select(func.count()).select_from(model)
            for expression in filters: query = query.where(expression)
            return int((await db.execute(query)).scalar_one())
        branch_row = (await db.execute(select(Branch).where(Branch.name == branch))).scalar_one_or_none()
        branch_id = branch_row.id if branch_row else None
        if role == "branch_admin":
            summaries[role].update({"active_students": await count(User, User.role == "student", User.status == "active", User.branch_id == branch_id), "active_faculty": await count(User, User.role == "faculty", User.status == "active", User.branch_id == branch_id), "active_batches": await count(Batch, Batch.branch_id == branch_id)})
        elif role == "student":
            summaries[role].update({"active_courses": await count(Course, Course.status == "published"), "pending_assignments": await count(Assignment), "upcoming_sessions": await count(Session, Session.branch_id == branch_id), "certificates": await count(Certificate, Certificate.student_id == user.get("sub"))})
        elif role == "faculty":
            summaries[role].update({"pending_submissions": await count(Submission), "resources_to_publish": await count(Resource, Resource.branch_id == branch_id, Resource.status == "pending_approval"), "attendance_to_mark": await count(Attendance)})
        else:
            summaries[role].update({"active_branches": await count(Branch, Branch.status == "active"), "active_students": await count(User, User.role == "student", User.status == "active"), "published_courses": await count(Course, Course.status == "published")})
        return {"scope": role, "branch": user.get("branch"), "summary": summaries[role]}
    if role == "branch_admin":
        branch_students = [student for student in STUDENTS if student["branch"] == branch and student["status"] == "active"]
        branch_faculty = [member for member in FACULTY if member["branch"] == branch and member["status"] == "active"]
        branch_batches = [batch for batch in BATCHES if batch["branch"] == branch]
        summaries[role].update({"active_students": len(branch_students), "active_faculty": len(branch_faculty), "active_batches": len(branch_batches)})
    if role == "student":
        summaries[role].update({"active_courses": sum(1 for course in COURSES if course["status"] == "published"), "pending_assignments": sum(1 for item in ASSIGNMENTS if item["branch"] == branch and item["status"] in {"due", "in_progress"}), "upcoming_sessions": sum(1 for item in SESSIONS if item["branch"] == branch), "certificates": sum(1 for item in CERTIFICATES if item["student_id"] == user.get("sub"))})
    if role == "faculty":
        branch_submissions = [item for item in SUBMISSIONS if item["branch"] == branch]
        branch_resources = [item for item in RESOURCES if item["branch"] == branch and item["status"] == "pending_approval"]
        summaries[role].update({"pending_submissions": len(branch_submissions), "resources_to_publish": len(branch_resources), "attendance_to_mark": sum(1 for item in ATTENDANCE if item["branch"] == branch and item["date"] == "2026-11-05")})
    if role == "management":
        summaries[role].update({"active_branches": len(BRANCHES), "active_students": sum(1 for student in STUDENTS if student["status"] == "active"), "published_courses": sum(1 for course in COURSES if course["status"] == "published")})
    return {"scope": role, "branch": user.get("branch"), "summary": summaries[role]}

@router.get("/branches")
async def branch_report(user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        branches = (await db.execute(select(Branch).where(Branch.status == "active").order_by(Branch.name))).scalars().all()
        items = []
        for branch in branches:
            students = await db.execute(select(func.count()).select_from(User).where(User.branch_id == branch.id, User.role == "student", User.status == "active"))
            faculty = await db.execute(select(func.count()).select_from(User).where(User.branch_id == branch.id, User.role == "faculty", User.status == "active"))
            items.append({"branch": branch.name, "students": int(students.scalar_one()), "faculty": int(faculty.scalar_one()), "status": branch.status, "city": branch.city, "state": branch.state, "code": branch.code})
        return {"items": items, "total": len(items), "scope": "management"}
    items = []
    for branch in BRANCHES:
        students = [student for student in STUDENTS if student["branch"] == branch]
        faculty = [member for member in FACULTY if member["branch"] == branch]
        items.append({"branch": branch, "students": len(students), "faculty": len(faculty), "status": "active"})
    return {"items": items, "total": len(items), "scope": "management"}

@router.get("/attendance")
async def attendance_report(user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        rows = (await db.execute(select(Attendance, Branch).join(Batch, Attendance.batch_id == Batch.id).join(Branch, Batch.branch_id == Branch.id))).all()
        by_branch = {}
        for record, branch in rows:
            summary = by_branch.setdefault(branch.name, {"branch": branch.name, "total": 0, "present": 0, "late": 0, "absent": 0})
            summary["total"] += 1
            status = record.status if record.status in {"present", "late", "absent"} else "absent"
            summary[status] += 1
        items = list(by_branch.values())
        for item in items: item["attendance_rate"] = round((item["present"] + item["late"]) / item["total"] * 100, 1) if item["total"] else 0
        return {"items": items, "total": len(items), "scope": "management"}
    by_branch = {}
    for record in ATTENDANCE:
        branch = record["branch"]
        summary = by_branch.setdefault(branch, {"branch": branch, "total": 0, "present": 0, "late": 0, "absent": 0})
        summary["total"] += 1
        status = record["status"] if record["status"] in {"present", "late", "absent"} else "absent"
        summary[status] += 1
    items = list(by_branch.values())
    for item in items:
        item["attendance_rate"] = round((item["present"] + item["late"]) / item["total"] * 100, 1) if item["total"] else 0
    return {"items": items, "total": len(items), "scope": "management"}

@router.get("/progress")
async def learner_progress(user=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    student_id = user.get("sub")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: student_uuid = uuid.UUID(student_id)
        except (ValueError, TypeError): student_uuid = None
        if student_uuid is None: return {"scope": "student", "student_id": student_id, "summary": {"submissions": 0, "exam_attempts": 0, "certificates": 0, "attendance_rate": 0, "average_score": 0, "upcoming_sessions": 0}, "submissions": [], "attempts": [], "certificates": [], "sessions": []}
        submissions = (await db.execute(select(Submission).where(Submission.student_id == student_uuid))).scalars().all()
        attempts = (await db.execute(select(ExamAttempt).where(ExamAttempt.student_id == student_uuid))).scalars().all()
        certificates = (await db.execute(select(Certificate).where(Certificate.student_id == student_uuid))).scalars().all()
        attendance = (await db.execute(select(Attendance).where(Attendance.student_id == student_uuid))).scalars().all()
        sessions = (await db.execute(select(Session, Branch).join(Branch, Session.branch_id == Branch.id, isouter=True).where(Branch.name == user.get("branch", "Salem")))).all()
        attendance_rate = round(sum(1 for item in attendance if item.status in {"present", "late"}) / len(attendance) * 100, 1) if attendance else 0
        scores = [float(item.score) for item in submissions if item.score is not None] + [float(item.score) for item in attempts if item.score is not None]
        average_score = round(sum(scores) / len(scores), 1) if scores else 0
        return {"scope": "student", "student_id": student_id, "summary": {"submissions": len(submissions), "exam_attempts": len(attempts), "certificates": len(certificates), "attendance_rate": attendance_rate, "average_score": average_score, "upcoming_sessions": len(sessions)}, "submissions": [{"id": str(item.id), "assignment_id": str(item.assignment_id), "score": float(item.score) if item.score is not None else None} for item in submissions], "attempts": [{"id": str(item.id), "exam_id": str(item.exam_id), "score": float(item.score) if item.score is not None else None} for item in attempts], "certificates": [{"id": str(item.id), "certificate_number": item.certificate_number} for item in certificates], "sessions": [{"id": str(item.id), "title": item.title, "starts_at": item.starts_at.isoformat()} for item, branch in sessions]}
    submissions = [item for item in SUBMISSIONS if item["student_id"] == student_id]
    attempts = [item for item in ATTEMPTS if item["student_id"] == student_id]
    certificates = [item for item in CERTIFICATES if item["student_id"] == student_id]
    attendance = [item for item in ATTENDANCE if item["student_id"] == student_id]
    attendance_rate = round(sum(1 for item in attendance if item["status"] in {"present", "late"}) / len(attendance) * 100, 1) if attendance else 0
    sessions = [item for item in SESSIONS if item["branch"] == user.get("branch", "Salem")]
    scores = [item["score"] for item in submissions if item.get("score") is not None] + [item["score"] for item in attempts if item.get("score") is not None]
    average_score = round(sum(scores) / len(scores), 1) if scores else 0
    return {"scope": "student", "student_id": student_id, "summary": {"submissions": len(submissions), "exam_attempts": len(attempts), "certificates": len(certificates), "attendance_rate": attendance_rate, "average_score": average_score, "upcoming_sessions": len(sessions)}, "submissions": submissions, "attempts": attempts, "certificates": certificates, "sessions": sessions}

@router.get("/quality")
async def content_quality_report(user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        async def count(model, *filters):
            query = select(func.count()).select_from(model)
            for expression in filters: query = query.where(expression)
            return int((await db.execute(query)).scalar_one())
        return {"scope": "management", "summary": {"pending_resources": await count(Resource, Resource.status == "pending_approval"), "draft_lessons": await count(Lesson, Lesson.status == "draft"), "draft_courses": await count(Course, Course.status == "draft"), "ungraded_submissions": await count(Submission, Submission.score.is_(None))}}
    return {"scope": "management", "summary": {"pending_resources": sum(1 for item in RESOURCES if item["status"] == "pending_approval"), "draft_lessons": sum(1 for item in LESSONS if not item["published"]), "draft_courses": sum(1 for item in COURSES if item["status"] == "draft"), "ungraded_submissions": sum(1 for item in SUBMISSIONS if item.get("status") == "submitted")}}
