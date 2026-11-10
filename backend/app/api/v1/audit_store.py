from datetime import datetime, timezone
import uuid
from app.models import AuditLog

AUDIT_LOGS = [
    {"id": "audit-1001", "action": "student.enrollment.created", "entity_type": "enrollment", "actor": "Ravi Kumar", "branch": "Salem", "created_at": "2026-11-05T09:12:00+05:30"},
    {"id": "audit-1002", "action": "assignment.submission.created", "entity_type": "submission", "actor": "Arjun Kumar", "branch": "Salem", "created_at": "2026-11-04T18:41:00+05:30"},
]

def record_audit(action: str, entity_type: str, actor: str, branch: str):
    AUDIT_LOGS.append({"id": "audit-demo-" + str(len(AUDIT_LOGS) + 1), "action": action, "entity_type": entity_type, "actor": actor, "branch": branch, "created_at": datetime.now(timezone.utc).isoformat()})

async def persist_audit(db, action: str, entity_type: str, actor: str, branch: str):
    try: actor_id = uuid.UUID(actor)
    except (ValueError, TypeError): actor_id = None
    db.add(AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, metadata_json={"branch": branch}))
    await db.commit()
