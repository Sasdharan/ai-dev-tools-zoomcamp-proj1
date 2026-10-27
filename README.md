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

Use Python **3.14.7**, Node.js **24.22.1 (LTS)**, and uv **0.13.6**.
The backend's `.python-version` and frontend's `.node-version` pin the
development runtimes; select them with your version manager before running
the commands below. `uv` honors `.python-version` automatically. The Docker
images use the same Python and Node versions, and Render runs those images
without choosing separate language runtimes. CI uses the same pins and also
tests Python 3.10 to preserve the declared compatibility floor. Intermediate
Python versions are not separately tested. Application-library upgrades are
not part of this infrastructure update.

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

All backend tests (unit and integration) run with a single command:
`cd backend; uv run pytest -v`.

- **Unit tests** (`-m unit`) check settings, the database URL/driver
  selection, Alembic configuration, and the transaction model in isolation.
- **Integration tests** (`-m integration`) run the FastAPI app through
  `TestClient` against a migrated SQLite database: CRUD, CSV import/export,
  summaries, migrations, and trace/log/metric correlation.

```powershell
cd backend
uv run pytest -v
uv run pytest -m unit -v
uv run pytest -m integration -v
uv run ruff check . ..\migrations
uv run ruff format --check . ..\migrations
cd ..\frontend
npm run build
```

SMS transaction intake (issue #14) was scoped and deferred: it is not part of
the MVP, and no SMS webhook is implemented.

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

- `ci.yml` - backend lint (ruff) and tests (pytest), plus frontend build, on
  every pull request and push to `main`.
- `docker.yml` - builds the backend and frontend Docker images.
- `deploy.yml` - continuous deployment to Render:

```text
push to main -> CI (lint, tests, build)
             -> publish images to GHCR tagged with the commit SHA
             -> deploy to dev automatically + /health check
             -> manual approval (GitHub Environment "production")
             -> deploy the same images to production + /health check
```

All JavaScript Actions use Node-24-based releases. This is separate from the
Node version used to build the frontend. CI also runs the deployment helper's
regression checks, without calling Render or requiring deployment secrets.

### Rollback

Run **Actions > Deploy > Run workflow** with `image_tag` set to the commit SHA
of a previous good release. The workflow skips the build, redeploys those
existing images to dev, and after approval to production. Render's
**Rollback** button on a service is an alternative for a quick revert.

## Deployment (Render)

- Dev: `<dev frontend URL>`
- Production: `<production frontend URL>`

The app runs on [Render](https://render.com) as Docker images pulled from
GHCR. [`render.yaml`](render.yaml) defines dev and prod environments, each with
a backend web service, frontend web service, and PostgreSQL database. The
backend image runs Alembic migrations on startup, then serves on Render's
`PORT`. The frontend's nginx proxies `/api` to `BACKEND_URL`.

One-time setup:

1. Publish images once: run **Actions > Deploy** (or push to `main`) and,
   in GitHub **Packages**, make both `ai-dev-tools-zoomcamp-proj1-backend` and
   `-frontend` packages public (or add GHCR registry credentials in Render).
2. In Render, create a **Blueprint** from this repository. Set each frontend's
   `BACKEND_URL` to the public URL of the matching backend, e.g.
   `https://expense-tracker-api-dev.onrender.com`.
   If creating services manually, select **Existing Image** and enter the
   matching GHCR image URL. If an existing service fails looking for
   `./Dockerfile`, open **Settings > Build > Source > Edit**, select
   **Existing Image**, and connect the matching GHCR image instead of the Git
   repository. Changing the Blueprint file alone does not configure a
   separately created service.
3. In GitHub **Settings > Environments**, create `development` and
   `production`. Add required reviewers to `production`. In each environment
   set:
   - secrets `RENDER_DEPLOY_HOOK_API` and `RENDER_DEPLOY_HOOK_WEB` - the deploy
     hook URLs of that environment's backend and frontend services (Render
     service **Settings > Deploy Hook**);
   - variables `API_URL` (backend public URL) and `DEV_WEB_URL` /
     `PROD_WEB_URL` (frontend public URL).

Use complete HTTPS URLs without surrounding quotes or whitespace. Copy each
deploy hook directly from Render, including its `?key=...` query string.
Do not use a dashboard URL or paste hook secrets into logs, issues, or chat.
Both environments need their own configuration:

| GitHub Environment | Secrets | Variables |
| --- | --- | --- |
| `development` | `RENDER_DEPLOY_HOOK_API`, `RENDER_DEPLOY_HOOK_WEB` | `API_URL`, `DEV_WEB_URL` |
| `production` | `RENDER_DEPLOY_HOOK_API`, `RENDER_DEPLOY_HOOK_WEB` | `API_URL`, `PROD_WEB_URL` |

The workflow validates all of an environment's configuration before triggering
either service. A missing hook previously caused `curl: (3) URL rejected: Bad
hostname`; it now reports the missing setting by name without exposing values.
Secrets cannot be generated from the repository: create the Render services
first and supply their hooks in GitHub **Settings > Environments**.

The deploy helper sends URL-encoded `imgURL` parameters to select the exact
GHCR image SHA, including for rollbacks. Render's `ref` parameter is for
Git-source deployments, not these image-backed services. It then polls both
the API's `/health` and the frontend's `/`, with bounded request timeouts.
These are availability checks, not proof that Render has finished rolling
out the requested SHA; confirm the image tag and deploy status in Render.

PostgreSQL and the observability services are not upgraded here. In particular,
changing a PostgreSQL major image tag on an existing data volume is not a
safe upgrade. Compose currently uses PostgreSQL 17; verify the managed Render
database's version separately and plan a backup/migration before changing it.

Free Render web services sleep when idle, so the first request after a pause
may take about 30 seconds. Free Render PostgreSQL databases expire after 30
days. The Grafana telemetry stack runs only with Docker Compose; on Render
`OTEL_EXPORTER_OTLP_ENDPOINT` is unset and telemetry export is disabled.

### Run workflows locally

Run them locally with [act](https://github.com/nektos/act) (requires Docker; defaults are in `.actrc`):

```sh
act --list
act workflow_dispatch -W .github/workflows/ci.yml
act workflow_dispatch -W .github/workflows/docker.yml
```
