"""Add delivery, assessment and notification tables used by the LMS API."""

from alembic import op

revision = "0002_lms_delivery_tables"
down_revision = "0001_initial_lms_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS resources (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), course_id UUID REFERENCES courses(id),
      branch_id UUID REFERENCES branches(id), title VARCHAR(180) NOT NULL, resource_type VARCHAR(32) NOT NULL,
      resource_url TEXT, status VARCHAR(24) NOT NULL DEFAULT 'pending_approval', created_by UUID REFERENCES users(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), branch_id UUID REFERENCES branches(id),
      batch_id UUID REFERENCES batches(id), title VARCHAR(180) NOT NULL, session_type VARCHAR(32) NOT NULL,
      starts_at TIMESTAMPTZ NOT NULL, duration_minutes INTEGER NOT NULL, host_id UUID REFERENCES users(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS exams (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), course_id UUID REFERENCES courses(id),
      branch_id UUID REFERENCES branches(id), title VARCHAR(180) NOT NULL, total_marks NUMERIC(7,2) NOT NULL DEFAULT 100,
      status VARCHAR(24) NOT NULL DEFAULT 'published', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS exam_attempts (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), exam_id UUID NOT NULL REFERENCES exams(id),
      student_id UUID NOT NULL REFERENCES users(id), score NUMERIC(7,2), submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (exam_id, student_id)
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id),
      title VARCHAR(180) NOT NULL, message TEXT NOT NULL, read_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_resources_branch_status ON resources(branch_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_branch_start ON sessions(branch_id, starts_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read_at)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS notifications, exam_attempts, exams, sessions, resources CASCADE")
