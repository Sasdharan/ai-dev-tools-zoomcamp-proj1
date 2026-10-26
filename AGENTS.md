# Agent Development Guidelines

## Project Context

- **Description:** Local-first personal expense tracker for creating, reviewing, and importing/exporting transactions.
- **Tech Stack:**
  - Python dependencies: `uv`
  - Frontend: React + Vite
  - Backend: Python + FastAPI
  - Persistence: SQLAlchemy ORM; SQLite for local/self-hosted use and PostgreSQL for the containerized deployment, selected through `DATABASE_URL`.
  - Runtime: Docker Compose for the containerized application.

## Critical Commands

- **Setup:** Create `.env` from `.env.example` only if `.env` does not already exist, then `cd backend && uv sync`
- **Build:** `docker compose --env-file .env up --build`
- **Test:** `cd backend && uv run pytest -v`
- **Smoke test:** `cd backend && uv run pytest -m smoke -q`
- **Lint:** `cd backend && uv run ruff check . ../migrations && uv run ruff format --check . ../migrations`
- **Format/fix:** `cd backend && uv run ruff check --fix . ../migrations && uv run ruff format . ../migrations`
- For formatting/lint-only changes (no behavior change), run lint plus the smoke tests instead of the full suite.

## Project Documentation

- [Product specification](./_docs/spec.md) defines the intended MVP scope and acceptance criteria.
- [Backlog](./_docs/task.md) links to the project's GitHub issues.
- [Development process](./_docs/process.md) defines task tracking, implementation, QA, and integration.
- [Team specification](./_docs/teams.md) describes team roles and how they collaborate.
- Role responsibilities are detailed in [PM](./_docs/team/pm.md), [Software Engineer](./_docs/team/software-engineer.md), and [QA Engineer](./_docs/team/qa-engineer.md).
- The [README](./README.md) documents the implemented application and how to run it.

## Architecture Rules

- The React client calls the FastAPI HTTP API; the API validates and persists transactions through SQLAlchemy.
- The current MVP supports transaction creation/listing and CSV import/export through backend endpoints. Check the actual frontend and API before claiming a capability is available in the UI.
- SMS intake is out of scope for the current MVP and no SMS webhook is implemented. If a future task requests SMS intake, check the current routes and OpenAPI schema, clarify the requested scope and contract, and do not rely on or invent the route or payload described in an older handover document.
- Database migrations must strictly happen via Alembic migration scripts stored in `/migrations`.
Do not call SQLAlchemy `create_all` or alter tables at runtime.
- Use SQLAlchemy ORM for all database access. Select the database backend only via the `DATABASE_URL` environment variable in `.env`; do not hardcode driver-specific SQL or connection strings. Do not infer that `.env` is absent from workspace search results or Git status: local environment files may be hidden, ignored, or untracked. Check the filesystem directly, and do not overwrite an existing `.env`. If the file is genuinely absent, tell the user to create it from `.env.example`; if `DATABASE_URL` is unavailable, ask the user to set it. Verify configuration without printing or exposing its value. Do not fall back to a hardcoded connection string.

## Boundaries & Guardrails

### Always Do

- Run lint and test before declaring a task complete.

### Ask First

- Ask for confirmation before changing the database schema, including creating or modifying Alembic migration scripts in `/migrations`; once confirmed, make schema changes only through those migration scripts.
- Introducing any new third-party dependencies

### Never Do

- Never drop or bypass failing unit tests to make a build pass.
- If lint or tests still fail after 3 fix attempts (not counting the initial failing run), stop, report the failing command and full error output to the user, and do not mark the task complete.
- Never hardcode API keys or environment secrets (always use `.env`).
