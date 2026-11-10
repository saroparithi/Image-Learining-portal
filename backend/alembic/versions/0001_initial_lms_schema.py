"""Create the initial IMAGE LMS relational schema.

This migration mirrors database/schema.sql so Docker and Alembic use the same
contract. Each statement is idempotent to support existing development databases.
"""

from alembic import op

revision = "0001_initial_lms_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("""
    CREATE TABLE IF NOT EXISTS organizations (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(180) NOT NULL,
      domain VARCHAR(180) NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS branches (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), organization_id UUID NOT NULL REFERENCES organizations(id),
      code VARCHAR(32) NOT NULL, name VARCHAR(120) NOT NULL, state VARCHAR(80), city VARCHAR(80),
      status VARCHAR(20) NOT NULL DEFAULT 'active', UNIQUE (organization_id, code)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(255) NOT NULL UNIQUE,
      password_hash TEXT NOT NULL, full_name VARCHAR(160) NOT NULL,
      role VARCHAR(32) NOT NULL CHECK (role IN ('student','faculty','branch_admin','management')),
      branch_id UUID REFERENCES branches(id), status VARCHAR(20) NOT NULL DEFAULT 'active', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS courses (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), code VARCHAR(32) NOT NULL UNIQUE,
      name VARCHAR(180) NOT NULL, category VARCHAR(80) NOT NULL, description TEXT, status VARCHAR(20) NOT NULL DEFAULT 'draft'
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS batches (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), branch_id UUID NOT NULL REFERENCES branches(id),
      course_id UUID NOT NULL REFERENCES courses(id), name VARCHAR(120) NOT NULL, academic_year VARCHAR(20) NOT NULL,
      faculty_id UUID REFERENCES users(id)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL REFERENCES users(id),
      batch_id UUID NOT NULL REFERENCES batches(id), enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (student_id, batch_id)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), course_id UUID NOT NULL REFERENCES courses(id),
      title VARCHAR(180) NOT NULL, sequence INTEGER NOT NULL, content_type VARCHAR(32) NOT NULL,
      resource_url TEXT, status VARCHAR(20) NOT NULL DEFAULT 'draft'
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), lesson_id UUID NOT NULL REFERENCES lessons(id),
      title VARCHAR(180) NOT NULL, description TEXT, due_at TIMESTAMPTZ, max_score NUMERIC(6,2) NOT NULL DEFAULT 100
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), assignment_id UUID NOT NULL REFERENCES assignments(id),
      student_id UUID NOT NULL REFERENCES users(id), file_url TEXT, score NUMERIC(6,2), feedback TEXT,
      submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(), graded_at TIMESTAMPTZ
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL REFERENCES users(id),
      batch_id UUID NOT NULL REFERENCES batches(id), attendance_date DATE NOT NULL,
      status VARCHAR(20) NOT NULL CHECK (status IN ('present','absent','late','excused')),
      UNIQUE (student_id, batch_id, attendance_date)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL REFERENCES users(id),
      course_id UUID NOT NULL REFERENCES courses(id), certificate_number VARCHAR(80) NOT NULL UNIQUE,
      issued_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), actor_id UUID REFERENCES users(id), action VARCHAR(120) NOT NULL,
      entity_type VARCHAR(80) NOT NULL, entity_id UUID, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_branch_role ON users(branch_id, role)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS audit_logs, certificates, attendance, submissions, assignments, lessons, enrollments, batches, courses, users, branches, organizations CASCADE")
