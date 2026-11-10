import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.core.database import get_db
from app.models import Notification, User

router = APIRouter()

NOTIFICATIONS = [
    {"id": "note-1001", "title": "Typography class reminder", "message": "Your live class starts today at 10:00 AM.", "audience": "student", "branch": "Salem", "read": False},
    {"id": "note-1002", "title": "New submission received", "message": "A student submitted Brand identity moodboard.", "audience": "faculty", "branch": "Salem", "read": False},
    {"id": "note-1003", "title": "Monthly branch report ready", "message": "Your October learning outcomes report is available.", "audience": "management", "branch": "all", "read": False},
]

class NotificationUpdate(BaseModel):
    read: bool = True

@router.get("")
async def list_notifications(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: user_id = uuid.UUID(user.get("sub", ""))
        except ValueError: return {"items": [], "unread": 0, "scope": role}
        rows = (await db.execute(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()))).scalars()
        items = [{"id": str(item.id), "title": item.title, "message": item.message, "read": item.read_at is not None} for item in rows]
        return {"items": items, "unread": sum(1 for item in items if not item["read"]), "scope": role}
    items = [item for item in NOTIFICATIONS if item["audience"] in {role, "all"} and (item["branch"] in {user.get("branch", "Salem"), "all"} or role == "management")]
    return {"items": items, "unread": sum(1 for item in items if not item["read"]), "scope": role}

@router.patch("/{notification_id}")
async def update_notification(notification_id: str, payload: NotificationUpdate, user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: item = (await db.execute(select(Notification).where(Notification.id == uuid.UUID(notification_id)))).scalar_one_or_none()
        except ValueError: item = None
        try: user_id = uuid.UUID(user.get("sub", ""))
        except ValueError: user_id = None
        if item is None or user_id is None or item.user_id != user_id: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        item.read_at = datetime.now(timezone.utc) if payload.read else None; await db.commit()
        await persist_audit(db, "notification.updated", "notification", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"id": notification_id, "read": item.read_at is not None, "updated_by": user.get("sub")}
    item = next((item for item in NOTIFICATIONS if item["id"] == notification_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    visible = item["audience"] in {role, "all"} and (item["branch"] in {user.get("branch", "Salem"), "all"} or role == "management")
    if not visible:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    item["read"] = payload.read
    record_audit("notification.updated", "notification", user.get("sub", "unknown"), item["branch"])
    return {"id": notification_id, "read": item["read"], "updated_by": user.get("sub")}
