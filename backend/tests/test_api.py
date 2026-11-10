from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["persistence"] == "memory"

def test_login_returns_jwt():
    response = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]

def test_login_rejects_empty_credentials():
    response = client.post("/api/v1/auth/login", json={"identifier": "", "password": ""})
    assert response.status_code == 401

def test_login_rejects_unknown_identity():
    response = client.post("/api/v1/auth/login", json={"identifier": "unknown@example.com", "password": "demo"})
    assert response.status_code == 401

def test_login_rejects_wrong_password():
    response = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "wrong"})
    assert response.status_code == 401

def test_me_returns_role_permissions():
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert response.json()["role"] == "faculty"
    assert "attendance:write" in response.json()["permissions"]
    assert "audit:read" not in response.json()["permissions"]

def test_overview_is_role_specific():
    identities = {
        "student@image.edu.in": "active_courses",
        "faculty@image.edu.in": "assigned_classes",
        "admin@image.edu.in": "active_students",
        "management@image.edu.in": "active_branches",
    }
    for identifier, expected_field in identities.items():
        login = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": "demo"}).json()
        response = client.get("/api/v1/reports/overview", headers={"Authorization": f"Bearer {login['access_token']}"})
        assert response.status_code == 200
        assert expected_field in response.json()["summary"]

def test_management_overview_uses_catalogue_counts():
    management = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/overview", headers={"Authorization": f"Bearer {management['access_token']}"})
    assert response.status_code == 200
    assert response.json()["summary"]["active_branches"] >= 1
    assert response.json()["summary"]["published_courses"] >= 1

def test_student_overview_uses_learning_catalogue_counts():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/overview", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["active_courses"] >= 1
    assert summary["upcoming_sessions"] >= 1

def test_faculty_overview_uses_branch_activity_counts():
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/overview", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["pending_submissions"] >= 0
    assert summary["resources_to_publish"] >= 0

def test_workspace_catalogue_matches_role_permissions():
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 401
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert "attendance:write" in response.json()["items"]["faculty"]["permissions"]
    assert "audit:read" in response.json()["items"]["management"]["permissions"]
    assert response.json()["current_role"] == "faculty"

def test_notification_read_state_persists_for_visible_role():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    updated = client.patch("/api/v1/notifications/note-1001", headers=headers, json={"read": True})
    assert updated.status_code == 200
    notifications = client.get("/api/v1/notifications", headers=headers)
    assert notifications.status_code == 200
    assert notifications.json()["unread"] == 0

def test_notification_update_hides_other_role_messages():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.patch("/api/v1/notifications/note-1002", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"read": True})
    assert response.status_code == 404

def test_faculty_resource_submission_is_visible_in_branch_catalogue():
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = client.post("/api/v1/resources", headers=headers, json={"title": "Motion design references", "type": "pdf", "course": "Motion Design", "resource_url": "https://example.invalid/motion.pdf"})
    assert created.status_code == 200
    catalogue = client.get("/api/v1/resources", headers=headers)
    assert any(item["title"] == "Motion design references" and item["status"] == "pending_approval" for item in catalogue.json()["items"])
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    student_catalogue = client.get("/api/v1/resources", headers={"Authorization": f"Bearer {student['access_token']}"})
    assert all(item["status"] == "published" for item in student_catalogue.json()["items"])

def test_management_can_approve_resource():
    faculty = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    created = client.post("/api/v1/resources", headers={"Authorization": f"Bearer {faculty['access_token']}"}, json={"title": "Approval workflow", "type": "pdf", "course": "Motion Design", "resource_url": "https://example.invalid/approval.pdf"})
    resource_id = created.json()["resource"]["id"]
    management = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    approved = client.patch(f"/api/v1/resources/{resource_id}", headers={"Authorization": f"Bearer {management['access_token']}"}, json={"status": "published"})
    assert approved.status_code == 200
    assert approved.json()["resource"]["status"] == "published"

def test_student_submission_is_retained_and_visible_to_branch_faculty():
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    student_headers = {"Authorization": f"Bearer {student['access_token']}"}
    created = client.post("/api/v1/assignments/submissions", headers=student_headers, json={"assignment_id": "asg-1001", "submission_url": "https://example.invalid/moodboard.pdf", "notes": "Final moodboard"})
    assert created.status_code == 200
    faculty = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    submissions = client.get("/api/v1/assignments/submissions", headers={"Authorization": f"Bearer {faculty['access_token']}"})
    assert submissions.status_code == 200
    assert any(item["assignment_id"] == "asg-1001" for item in submissions.json()["items"])

