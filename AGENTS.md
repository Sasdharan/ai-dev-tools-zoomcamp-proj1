# Agent Development Guidelines

## Project Context

- **Description:** Local expense tracker starter for importing/exporting transactions and tracking SMS transactions.
- **Tech Stack:**
  - Python dependencies: `uv`
  - Frontend direction: React + Vite, intended as an installable PWA. The frontend is not currently present; treat this as planned architecture, not existing code.
  - Backend: Python + FastAPI
  - Persistence: SQLAlchemy ORM; SQLite for local/self-hosted use and PostgreSQL for the containerized deployment, selected through `DATABASE_URL`.
  - Runtime: Docker Compose for the containerized application.

## Critical Commands

- **Setup:** Create `.env` from `.env.example` only if `.env` does not already exist, then `cd backend && uv sync`
- **Build:** `docker compose --env-file .env up --build`
- **Test:** `cd backend && uv run pytest -v`
- **Lint:** `cd backend && uv run ruff check . ../migrations && uv run ruff format --check . ../migrations`

## Architecture Rules

- Intended flow: React client calls the FastAPI HTTP API; the API validates and persists transactions through SQLAlchemy. Support transaction import/export and SMS transaction intake.
- SMS intake is intended to use a webhook; the handover guide documents `POST /api/v1/webhook/sms`.
Before using the SMS webhook, check the FastAPI route definitions in `backend/` (or the OpenAPI schema at `/docs`).
If the implemented path or payload differs from `POST /api/v1/webhook/sms`, use the implemented version and tell the user about the discrepancy.
If the SMS webhook route is not implemented, do not invent a payload schema.
Ask the user whether to implement it, and state which parts of SMS intake are missing.
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
