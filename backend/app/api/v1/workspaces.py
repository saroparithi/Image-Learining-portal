from fastapi import APIRouter, Depends
from app.core.security import current_user

router = APIRouter()

WORKSPACES = {
    "student": {
        "label": "Student",
        "navigation": ["Overview", "My learning", "Progress", "Schedule", "Resources", "Career launchpad"],
        "permissions": ["learning:read", "assignments:submit", "exams:attempt", "reports:self"],
    },
    "faculty": {
        "label": "Faculty",
        "navigation": ["Overview", "My classes", "Attendance", "Assignments", "Exams", "Students", "Resources"],
        "permissions": ["learning:read", "classes:manage", "assignments:author", "assignments:review", "exams:author", "attendance:write", "resources:publish"],
    },
    "branch_admin": {
        "label": "Branch Admin",
        "navigation": ["Overview", "Students", "Faculty", "Courses", "Assignments", "Attendance", "Reports"],
        "permissions": ["students:manage", "faculty:manage", "courses:manage", "assignments:author", "assignments:review", "exams:author", "attendance:write", "resources:publish", "sessions:schedule", "reports:read"],
    },
    "management": {
        "label": "Management",
        "navigation": ["Overview", "Branches", "Performance", "Courses", "Exams", "Reports", "Audit logs"],
        "permissions": ["branches:manage", "courses:manage", "exams:manage", "resources:approve", "reports:read", "audit:read"],
    },
}

@router.get("")
def list_workspaces(user=Depends(current_user)):
    role = user.get("role")
    return {"items": WORKSPACES, "current_role": role, "current_workspace": WORKSPACES.get(role)}