def test_student_cannot_submit_assignment_from_another_branch():
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/assignments/submissions", headers={"Authorization": f"Bearer {student['access_token']}"}, json={"assignment_id": "asg-1003", "submission_url": "https://example.invalid/work.pdf"})
    assert response.status_code == 404

def test_faculty_can_grade_branch_submission():
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    created = client.post("/api/v1/assignments/submissions", headers={"Authorization": f"Bearer {student['access_token']}"}, json={"assignment_id": "asg-1001", "submission_url": "https://example.invalid/grade.pdf"})
    submission_id = created.json()["submission"]["id"]
    faculty = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    graded = client.patch(f"/api/v1/assignments/submissions/{submission_id}", headers={"Authorization": f"Bearer {faculty['access_token']}"}, json={"score": 88, "feedback": "Strong concept"})
    assert graded.status_code == 200
    assert graded.json()["submission"]["status"] == "graded"

def test_student_cannot_grade_submission():
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.patch("/api/v1/assignments/submissions/sub-demo-999", headers={"Authorization": f"Bearer {student['access_token']}"}, json={"score": 80})
    assert response.status_code == 403

def test_exam_attempt_is_retained_and_visible_to_branch_faculty():
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    created = client.post("/api/v1/exams/attempts", headers={"Authorization": f"Bearer {student['access_token']}"}, json={"exam_id": "exam-1001", "answers": {"1": "a", "2": "b"}})
    assert created.status_code == 200
    student_notifications = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {student['access_token']}"})
    assert any(item["title"] == "Exam attempt received" for item in student_notifications.json()["items"])
    faculty = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    attempts = client.get("/api/v1/exams/attempts", headers={"Authorization": f"Bearer {faculty['access_token']}"})
    assert attempts.status_code == 200
    assert any(item["exam_id"] == "exam-1001" for item in attempts.json()["items"])

def test_student_cannot_attempt_exam_from_another_branch():
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/exams/attempts", headers={"Authorization": f"Bearer {student['access_token']}"}, json={"exam_id": "exam-1002", "answers": {"1": "a"}})
    assert response.status_code == 404

def test_branch_admin_can_issue_certificate_visible_to_student():
    admin = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    issued = client.post("/api/v1/certificates", headers={"Authorization": f"Bearer {admin['access_token']}"}, json={"student_id": "stu-1001", "student_name": "Arjun Kumar", "course": "Motion Design"})
    assert issued.status_code == 200
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    certificates = client.get("/api/v1/certificates", headers={"Authorization": f"Bearer {student['access_token']}"})
    assert any(item["course"] == "Motion Design" for item in certificates.json()["items"])

def test_student_cannot_issue_certificate():
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/certificates", headers={"Authorization": f"Bearer {student['access_token']}"}, json={"student_id": "stu-1001", "student_name": "Arjun Kumar", "course": "Motion Design"})
    assert response.status_code == 403

def test_faculty_lesson_draft_is_retained_but_hidden_from_students():
    faculty = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    faculty_headers = {"Authorization": f"Bearer {faculty['access_token']}"}
    created = client.post("/api/v1/lessons", headers=faculty_headers, json={"course": "Motion Design", "module": "Animation basics", "title": "Keyframes", "sequence": 1, "content_type": "lesson"})
    assert created.status_code == 200
    assert created.json()["lesson"]["published"] is False
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    lessons = client.get("/api/v1/lessons", headers={"Authorization": f"Bearer {student['access_token']}"})
    assert all(item["published"] for item in lessons.json()["items"])

def test_management_can_publish_lesson_draft():
    faculty = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    created = client.post("/api/v1/lessons", headers={"Authorization": f"Bearer {faculty['access_token']}"}, json={"course": "Motion Design", "module": "Animation basics", "title": "Publishing workflow", "sequence": 2, "content_type": "lesson"})
    lesson_id = created.json()["lesson"]["id"]
    management = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    published = client.patch(f"/api/v1/lessons/{lesson_id}", headers={"Authorization": f"Bearer {management['access_token']}"}, json={"published": True})
    assert published.status_code == 200
    assert published.json()["lesson"]["published"] is True

def test_protected_endpoint_requires_token():
    response = client.get("/api/v1/courses")
    assert response.status_code == 401

