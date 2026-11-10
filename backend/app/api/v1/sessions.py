import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.core.database import get_db
from app.models import Batch, Branch, Course, Notification, Session, User
from app.api.v1.notifications import NOTIFICATIONS

router = APIRouter()

SESSIONS = [
    {"id": "session-1001", "title": "Typography fundamentals", "course": "Graphic & UX / UI Design", "branch": "Salem", "starts_at": "2026-11-05T10:00:00+05:30", "duration_minutes": 90, "type": "live_class", "faculty": "Priya Menon"},
    {"id": "session-1002", "title": "Portfolio review: Brand identity", "course": "Graphic & UX / UI Design", "branch": "Salem", "starts_at": "2026-11-06T14:00:00+05:30", "duration_minutes": 60, "type": "mentor_session", "faculty": "Priya Menon"},
    {"id": "session-1003", "title": "Introduction to 3D modelling", "course": "3D Animation & VFX", "branch": "Salem", "starts_at": "2026-11-08T11:00:00+05:30", "duration_minutes": 120, "type": "workshop", "faculty": "Karthik Dev"},
]

class SessionCreate(BaseModel):
    title: str
    course: str
    starts_at: str
    duration_minutes: int
    type: str
    faculty: str

@router.get("")
async def list_sessions(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Session, Branch, Course, User).join(Branch, Session.branch_id == Branch.id, isouter=True).join(Batch, Session.batch_id == Batch.id, isouter=True).join(Course, Batch.course_id == Course.id, isouter=True).join(User, Session.host_id == User.id, isouter=True)
        if role != "management": query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": str(item.id), "title": item.title, "course": course.name if course else "", "branch": branch.name if branch else "", "starts_at": item.starts_at.isoformat(), "duration_minutes": item.duration_minutes, "type": item.session_type, "faculty": faculty.full_name if faculty else ""} for item, branch, course, faculty in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    items = SESSIONS if role == "management" else [session for session in SESSIONS if session["branch"] == user.get("branch", "Salem")]
    return {"items": items, "total": len(items), "scope": role}

@router.post("")
async def create_session(payload: SessionCreate, user=Depends(require_role("faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if payload.duration_minutes <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Duration must be positive")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        branch = (await db.execute(select(Branch).where(Branch.name == user.get("branch", "Salem")))).scalar_one_or_none()
        course = (await db.execute(select(Course).where(Course.name == payload.course))).scalar_one_or_none()
        batch = None
        if branch and course:
            batch = (await db.execute(select(Batch).where(Batch.branch_id == branch.id, Batch.course_id == course.id).order_by(Batch.name))).scalars().first()
        creator = None
        try: creator = (await db.execute(select(User).where(User.id == user.get("sub")))).scalar_one_or_none()
        except Exception: pass
        if branch is None or course is None or batch is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch, course, or batch not found")
        try: starts_at = datetime.fromisoformat(payload.starts_at)
        except ValueError: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid session start time")
        session = Session(branch_id=branch.id, batch_id=batch.id, title=payload.title, session_type=payload.type, starts_at=starts_at, duration_minutes=payload.duration_minutes, host_id=creator.id if creator else None)
        db.add(session)
        student_ids = (await db.execute(select(User.id).where(User.role == "student", User.branch_id == branch.id))).scalars().all()
        for student_id in student_ids:
            db.add(Notification(user_id=student_id, title="New live session scheduled", message=f"{payload.title} is scheduled for {payload.starts_at}."))
        await db.commit()
        result = {"id": str(session.id), "title": session.title, "course": course.name, "branch": branch.name, "starts_at": session.starts_at.isoformat(), "duration_minutes": session.duration_minutes, "type": session.session_type, "faculty": user.get("name", "")}
        await persist_audit(db, "session.scheduled", "session", user.get("sub", "unknown"), branch.name)
        return {"status": "scheduled", "session": result, "created_by": user.get("sub")}
    session = {"id": "session-demo-" + str(len(SESSIONS) + 1), **payload.model_dump(), "branch": user.get("branch", "Salem")}
    SESSIONS.append(session)
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "New live session scheduled", "message": f"{payload.title} is scheduled for {payload.starts_at}.", "audience": "student", "branch": session["branch"], "read": False})
    record_audit("session.scheduled", "session", user.get("sub", "unknown"), session["branch"])
    return {"status": "scheduled", "session": session, "created_by": user.get("sub")}
