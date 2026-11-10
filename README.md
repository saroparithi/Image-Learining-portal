# IMAGE LMS

IMAGE Creative Education's multi-branch learning management system.

## Current state

The React/Vite frontend is a role-aware LMS shell with Student, Faculty, Branch Admin, and Management workspaces. The FastAPI service in `backend/` provides authenticated role-scoped catalogue, learning, delivery, reporting, and administration endpoints.

## Run locally

Use `npm install` then `npm run dev` for local frontend development. Use `docker compose up --build` to run the complete LMS frontend, API, PostgreSQL, and Redis stack. The frontend is available at `http://localhost:5173`, the API at `http://localhost:8000`, and interactive API docs at `http://localhost:8000/docs`. Set `$env:VITE_API_URL` before the Compose build when the API is hosted at another public URL, and set `$env:DATABASE_URL`, `$env:REDIS_URL`, `$env:JWT_SECRET`, plus `$env:JWT_ACCESS_MINUTES` before deployment. The default Compose mode is the in-memory development catalogue; launch with `$env:PERSISTENCE_MODE="postgres"; docker compose up --build` to enable the migrated PostgreSQL branch, course, and batch paths.

The API entrypoint applies `alembic upgrade head` automatically when the Compose database becomes available. Apply `database/seed.sql` separately when you want the initial organization, representative branches, and course catalogue. From a local backend environment, the equivalent migration command is `alembic upgrade head` from `backend/`. `database/schema.sql` remains available as an idempotent SQL bootstrap fallback. The production roadmap is identity and RBAC; branch and organization management; course and curriculum management; student/faculty/batch management; lessons and private learning resources; assignments and examinations; attendance and certificates; reporting; audit and deployment hardening.

The development token and sample records remain the default local scaffolding. In `PERSISTENCE_MODE=postgres`, branches, courses, batches, students, and faculty use PostgreSQL-backed records, and persisted student/faculty accounts can authenticate with the development password. Production still requires hardened password hashing, JWT configuration, seeded identity management, and deployment security review.

## Production Compose

Use the production override only after setting a unique JWT secret, the public frontend origin, and a deployment-safe database configuration:

```powershell
$env:JWT_SECRET = "generate-a-long-random-secret"
$env:POSTGRES_PASSWORD = "generate-a-strong-database-password"
$env:CORS_ALLOWED_ORIGINS = "https://lms.example.com"
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build
```

The production override enables PostgreSQL persistence, disables the development API bind mount, keeps PostgreSQL and Redis off host ports, and disables FastAPI Swagger/ReDoc. Configure HTTPS and a reverse proxy before exposing the services publicly.

## Development demo access

The login screen accepts these local demo identities with password `demo`:

- `student@image.edu.in` — Student workspace
- `faculty@image.edu.in` — Faculty workspace
- `admin@image.edu.in` — Branch Admin workspace
- `management@image.edu.in` — Management workspace

Each role changes the workspace navigation and API permissions. Current portal workflows include assignment submission, progress, resources, certificates, and exams for students; lesson, assignment, exam, grading, live-session scheduling, attendance, and resource submission for faculty; student, faculty, batch, course, assignment, exam-draft, attendance, session, lesson, resource, and certificate operations for branch admins; and branch, course, exam, resource approval, report, quality, and audit operations for management. The API currently uses an in-memory development catalogue by default; PostgreSQL schema, migrations, and seed files are provided for persisted operation.

## Validation

Run `npm run build` to validate the frontend production bundle. For the backend, start Docker Desktop and run `npm run test:api` from the repository root; this executes `docker compose run --rm api pytest -q`. For full-stack validation, use `docker compose up --build` and confirm `docker compose ps` reports frontend, API, PostgreSQL, and Redis as healthy.

## Runtime troubleshooting

The Compose file keeps PostgreSQL and Redis internal to the Compose network, so host ports 5432 and 6379 do not need to be free. If an older stack is already running, stop it with `docker compose down` from that stack's folder before starting this one. If Docker reports a named-pipe permission error, open Docker Desktop, wait for the Linux engine to become ready, and rerun the Compose command from an approved terminal.