def test_student_can_read_own_students_scope():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/students", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert response.json()["scope"] == "student"
    assert response.json()["total"] == 1

def test_student_cannot_record_attendance():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/attendance", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"student_id": "stu-1001", "attendance_date": "2026-11-05", "status": "present"})
    assert response.status_code == 403

def test_faculty_attendance_record_updates_branch_attendance():
    faculty = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {faculty['access_token']}"}
    recorded = client.post("/api/v1/attendance", headers=headers, json={"student_id": "stu-1002", "attendance_date": "2026-11-06", "status": "late"})
    assert recorded.status_code == 200
    attendance = client.get("/api/v1/attendance", headers=headers)
    assert any(item["student_id"] == "stu-1002" and item["date"] == "2026-11-06" and item["status"] == "late" for item in attendance.json()["items"])

def test_student_cannot_create_course():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/courses", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"code": "TEST", "name": "Test", "category": "Specialization"})
    assert response.status_code == 403

def test_management_can_create_branch():
    login = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/branches", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"code": "TIR", "name": "Tirupati", "state": "Andhra Pradesh", "city": "Tirupati"})
    assert response.status_code == 200

def test_management_course_draft_is_visible_in_catalogue():
    login = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = client.post("/api/v1/courses", headers=headers, json={"code": "MOTION", "name": "Motion Design", "category": "Specialization"})
    assert created.status_code == 200
    catalogue = client.get("/api/v1/courses", headers=headers)
    assert any(item["code"] == "MOTION" and item["status"] == "draft" for item in catalogue.json()["items"])

def test_course_catalogue_has_status_for_every_course():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/courses", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert all(item["status"] in {"published", "draft"} for item in response.json()["items"])

def test_student_cannot_see_management_course_draft():
    management = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    client.post("/api/v1/courses", headers={"Authorization": f"Bearer {management['access_token']}"}, json={"code": "PRIVATE-COURSE", "name": "Private Draft", "category": "Specialization"})
    student = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    courses = client.get("/api/v1/courses", headers={"Authorization": f"Bearer {student['access_token']}"})
    assert all(item["status"] == "published" for item in courses.json()["items"])

def test_management_can_publish_course_draft():
    management = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {management['access_token']}"}
    client.post("/api/v1/courses", headers=headers, json={"code": "PUBLISH-COURSE", "name": "Publish Workflow", "category": "Professional"})
    updated = client.patch("/api/v1/courses/PUBLISH-COURSE", headers=headers, json={"status": "published"})
    assert updated.status_code == 200
    assert updated.json()["course"]["status"] == "published"

def test_management_branch_creation_updates_branch_catalogue():
    login = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = client.post("/api/v1/branches", headers=headers, json={"code": "KOC", "name": "Kochi", "state": "Kerala", "city": "Kochi"})
    assert created.status_code == 200
    catalogue = client.get("/api/v1/branches")
    assert any(item["name"] == "Kochi" for item in catalogue.json()["items"])

def test_branch_admin_batch_creation_updates_batch_catalogue():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = client.post("/api/v1/batches", headers=headers, json={"name": "Salem Motion 2026 A", "branch": "Salem", "course": "Motion Design", "academic_year": "2026", "faculty": "Priya Menon"})
    assert created.status_code == 200
    catalogue = client.get("/api/v1/batches", headers=headers)
    assert any(item["name"] == "Salem Motion 2026 A" for item in catalogue.json()["items"])

def test_branch_admin_can_create_enrollment():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/enrollments", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"student_id": "stu-1004", "batch_id": "batch-salem-ux-01", "course": "Graphic & UX / UI Design", "branch": "Salem"})
    assert response.status_code == 200

def test_branch_admin_enrollment_is_visible_in_branch_list():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = client.post("/api/v1/enrollments", headers=headers, json={"student_id": "stu-1006", "batch_id": "batch-salem-ux-01", "course": "Graphic & UX / UI Design", "branch": "Salem"})
    assert created.status_code == 200
    enrollments = client.get("/api/v1/enrollments", headers=headers)
    assert any(item["student_id"] == "stu-1006" for item in enrollments.json()["items"])

def test_branch_admin_cannot_enrol_student_outside_branch():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/enrollments", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"student_id": "stu-1005", "batch_id": "batch-adyar-gai-01", "course": "C-TECH with Gen AI", "branch": "Adyar"})
    assert response.status_code == 403

