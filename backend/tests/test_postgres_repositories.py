import os
import uuid
import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(os.getenv("PERSISTENCE_MODE", "memory") != "postgres", reason="PostgreSQL repository smoke tests require PERSISTENCE_MODE=postgres")


def test_postgres_branch_course_batch_round_trip():
    from app.main import app

    client = TestClient(app)
    token = client.post("/api/v1/auth/login", json={"identifier": "management@image.edu.in", "password": "demo"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    suffix = uuid.uuid4().hex[:8]
    branch = {"code": f"PG-{suffix}", "name": f"PG Branch {suffix}", "state": "Tamil Nadu", "city": "Chennai"}
    course = {"code": f"PG-{suffix}-C", "name": f"PG Course {suffix}", "category": "Integration"}
    created_branch = client.post("/api/v1/branches", headers=headers, json=branch)
    created_course = client.post("/api/v1/courses", headers=headers, json=course)
    assert created_branch.status_code == 200
    assert created_course.status_code == 200
    created_batch = client.post("/api/v1/batches", headers=headers, json={"name": f"PG Batch {suffix}", "branch": branch["name"], "course": course["name"], "academic_year": "2026", "faculty": "Priya Menon"})
    assert created_batch.status_code == 200
    assert created_batch.json()["batch"]["name"] == f"PG Batch {suffix}"
    created_exam = client.post("/api/v1/exams", headers=headers, json={"title": f"PG Exam {suffix}", "course": course["name"], "branch": branch["name"], "total_marks": 50, "status": "draft"})
    assert created_exam.status_code == 200
    exam_id = created_exam.json()["exam"]["id"]
    published_exam = client.patch(f"/api/v1/exams/{exam_id}", headers=headers, json={"status": "open"})
    assert published_exam.status_code == 200 and published_exam.json()["status"] == "open"
    classes = client.get("/api/v1/faculty/classes", headers=headers)
    assert classes.status_code == 200
    assert any(item["name"] == f"PG Batch {suffix}" for item in classes.json()["items"])
    branch_report = client.get("/api/v1/reports/branches", headers=headers)
    assert branch_report.status_code == 200
    assert any(item["branch"] == branch["name"] for item in branch_report.json()["items"])
    student_email = f"student-{suffix}@example.test"
    faculty_email = f"faculty-{suffix}@example.test"
    assert client.post("/api/v1/students", headers=headers, json={"name": f"PG Student {suffix}", "email": student_email, "branch": branch["name"], "course": course["name"]}).status_code == 200
    assert client.post("/api/v1/faculty", headers=headers, json={"name": f"PG Faculty {suffix}", "email": faculty_email, "branch": branch["name"], "specialization": "Integration"}).status_code == 200
    published_course = client.patch(f"/api/v1/courses/{course['code']}", headers=headers, json={"status": "published"})
    assert published_course.status_code == 200
    student_login = client.post("/api/v1/auth/login", json={"identifier": student_email, "password": "demo"})
    faculty_login = client.post("/api/v1/auth/login", json={"identifier": faculty_email, "password": "demo"})
    assert student_login.status_code == 200 and student_login.json()["user"]["role"] == "student"
    assert faculty_login.status_code == 200 and faculty_login.json()["user"]["role"] == "faculty"
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    faculty_headers = {"Authorization": f"Bearer {faculty_login.json()['access_token']}"}
    course_notifications = client.get("/api/v1/notifications", headers=student_headers)
    assert course_notifications.status_code == 200 and any(item["title"] == "New course available" for item in course_notifications.json()["items"])
    issued_certificate = client.post("/api/v1/certificates", headers=headers, json={"student_id": student_login.json()["user"]["sub"], "student_name": f"PG Student {suffix}", "course": course["name"]})
    assert issued_certificate.status_code == 200
    duplicate_certificate = client.post("/api/v1/certificates", headers=headers, json={"student_id": student_login.json()["user"]["sub"], "student_name": f"PG Student {suffix}", "course": course["name"]})
    assert duplicate_certificate.status_code == 409
    certificate_notifications = client.get("/api/v1/notifications", headers=student_headers)
    assert certificate_notifications.status_code == 200 and any(item["title"] == "Certificate issued" for item in certificate_notifications.json()["items"])
    assert client.patch(f"/api/v1/exams/{exam_id}", headers=headers, json={"status": "scheduled"}).status_code == 200
    reopened_exam = client.patch(f"/api/v1/exams/{exam_id}", headers=headers, json={"status": "open"})
    assert reopened_exam.status_code == 200
    student_exams = client.get("/api/v1/exams", headers=student_headers)
    assert student_exams.status_code == 200 and any(item["id"] == exam_id and item["status"] == "open" and item["total_marks"] == 50 for item in student_exams.json()["items"])
    exam_notifications = client.get("/api/v1/notifications", headers=student_headers)
    assert exam_notifications.status_code == 200 and any(item["title"] == "Exam available" for item in exam_notifications.json()["items"])
    scheduled = client.post("/api/v1/sessions", headers=faculty_headers, json={"title": f"Session {suffix}", "course": course["name"], "starts_at": "2026-11-10T10:00:00+05:30", "duration_minutes": 60, "type": "live_class", "faculty": f"PG Faculty {suffix}"})
    assert scheduled.status_code == 200
    session_notifications = client.get("/api/v1/notifications", headers=student_headers)
    assert session_notifications.status_code == 200 and any(item["title"] == "New live session scheduled" for item in session_notifications.json()["items"])
    faculty_sessions = client.get("/api/v1/sessions", headers=faculty_headers)
    assert faculty_sessions.status_code == 200
    assert any(item["title"] == f"Session {suffix}" for item in faculty_sessions.json()["items"])
    enrolled = client.post("/api/v1/enrollments", headers=headers, json={"student_id": student_login.json()["user"]["sub"], "batch_id": created_batch.json()["batch"]["id"], "course": course["name"], "branch": branch["name"]})
    assert enrolled.status_code == 200
    enrollment_notifications = client.get("/api/v1/notifications", headers=student_headers)
    assert enrollment_notifications.status_code == 200 and any(item["title"] == "Enrollment confirmed" for item in enrollment_notifications.json()["items"])
    student_enrollments = client.get("/api/v1/enrollments", headers=student_headers)
    assert student_enrollments.status_code == 200
    assert any(item["batch_id"] == created_batch.json()["batch"]["id"] for item in student_enrollments.json()["items"])
    created_lesson = client.post("/api/v1/lessons", headers=faculty_headers, json={"course": course["name"], "module": "Integration", "title": f"Lesson {suffix}", "sequence": 1, "content_type": "project"})
    assert created_lesson.status_code == 200
    created_assignment = client.post("/api/v1/assignments", headers=faculty_headers, json={"lesson_id": created_lesson.json()["lesson"]["id"], "title": f"Assignment {suffix}", "description": "Build and submit the project", "due_at": "2026-11-20T23:59:00+05:30", "max_score": 100})
    assert created_assignment.status_code == 200
    assignment_id = created_assignment.json()["assignment"]["id"]
    assignment_notifications = client.get("/api/v1/notifications", headers=student_headers)
    assert assignment_notifications.status_code == 200 and any(item["title"] == "New assignment available" for item in assignment_notifications.json()["items"])
    from app.core.database import SessionLocal
    from app.models import Attendance
    async def seed_attendance():
        async with SessionLocal() as session:
            session.add(Attendance(student_id=uuid.UUID(student_login.json()["user"]["sub"]), batch_id=uuid.UUID(created_batch.json()["batch"]["id"]), attendance_date=date.today(), status="present"))
            await session.commit()
    asyncio.run(seed_attendance())
    attendance_report = client.get("/api/v1/reports/attendance", headers=headers)
    assert attendance_report.status_code == 200
    assert any(item["branch"] == branch["name"] and item["attendance_rate"] == 100 for item in attendance_report.json()["items"])
    bulk_attendance = client.post("/api/v1/attendance/bulk", headers=faculty_headers, json={"attendance_date": "2026-11-07", "records": [{"student_id": student_login.json()["user"]["sub"], "status": "present"}]})
    assert bulk_attendance.status_code == 200
    assert bulk_attendance.json()["count"] == 1
    submitted = client.post("/api/v1/assignments/submissions", headers=student_headers, json={"assignment_id": assignment_id, "submission_url": "https://example.test/work.pdf"})
    assert submitted.status_code == 200
    faculty_notifications = client.get("/api/v1/notifications", headers=faculty_headers)
    assert faculty_notifications.status_code == 200 and any(item["title"] == "New submission received" for item in faculty_notifications.json()["items"])
    assignment_status = client.get("/api/v1/assignments", headers=student_headers)
    assert any(item["id"] == assignment_id and item["status"] == "submitted" for item in assignment_status.json()["items"])
    graded = client.patch(f"/api/v1/assignments/submissions/{submitted.json()['submission']['id']}", headers=faculty_headers, json={"score": 91, "feedback": "Strong work"})
    assert graded.status_code == 200 and graded.json()["status"] == "graded"
    notifications = client.get("/api/v1/notifications", headers=student_headers)
    assert notifications.status_code == 200 and any(item["title"] == "Assignment graded" for item in notifications.json()["items"])
    assignment_status = client.get("/api/v1/assignments", headers=student_headers)
    assert any(item["id"] == assignment_id and item["status"] == "graded" for item in assignment_status.json()["items"])
    graded_assignment = next(item for item in assignment_status.json()["items"] if item["id"] == assignment_id)
    assert graded_assignment["score"] == 91 and graded_assignment["max_score"] == 100
    progress = client.get("/api/v1/reports/progress", headers=student_headers)
    assert progress.status_code == 200
    assert progress.json()["summary"]["submissions"] >= 1
    assert progress.json()["summary"]["average_score"] == 91
    quality = client.get("/api/v1/reports/quality", headers=headers)
    assert quality.status_code == 200
    assert set(quality.json()["summary"]) == {"pending_resources", "draft_lessons", "draft_courses", "ungraded_submissions"}
    audit = client.get("/api/v1/audit", headers=headers)
    assert audit.status_code == 200
    assert audit.json()["scope"] == "management"
    audit_actions = {item["action"] for item in audit.json()["items"]}
    assert {"branch.created", "batch.created", "student.created", "faculty.created", "enrollment.created", "assignment.submission.created", "assignment.submission.graded"}.issubset(audit_actions)
    dashboard = client.get("/api/v1/reports/dashboard", headers=student_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["scope"] == "student"
    assert dashboard.json()["average_score"] == 91
