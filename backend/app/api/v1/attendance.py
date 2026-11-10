from datetime import date
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.security import require_role
from app.api.v1.audit_store import persist_audit, record_audit
from app.core.database import get_db
from app.models import Attendance, Batch, Branch, User

router = APIRouter()

ATTENDANCE = [
    {"student_id": "stu-1001", "student_name": "Arjun Kumar", "branch": "Salem", "date": "2026-11-05", "status": "present"},
    {"student_id": "stu-1002", "student_name": "Meena Raj", "branch": "Salem", "date": "2026-11-05", "status": "present"},
    {"student_id": "stu-1003", "student_name": "Vijay Anand", "branch": "Adyar", "date": "2026-11-05", "status": "late"},
]

class AttendanceRecord(BaseModel):
    student_id: str
    attendance_date: date
    status: str

class BulkAttendanceRecord(BaseModel):
    student_id: str
    status: str

class BulkAttendance(BaseModel):
    attendance_date: date
    records: list[BulkAttendanceRecord]

@router.post("/bulk")
async def record_bulk_attendance(payload: BulkAttendance, user=Depends(require_role("faculty", "branch_admin")), db: AsyncSession = Depends(get_db)):
    if not payload.records:
        raise HTTPException(status_code=422, detail="At least one attendance record is required")
    results = []
    for item in payload.records:
        record = AttendanceRecord(student_id=item.student_id, attendance_date=payload.attendance_date, status=item.status)
        result = await record_attendance(record, user, db)
        results.append(result["record"])
    return {"status": "recorded", "count": len(results), "records": results}

@router.get("")
async def list_attendance(user=Depends(require_role("student", "faculty", "branch_admin", "management")), db: AsyncSession = Depends(get_db)):
    role = user.get("role")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        query = select(Attendance, User, Batch, Branch).join(User, Attendance.student_id == User.id).join(Batch, Attendance.batch_id == Batch.id).join(Branch, User.branch_id == Branch.id, isouter=True)
        if role == "student":
            try: query = query.where(User.id == uuid.UUID(user.get("sub", "")))
            except ValueError: query = query.where(Attendance.id == uuid.uuid4())
        elif role in {"faculty", "branch_admin"}: query = query.where(Branch.name == user.get("branch", "Salem"))
        items = [{"student_id": str(student.id), "student_name": student.full_name, "branch": branch.name if branch else "", "date": item.attendance_date.isoformat(), "status": item.status} for item, student, batch, branch in (await db.execute(query)).all()]
        return {"items": items, "total": len(items), "scope": role}
    if role == "student":
        items = [item for item in ATTENDANCE if item["student_id"] == user.get("sub", "stu-1001")]
    elif role in {"faculty", "branch_admin"}:
        items = [item for item in ATTENDANCE if item["branch"] == user.get("branch", "Salem")]
    else:
        items = ATTENDANCE
    return {"items": items, "total": len(items), "scope": role}

@router.post("")
async def record_attendance(payload: AttendanceRecord, user=Depends(require_role("faculty", "branch_admin")), db: AsyncSession = Depends(get_db)):
    branch = user.get("branch", "Salem")
    if os.getenv("PERSISTENCE_MODE", "memory") == "postgres":
        try: student_id = uuid.UUID(payload.student_id)
        except ValueError: raise HTTPException(status_code=404, detail="Student not found")
        student = (await db.execute(select(User).where(User.id == student_id, User.role == "student"))).scalar_one_or_none()
        batch = (await db.execute(select(Batch).join(Branch, Batch.branch_id == Branch.id).where(Branch.name == branch).order_by(Batch.name))).scalars().first()
        if student is None or batch is None: raise HTTPException(status_code=404, detail="Student or batch not found")
        student_branch = (await db.execute(select(Branch).where(Branch.id == student.branch_id))).scalar_one_or_none()
        if user.get("role") == "branch_admin" and (student_branch is None or student_branch.name != branch): raise HTTPException(status_code=403, detail="Student is outside your branch")
        existing = (await db.execute(select(Attendance).where(Attendance.student_id == student.id, Attendance.batch_id == batch.id, Attendance.attendance_date == payload.attendance_date))).scalar_one_or_none()
        if existing: existing.status = payload.status
        else: db.add(Attendance(student_id=student.id, batch_id=batch.id, attendance_date=payload.attendance_date, status=payload.status))
        await db.commit()
        record = {"student_id": str(student.id), "student_name": student.full_name, "branch": branch, "date": payload.attendance_date.isoformat(), "status": payload.status, "recorded_by": user.get("sub")}
        await persist_audit(db, "attendance.recorded", "attendance", user.get("sub", "unknown"), branch)
        return {"status": "recorded", "record": record}
    record = {"student_id": payload.student_id, "student_name": payload.student_id, "branch": branch, "date": payload.attendance_date.isoformat(), "status": payload.status, "recorded_by": user.get("sub")}
    existing = next((item for item in ATTENDANCE if item["student_id"] == payload.student_id and item["branch"] == branch and item["date"] == record["date"]), None)
    if existing:
        existing.update(record)
    else:
        ATTENDANCE.append(record)
    record_audit("attendance.recorded", "attendance", user.get("sub", "unknown"), branch)
    return {"status": "recorded", "record": record}
