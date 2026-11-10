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
from app.models import Branch, Course, Notification, Resource, User

router = APIRouter()

RESOURCES = [
    {"id": "res-1001", "title": "Typography fundamentals notes", "type": "pdf", "course": "Graphic & UX / UI Design", "branch": "Salem", "status": "published"},
    {"id": "res-1002", "title": "Brand identity studio walkthrough", "type": "video", "course": "Graphic & UX / UI Design", "branch": "Salem", "status": "published"},
    {"id": "res-1003", "title": "3D modelling reference pack", "type": "pdf", "course": "3D Animation & VFX", "branch": "Salem", "status": "published"},
]

class ResourceCreate(BaseModel):
    title: str
    type: str
    course: str
    resource_url: str

class ResourceUpdate(BaseModel):
    status: str

@router.get("")
async def list_resources(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Resource, Course, Branch).join(Course, Resource.course_id == Course.id, isouter=True).join(Branch, Resource.branch_id == Branch.id, isouter=True)
        if role != "management": query = query.where(Branch.name == user.get("branch", "Salem"))
        if role == "student": query = query.where(Resource.status == "published")
        items = [{"id": str(resource.id), "title": resource.title, "type": resource.resource_type, "course": course.name if course else "", "branch": branch.name if branch else "", "resource_url": resource.resource_url or "", "status": resource.status} for resource, course, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    items = RESOURCES if role == "management" else [item for item in RESOURCES if item["branch"] == user.get("branch", "Salem")]
    if role == "student":
        items = [item for item in items if item["status"] == "published"]
    return {"items": items, "total": len(items), "scope": role}

@router.post("")
async def publish_resource(payload: ResourceCreate, user=Depends(require_role("faculty", "branch_admin")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        branch = (await db.execute(select(Branch).where(Branch.name == user.get("branch", "Salem")))).scalar_one_or_none()
        course = (await db.execute(select(Course).where(Course.name == payload.course))).scalar_one_or_none()
        if branch is None or course is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch or course not found")
        creator = None
        try: creator = (await db.execute(select(User).where(User.id == uuid.UUID(user.get("sub", ""))))).scalar_one_or_none()
        except ValueError: pass
        resource = Resource(course_id=course.id, branch_id=branch.id, title=payload.title, resource_type=payload.type, resource_url=payload.resource_url, created_by=creator.id if creator else None)
        db.add(resource)
        management_ids = (await db.execute(select(User.id).where(User.role == "management"))).scalars().all()
        for management_id in management_ids: db.add(Notification(user_id=management_id, title="Resource awaiting approval", message=f"{payload.title} was submitted for review."))
        await db.commit()
        result = {"id": str(resource.id), "title": resource.title, "type": resource.resource_type, "course": course.name, "branch": branch.name, "resource_url": resource.resource_url, "status": resource.status}
        record_audit("resource.submitted", "resource", user.get("sub", "unknown"), branch.name)
        await persist_audit(db, "resource.submitted", "resource", user.get("sub", "unknown"), branch.name)
        return {"status": "queued_for_approval", "resource": result, "submitted_by": user.get("sub")}
    resource = {"id": "res-demo-" + str(len(RESOURCES) + 1), **payload.model_dump(), "branch": user.get("branch", "Salem"), "status": "pending_approval"}
    RESOURCES.append(resource)
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "Resource awaiting approval", "message": f"{payload.title} was submitted for review.", "audience": "management", "branch": "all", "read": False})
    record_audit("resource.submitted", "resource", user.get("sub", "unknown"), resource["branch"])
    return {"status": "queued_for_approval", "resource": resource, "submitted_by": user.get("sub")}

@router.patch("/{resource_id}")
async def update_resource(resource_id: str, payload: ResourceUpdate, user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if payload.status not in {"published", "rejected"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported resource status")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: resource = (await db.execute(select(Resource).where(Resource.id == uuid.UUID(resource_id)))).scalar_one_or_none()
        except ValueError: resource = None
        if resource is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        resource.status = payload.status
        if resource.created_by:
            db.add(Notification(user_id=resource.created_by, title=f"Resource {payload.status}", message=f"Your resource {resource.title} was {payload.status}."))
        await db.commit()
        result = {"id": str(resource.id), "title": resource.title, "type": resource.resource_type, "resource_url": resource.resource_url or "", "status": resource.status}
        record_audit("resource.status_updated", "resource", user.get("sub", "unknown"), user.get("branch", "all"))
        await persist_audit(db, "resource.status_updated", "resource", user.get("sub", "unknown"), user.get("branch", "all"))
        return {"status": payload.status, "resource": result, "updated_by": user.get("sub")}
    resource = next((item for item in RESOURCES if item["id"] == resource_id), None)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    resource["status"] = payload.status
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": f"Resource {payload.status}", "message": f"Your resource {resource['title']} was {payload.status}.", "audience": "faculty", "branch": resource["branch"], "read": False})
    record_audit("resource.status_updated", "resource", user.get("sub", "unknown"), resource["branch"])
    return {"status": payload.status, "resource": resource, "updated_by": user.get("sub")}
