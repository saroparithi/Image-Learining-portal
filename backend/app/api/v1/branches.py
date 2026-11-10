import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.core.database import get_db
from app.models import Branch, Organization
router = APIRouter()
BRANCHES = ["Adyar", "Alwarpet", "Anna Nagar", "T.Nagar", "Vadapalani", "Velachery", "Coimbatore", "Madurai", "Salem", "Trichy", "Calicut", "Ernakulam", "Kannur", "Thiruvananthapuram", "Ameerpet", "Indira Nagar", "Jayanagar", "Pondicherry"]
BRANCH_DETAILS = {
    "Salem": {"state": "Tamil Nadu", "city": "Salem"},
    "Adyar": {"state": "Tamil Nadu", "city": "Chennai"},
    "Coimbatore": {"state": "Tamil Nadu", "city": "Coimbatore"},
    "Madurai": {"state": "Tamil Nadu", "city": "Madurai"},
    "Calicut": {"state": "Kerala", "city": "Kozhikode"},
    "Ernakulam": {"state": "Kerala", "city": "Kochi"},
}
@router.get("")
async def list_branches(db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        result = await db.execute(select(Branch).where(Branch.status == "active").order_by(Branch.name))
        items = [{"code": branch.code, "name": branch.name, "state": branch.state or "India", "city": branch.city or branch.name, "status": branch.status} for branch in result.scalars()]
        return {"items": items, "total": len(items)}
    items = [{"code": name.upper().replace(" ", "-").replace(".", ""), "name": name, **BRANCH_DETAILS.get(name, {"state": "India", "city": name}), "status": "active"} for name in BRANCHES]
    return {"items": items, "total": len(items)}

class BranchCreate(BaseModel):
    code: str
    name: str
    state: str
    city: str

@router.post("")
async def create_branch(payload: BranchCreate, user=Depends(require_role("management")), db: AsyncSession = Depends(get_db)):
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        organization = (await db.execute(select(Organization).where(Organization.domain == "image.edu.in"))).scalar_one_or_none()
        if organization is None:
            organization = Organization(name="IMAGE Creative Education", domain="image.edu.in")
            db.add(organization)
            await db.flush()
        duplicate = (await db.execute(select(Branch).where(Branch.organization_id == organization.id, Branch.code == payload.code))).scalar_one_or_none()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Branch already exists")
        branch = Branch(organization_id=organization.id, code=payload.code, name=payload.name.strip(), state=payload.state, city=payload.city)
        db.add(branch)
        await db.commit()
        await persist_audit(db, "branch.created", "branch", user.get("sub", "unknown"), branch.name)
        record_audit("branch.created", "branch", user.get("sub", "unknown"), branch.name)
        return {"status": "created", "branch": payload.model_dump(), "created_by": user.get("sub")}
    if any(branch.lower() == payload.name.strip().lower() for branch in BRANCHES):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Branch already exists")
    BRANCHES.append(payload.name.strip())
    BRANCH_DETAILS[payload.name.strip()] = {"state": payload.state, "city": payload.city, "code": payload.code}
    record_audit("branch.created", "branch", user.get("sub", "unknown"), payload.name.strip())
    return {"status": "created", "branch": payload.model_dump(), "created_by": user.get("sub")}
