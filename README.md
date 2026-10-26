# Personal Expense Tracker

I started this project because the expense tracker I relied on reached end of
life and lost official support. Rather than simply look for another app, I
decided to build a small replacement that I can run and maintain myself. It has
also been a chance to put the tools and ideas from the Zoomcamp project into
practice.

The goal is a straightforward personal expense tracker: save transactions,
review them in a simple frontend, and move existing records in or out with CSV.
The React/Vite frontend talks to a FastAPI backend. SQLite is available for
local development, while Docker Compose runs the app with PostgreSQL.

## What it can do

- Create and review transactions in the frontend.
- Import transactions from CSV and export saved transactions as CSV.
- Run locally with SQLite or as a containerized app backed by PostgreSQL.

## Run the application with Docker Compose

Install Docker Compose, then create `.env` from `.env.example` only if `.env`
does not already exist. Set `DATABASE_URL` in `.env` to the PostgreSQL service
URL and make its password match `POSTGRES_PASSWORD`:

```dotenv
DATABASE_URL=postgresql+psycopg2://expense_tracker:change-me-local@db:5432/expense_tracker
POSTGRES_DB=expense_tracker
POSTGRES_USER=expense_tracker
POSTGRES_PASSWORD=change-me-local
```

Replace the sample password with a private value in your local `.env`; do not
commit `.env`. The URL must use the same database, username, and password as
the PostgreSQL settings. Start the services from the repository root:

```powershell
docker compose --env-file .env up --build
```

The frontend is available at `http://localhost:3000`, the API documentation at
`http://localhost:8000/docs`, and the backend health check at
`http://localhost:8000/health`. Compose waits for PostgreSQL to become healthy,
runs the committed Alembic migrations, then starts the API and frontend. Stop
the services with `docker compose --env-file .env down`; the database volume is
preserved.

## Local development

Ensure the root `.env` exists; copy `.env.example` only if it is missing. For
local SQLite use, keep `DATABASE_URL=sqlite:///./expense_tracker.db` from
`.env.example`. Install and migrate the backend, then run it:

```powershell
cd backend
uv sync
uv run alembic -c ..\alembic.ini upgrade head
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal, start the Vite frontend. Its `/api` requests are proxied to
`http://localhost:8000` by default; set `API_PROXY_TARGET` to use a different
backend address.

```powershell
cd frontend
npm ci
npm run dev
```

## API and data

- `GET /api/v1/transactions` lists saved transactions.
- `POST /api/v1/transactions` creates a transaction with `date`, `amount`,
  `merchant`, and `category`.
- `GET /api/v1/transactions/export` downloads a CSV.
- `POST /api/v1/transactions/import` imports a CSV.

CSV uses `Date,Amount,Merchant,Category` columns. Schema changes are applied
only through Alembic migration scripts in `migrations/`.

## Validation

```powershell
cd backend
uv run pytest -v
uv run ruff check . ..\migrations
uv run ruff format --check . ..\migrations
cd ..\frontend
npm run build
```

SMS transaction intake (issue 14) remains out of scope for the MVP until that
contract and behavior are agreed.

## Future implementation direction

SMS-based transaction intake is a possible follow-up, not part of the current
MVP. The intended high-level flow is:

1. A user-configured phone automation detects a relevant SMS and sends it to a
   backend webhook.
2. The backend validates the request and parses the message into the existing
   transaction fields: date, amount, merchant, and category.
3. The backend stores valid transactions through the existing SQLAlchemy
   transaction flow, so they appear in the frontend and CSV exports like
   manually created transactions.
4. Invalid or unrecognized messages receive a clear error and are not silently
   saved as transactions.

Before implementing this, define and document the webhook path and payload,
how callers are authenticated, and how message formats are parsed. Those
details are intentionally undecided: there is currently no SMS webhook or
payload contract. Keep the work behind tests for valid messages, invalid or
ambiguous messages, and duplicate delivery; any schema changes must use
Alembic migrations.

