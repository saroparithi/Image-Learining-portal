import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import create_access_token, current_user, verify_password
from app.core.database import get_db
from app.models import Branch, User
router = APIRouter()
class LoginRequest(BaseModel):
    identifier: str
    password: str
@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not payload.identifier.strip() or not payload.password.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifier and password are required")
    identifier = payload.identifier.lower()
    if payload.password != "demo":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    identities = {
        "student@image.edu.in": {"sub": "stu-1001", "email": "student@image.edu.in", "name": "Arjun Kumar", "role": "student", "branch": "Salem"},
        "faculty@image.edu.in": {"sub": "demo-faculty", "email": "faculty@image.edu.in", "name": "Priya Menon", "role": "faculty", "branch": "Salem"},
        "admin@image.edu.in": {"sub": "demo-admin", "email": "admin@image.edu.in", "name": "Ravi Kumar", "role": "branch_admin", "branch": "Salem"},
        "management@image.edu.in": {"sub": "demo-management", "email": "management@image.edu.in", "name": "Anitha Raj", "role": "management", "branch": "all"},
    }
    user = identities.get(identifier)
    if user is None and os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        persisted = (await db.execute(select(User, Branch).join(Branch, User.branch_id == Branch.id, isouter=True).where(User.email == identifier, User.status == "active"))).first()
        if persisted and verify_password(payload.password, persisted[0].password_hash):
            account, branch = persisted
            user = {"sub": str(account.id), "email": account.email, "name": account.full_name, "role": account.role, "branch": branch.name if branch else "all"}
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user}
@router.get("/me")
def me(user=Depends(current_user)):
    permissions = {
        "student": ["learning:read", "assignments:submit", "exams:attempt", "reports:self"],
        "faculty": ["learning:read", "classes:manage", "assignments:review", "attendance:write", "resources:publish"],
        "branch_admin": ["students:manage", "faculty:manage", "courses:manage", "attendance:write", "reports:read"],
        "management": ["branches:manage", "courses:manage", "reports:read", "audit:read"],
    }
    return {**user, "permissions": permissions.get(user.get("role"), [])}
