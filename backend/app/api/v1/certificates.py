from datetime import date
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
from app.models import Certificate, Course, Notification, User, Branch

router = APIRouter()

CERTIFICATES = [
    {"number": "IMG-SLM-2026-001", "student_id": "stu-1001", "student_name": "Arjun Kumar", "course": "Graphic & UX / UI Design", "branch": "Salem", "issued_at": "2026-10-22"},
    {"number": "IMG-SLM-2026-002", "student_id": "stu-1002", "student_name": "Meena Raj", "course": "3D Animation & VFX", "branch": "Salem", "issued_at": "2026-10-18"},
]

class CertificateCreate(BaseModel):
    student_id: str
    student_name: str
    course: str

@router.post("")
async def issue_certificate(payload: CertificateCreate, user=Depends(require_role("branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    branch = user.get("branch", "Salem")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: student_id = uuid.UUID(payload.student_id)
        except ValueError: raise HTTPException(status_code=404, detail="Student not found")
        student = (await db.execute(select(User).where(User.id == student_id, User.role == "student"))).scalar_one_or_none()
        course = (await db.execute(select(Course).where(Course.name == payload.course))).scalar_one_or_none()
        if student is None or course is None: raise HTTPException(status_code=404, detail="Student or course not found")
        if (await db.execute(select(Certificate).where(Certificate.student_id == student_id, Certificate.course_id == course.id))).scalar_one_or_none(): raise HTTPException(status_code=409, detail="Certificate already issued for this course")
        student_branch = (await db.execute(select(Branch).where(Branch.id == student.branch_id))).scalar_one_or_none()
        if user.get("role") == "branch_admin" and (student_branch is None or student_branch.name != branch): raise HTTPException(status_code=403, detail="Student is outside your branch")
        branch_name = student_branch.name if student_branch else branch
        number = f"IMG-{branch_name[:3].upper()}-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"
        certificate = Certificate(student_id=student.id, course_id=course.id, certificate_number=number)
        db.add(certificate); db.add(Notification(user_id=student.id, title="Certificate issued", message=f"Your {course.name} certificate is now available.")); await db.commit()
        result = {"number": certificate.certificate_number, "student_id": str(student.id), "student_name": student.full_name, "course": course.name, "branch": branch_name, "issued_at": certificate.issued_at.date().isoformat() if certificate.issued_at else date.today().isoformat()}
        await persist_audit(db, "certificate.issued", "certificate", user.get("sub", "unknown"), branch_name)
        return {"status": "issued", "certificate": result}
    number = f"IMG-{branch[:3].upper()}-2026-{len(CERTIFICATES) + 1:03d}"
    if any(item["student_id"] == payload.student_id and item["course"] == payload.course for item in CERTIFICATES): raise HTTPException(status_code=409, detail="Certificate already issued for this course")
    certificate = {"number": number, **payload.model_dump(), "branch": branch, "issued_at": date.today().isoformat(), "issued_by": user.get("sub")}
    CERTIFICATES.append(certificate)
    NOTIFICATIONS.append({"id": "note-demo-" + str(len(NOTIFICATIONS) + 1), "title": "Certificate issued", "message": f"Your {payload.course} certificate is now available.", "audience": "student", "branch": branch, "read": False})
    record_audit("certificate.issued", "certificate", user.get("sub", "unknown"), branch)
    return {"status": "issued", "certificate": certificate}

@router.get("")
async def list_certificates(user=Depends(require_role("student", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Certificate, User, Course, Branch).join(User, Certificate.student_id == User.id).join(Course, Certificate.course_id == Course.id).join(Branch, User.branch_id == Branch.id, isouter=True)
        if role == "student":
            try: query = query.where(User.id == uuid.UUID(user.get("sub", "")))
            except ValueError: query = query.where(Certificate.id == uuid.uuid4())
        elif role == "branch_admin": query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"number": certificate.certificate_number, "student_id": str(student.id), "student_name": student.full_name, "course": course.name, "branch": branch.name if branch else "", "issued_at": certificate.issued_at.date().isoformat() if certificate.issued_at else ""} for certificate, student, course, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    if role == "student":
        items = [item for item in CERTIFICATES if item["student_id"] == user.get("sub", "stu-1001")]
    elif role == "branch_admin":
        items = [item for item in CERTIFICATES if item["branch"] == user.get("branch", "Salem")]
    else:
        items = CERTIFICATES
    return {"items": items, "total": len(items), "scope": role}
