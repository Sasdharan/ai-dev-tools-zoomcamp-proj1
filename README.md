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

- Create, review, edit, and delete transactions in the frontend.
- Import transactions from CSV and export saved transactions as CSV.
- Run locally with SQLite or as a containerized app backed by PostgreSQL.

## Run the application with Docker Compose

Install Docker Compose, then create `.env` from `.env.example` only if `.env`
does not already exist. Keep `DATABASE_URL` pointing at SQLite for local
development; Compose ignores it and connects the backend to its PostgreSQL
service using the `POSTGRES_*` settings in `.env`:

```dotenv
DATABASE_URL=sqlite:///./expense_tracker.db
POSTGRES_DB=expense_tracker
POSTGRES_USER=expense_tracker
POSTGRES_PASSWORD=change-me-local
```

Replace the sample password with a private, URL-safe value (letters, digits,
`-`, `_`) in your local `.env`; do not commit `.env`. Start the services from
the repository root:

```powershell
docker compose --env-file .env up --build
```

The frontend is available at `http://localhost:3000`, the API documentation at
`http://localhost:8000/docs`, and the backend health check at
`http://localhost:8000/health`. Compose waits for PostgreSQL to become healthy,
runs the committed Alembic migrations, then starts the API and frontend. Stop
the services with `docker compose --env-file .env down`; the database volume is
preserved.

## Observability

The Compose stack also starts an OpenTelemetry Collector, Prometheus, Loki,
Tempo, and Grafana. Open Grafana at `http://localhost:3001` to view the
transaction API dashboard, correlate request logs with traces, and inspect the
`transaction-api-5xx` alert. Grafana is configured for anonymous local access
and bound to loopback; do not expose port `3001` beyond your trusted machine.

To verify the alert locally, briefly stop the Compose database and make a
transaction-list request to produce a controlled API 5xx, then immediately
restart the database:

```powershell
docker compose --env-file .env stop db
try {
    Invoke-WebRequest -Uri http://localhost:8000/api/v1/transactions -Method Get
} catch {
    $_.Exception.Response.StatusCode
} finally {
    docker compose --env-file .env start db
}
```

The alert should fire after evaluation and return to normal once the 5-minute
error window has cleared. Perform this check only on a local test stack, not
while the application is in active use.

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

To try the app with example data, open the frontend and use **Import CSV** to
upload one of the files in [`sample-data/`](sample-data/):

- [`test_history.csv`](sample-data/test_history.csv) uses the standard
  `Date,Amount,Merchant,Category` columns and contains four transactions.
- [`bank_export_detailed.csv`](sample-data/bank_export_detailed.csv) mimics a
  bank export with three months of salary, rent, groceries, utilities, and other
  transactions. It uses the alternative `Transaction Date`, `Description`, and
  `Expense Category` headers and adds `Currency`, `Account`, `Payment Method`,
  `Reference`, and `Notes` columns, which the importer ignores.

The backend tests import both files, so keep them valid when changing them.

## API and data

- `GET /api/v1/transactions` lists saved transactions.
- `POST /api/v1/transactions` creates a transaction with `date`, `amount`,
  `merchant`, and `category`.
- `PUT /api/v1/transactions/{transaction_id}` updates a transaction.
- `DELETE /api/v1/transactions/{transaction_id}` deletes a transaction.
- `GET /api/v1/transactions/export` downloads a CSV.
- `GET /api/v1/transactions/summary` returns spending, income, and net totals,
  spending by category, and income/spending by month. A category whose amounts
  net to a positive value (for example, Salary) counts as income. Every other
  category counts as spending, and positive amounts in it, such as refunds,
  reduce that category's spending. Monthly values are never below zero.
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

## CI/CD

GitHub Actions workflows live in `.github/workflows/`:

- `ci.yml` - backend lint (ruff) and tests (pytest), plus frontend build.
- `docker.yml` - builds the backend and frontend Docker images.

Run them locally with [act](https://github.com/nektos/act) (requires Docker; defaults are in `.actrc`):

```sh
act --list
act workflow_dispatch -W .github/workflows/ci.yml
act workflow_dispatch -W .github/workflows/docker.yml
```
