import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.core.database import get_db
from app.models import Batch, Branch, Course, User

router = APIRouter()

BATCHES = [
    {"id": "batch-salem-ux-01", "name": "Salem UX/UI 2026 A", "branch": "Salem", "course": "Graphic & UX / UI Design", "academic_year": "2026", "faculty": "Priya Menon", "students": 28},
    {"id": "batch-salem-vfx-01", "name": "Salem 3D/VFX 2026 A", "branch": "Salem", "course": "3D Animation & VFX", "academic_year": "2026", "faculty": "Karthik Dev", "students": 24},
    {"id": "batch-adyar-gai-01", "name": "Adyar C-TECH 2026 A", "branch": "Adyar", "course": "C-TECH with Gen AI", "academic_year": "2026", "faculty": "Nisha Rao", "students": 31},
]

class BatchCreate(BaseModel):
    name: str
    branch: str
    course: str
    academic_year: str
    faculty: str

@router.get("")
async def list_batches(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Batch, Branch, Course, User).join(Branch, Batch.branch_id == Branch.id).join(Course, Batch.course_id == Course.id).join(User, Batch.faculty_id == User.id, isouter=True).order_by(Batch.name)
        if role != "management": query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"id": batch.id, "name": batch.name, "branch": branch.name, "course": course.name, "academic_year": batch.academic_year, "faculty": faculty.full_name if faculty else "", "students": 0} for batch, branch, course, faculty in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    items = BATCHES if role == "management" else [batch for batch in BATCHES if batch["branch"] == user.get("branch", "Salem")]
    return {"items": items, "total": len(items), "scope": role}

@router.post("")
async def create_batch(payload: BatchCreate, user=Depends(require_role("branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        branch = (await db.execute(select(Branch).where(Branch.name == payload.branch))).scalar_one_or_none()
        course = (await db.execute(select(Course).where(Course.name == payload.course))).scalar_one_or_none()
        if branch is None or course is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch or course not found")
        faculty = (await db.execute(select(User).where(User.full_name == payload.faculty, User.role == "faculty"))).scalar_one_or_none()
        duplicate = (await db.execute(select(Batch).where(Batch.branch_id == branch.id, Batch.name == payload.name))).scalar_one_or_none()
        if duplicate: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Batch already exists for this branch")
        batch = Batch(branch_id=branch.id, course_id=course.id, name=payload.name.strip(), academic_year=payload.academic_year, faculty_id=faculty.id if faculty else None)
        db.add(batch); await db.commit()
        await persist_audit(db, "batch.created", "batch", user.get("sub", "unknown"), branch.name)
        return {"status": "created", "batch": {"id": str(batch.id), **payload.model_dump()}, "created_by": user.get("sub")}
    if any(batch["name"].lower() == payload.name.strip().lower() and batch["branch"].lower() == payload.branch.strip().lower() for batch in BATCHES):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Batch already exists for this branch")
    batch = {"id": "batch-demo-" + str(len(BATCHES) + 1), **payload.model_dump()}
    BATCHES.append(batch)
    record_audit("batch.created", "batch", user.get("sub", "unknown"), batch["branch"])
    return {"status": "created", "batch": batch, "created_by": user.get("sub")}
