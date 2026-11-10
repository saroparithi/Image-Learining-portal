import os
from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import hash_password, require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.api.v1.batches import BATCHES
from app.core.database import get_db
from app.models import Batch, Branch, Course, User

router = APIRouter()

FACULTY = [
    {"id": "fac-1001", "name": "Priya Menon", "email": "priya.menon@example.test", "branch": "Salem", "specialization": "Graphic & UX / UI Design", "classes": 3, "status": "active"},
    {"id": "fac-1002", "name": "Karthik Dev", "email": "karthik.dev@example.test", "branch": "Salem", "specialization": "3D Animation & VFX", "classes": 3, "status": "active"},
    {"id": "fac-1003", "name": "Nisha Rao", "email": "nisha.rao@example.test", "branch": "Adyar", "specialization": "C-TECH with Gen AI", "classes": 4, "status": "active"},
]

class FacultyCreate(BaseModel):
    name: str
    email: str
    branch: str
    specialization: str

@router.get("")
async def list_faculty(user=Depends(require_role("faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(User, Branch).join(Branch, User.branch_id == Branch.id, isouter=True).where(User.role == "faculty")
        if role != "management": query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": str(member.id), "name": member.full_name, "email": member.email, "branch": branch.name if branch else "", "specialization": "", "classes": 0, "status": member.status} for member, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    items = FACULTY if role == "management" else [member for member in FACULTY if member["branch"] == user.get("branch", "Salem")]
    return {"items": items, "total": len(items), "scope": role}

@router.get("/classes")
async def list_faculty_classes(user=Depends(require_role("faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Batch, Branch, Course, User).join(Branch, Batch.branch_id == Branch.id).join(Course, Batch.course_id == Course.id).join(User, Batch.faculty_id == User.id, isouter=True)
        if role == "faculty":
            try: query = query.where(Batch.faculty_id == uuid.UUID(user.get("sub", "")))
            except ValueError: query = query.where(Batch.id == uuid.uuid4())
        elif role == "branch_admin": query = query.where(Branch.name == user.get("branch", "Salem"))
        rows = (await db.execute(query.order_by(Batch.name))).all()
        items = [{"id": str(batch.id), "name": batch.name, "branch": branch.name, "course": course.name, "academic_year": batch.academic_year, "faculty": faculty.full_name if faculty else "", "students": 0} for batch, branch, course, faculty in rows]
        return {"items": items, "total": len(items), "scope": role}
    if role == "faculty":
        items = [batch for batch in BATCHES if batch["branch"] == user.get("branch", "Salem") and batch["faculty"] == user.get("name")]
    elif role == "branch_admin":
        items = [batch for batch in BATCHES if batch["branch"] == user.get("branch", "Salem")]
    else:
        items = BATCHES
    return {"items": items, "total": len(items), "scope": role}

@router.post("")
async def create_faculty(payload: FacultyCreate, user=Depends(require_role("branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        if (await db.execute(select(User).where(User.email == payload.email.strip().lower()))).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Faculty email already exists")
        if user.get("role") == "branch_admin" and payload.branch != user.get("branch", "Salem"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faculty is outside your branch")
        branch = (await db.execute(select(Branch).where(Branch.name == payload.branch))).scalar_one_or_none()
        if branch is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        member = User(email=payload.email.strip().lower(), password_hash=hash_password("demo"), full_name=payload.name.strip(), role="faculty", branch_id=branch.id)
        db.add(member); await db.commit()
        result = {"id": str(member.id), "name": member.full_name, "email": member.email, "branch": payload.branch, "specialization": payload.specialization, "classes": 0, "status": member.status}
        await persist_audit(db, "faculty.created", "faculty", user.get("sub", "unknown"), payload.branch)
        record_audit("faculty.created", "faculty", user.get("sub", "unknown"), payload.branch)
        return {"status": "created", "faculty": result, "created_by": user.get("sub")}
    if any(member["email"].lower() == payload.email.strip().lower() for member in FACULTY):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Faculty email already exists")
    if user.get("role") == "branch_admin" and payload.branch != user.get("branch", "Salem"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faculty is outside your branch")
    member = {"id": "fac-demo-" + str(len(FACULTY) + 1), **payload.model_dump(), "classes": 0, "status": "active"}
    FACULTY.append(member)
    record_audit("faculty.created", "faculty", user.get("sub", "unknown"), payload.branch)
    return {"status": "created", "faculty": member, "created_by": user.get("sub")}
