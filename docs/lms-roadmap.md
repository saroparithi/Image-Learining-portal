# IMAGE LMS delivery roadmap

## Delivered role workflows

- Student: submit assignments, attempt exams, view progress, notifications, and earned certificates; receive enrollment, course, session, exam, submission, grading, and certificate alerts.
- Faculty: author lessons, assignments, and exam drafts, review submissions, schedule live sessions, record bulk attendance, and submit learning resources.
- Branch Admin: manage students, faculty, batches, attendance, certificate issuance, branch sessions, learning resources, lesson drafts, and branch assignments.
- Management: manage branches and course drafts, publish courses/resources, author and open exams, and inspect reports and audit activity.

## Persistence phase

PostgreSQL mode now supports the core role workflows and reporting aggregates: identities, branches, courses, batches, students, faculty, enrollments, lessons, assignments/submissions, sessions, resources, exams/attempts and status transitions, attendance, certificates, notifications, dashboard metrics, progress, quality reports, branch reports, attendance reports, and audit-log reads. Core mutations emit durable audit events and lifecycle notifications.

Memory mode remains the default for fast local development. Enable PostgreSQL with `$env:PERSISTENCE_MODE="postgres"; docker compose up --build`.

Each persisted endpoint preserves the memory-mode response shape, role permissions, and branch scoping. The Docker API suite, PostgreSQL smoke suite, migration command, and frontend production build are the regression gates for further aggregate work.

Remaining production work includes durable audit-event writes for every mutation, object storage for uploaded learning files, real-time session delivery, hardened non-demo authentication, background jobs, observability, and deployment secrets/configuration.

## Release gates

1. `npm run build`
2. `docker compose run --rm api alembic upgrade head`
3. `docker compose run --rm api pytest -q`
4. Verify all four demo roles can authenticate and see only their permitted workspace actions.
