import os
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import require_role
from app.core.database import get_db
from app.models import AuditLog, Branch, User
from app.api.v1.audit_store import AUDIT_LOGS

router = APIRouter()

@router.get("")
async def list_audit_logs(user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(AuditLog, User, Branch).join(User, AuditLog.actor_id == User.id, isouter=True).join(Branch, User.branch_id == Branch.id, isouter=True).order_by(AuditLog.created_at.desc())
        items = [{"id": str(log.id), "action": log.action, "entity_type": log.entity_type, "actor": actor.full_name if actor else "System", "branch": branch.name if branch else "all", "created_at": log.created_at.isoformat() if log.created_at else None} for log, actor, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": user.get("role")}
    return {"items": AUDIT_LOGS, "total": len(AUDIT_LOGS), "scope": user.get("role")}