def test_branch_admin_faculty_creation_updates_directory():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = client.post("/api/v1/faculty", headers=headers, json={"name": "Asha Kumar", "email": "asha.kumar@example.test", "branch": "Salem", "specialization": "Motion Design"})
    assert created.status_code == 200
    directory = client.get("/api/v1/faculty", headers=headers)
    assert any(member["email"] == "asha.kumar@example.test" for member in directory.json()["items"])

def test_branch_admin_cannot_create_faculty_outside_branch():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/faculty", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"name": "Asha Kumar", "email": "asha.adyar@example.test", "branch": "Adyar", "specialization": "Motion Design"})
    assert response.status_code == 403

def test_branch_admin_student_creation_updates_directory():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    created = client.post("/api/v1/students", headers=headers, json={"name": "Riya Das", "email": "riya.das@example.test", "branch": "Salem", "course": "Motion Design"})
    assert created.status_code == 200
    directory = client.get("/api/v1/students", headers=headers)
    assert any(student["email"] == "riya.das@example.test" for student in directory.json()["items"])

def test_branch_admin_cannot_create_student_outside_branch():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    response = client.post("/api/v1/students", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"name": "Riya Das", "email": "riya.adyar@example.test", "branch": "Adyar", "course": "Motion Design"})
    assert response.status_code == 403

def test_management_can_read_branch_report():
    login = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/branches", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert response.json()["scope"] == "management"
    assert any(item["branch"] == "Salem" and item["students"] >= 1 for item in response.json()["items"])

def test_branch_catalogue_includes_location_metadata():
    response = client.get("/api/v1/branches")
    assert response.status_code == 200
    salem = next(item for item in response.json()["items"] if item["name"] == "Salem")
    assert salem["state"] == "Tamil Nadu"
    assert salem["city"] == "Salem"
    assert salem["code"] == "SALEM"

def test_branch_admin_cannot_read_management_branch_report():
    login = client.post("/api/v1/auth/login", json={"identifier": "admin@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/branches", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 403

def test_management_can_read_attendance_report():
    login = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/attendance", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert response.json()["items"][0]["attendance_rate"] >= 0

def test_faculty_cannot_read_management_attendance_report():
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/attendance", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 403

def test_student_can_read_consolidated_progress():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/progress", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert response.json()["scope"] == "student"
    assert {"submissions", "exam_attempts", "certificates", "attendance_rate", "upcoming_sessions"}.issubset(response.json()["summary"])

def test_faculty_cannot_read_student_progress_report():
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/progress", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 403

def test_management_can_read_content_quality_report():
    login = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/reports/quality", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert set(response.json()["summary"]) == {"pending_resources", "draft_lessons", "draft_courses", "ungraded_submissions"}

def test_management_audit_log_includes_new_course_creation():
    management = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()
    headers = {"Authorization": f"Bearer {management['access_token']}"}
    client.post("/api/v1/courses", headers=headers, json={"code": "AUDIT-COURSE", "name": "Audit Course", "category": "Professional"})
    audit = client.get("/api/v1/audit", headers=headers)
    assert audit.status_code == 200
    assert any(item["action"] == "course.created" for item in audit.json()["items"])

def test_student_can_read_branch_schedule():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert response.json()["scope"] == "student"
    assert all(item["branch"] == "Salem" for item in response.json()["items"])

def test_faculty_can_schedule_branch_session():
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    created = client.post("/api/v1/sessions", headers={"Authorization": f"Bearer {login['access_token']}"}, json={"title": "Portfolio lab", "course": "Graphic & UX / UI Design", "starts_at": "2026-11-10T10:00:00+05:30", "duration_minutes": 90, "type": "live_class", "faculty": "Priya Menon"})
    assert created.status_code == 200
    assert created.json()["session"]["branch"] == "Salem"

def test_sessions_require_authentication():
    response = client.get("/api/v1/sessions")
    assert response.status_code == 401

def test_student_cannot_read_faculty_directory():
    login = client.post("/api/v1/auth/login", json={"identifier": "student@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/faculty", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 403

def test_faculty_can_read_assigned_classes():
    login = client.post("/api/v1/auth/login", json={"identifier": "faculty@image.edu.in", "password": "demo"}).json()
    response = client.get("/api/v1/faculty/classes", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert response.status_code == 200
    assert response.json()["scope"] == "faculty"
    assert all(item["faculty"] == "Priya Menon" for item in response.json()["items"])
