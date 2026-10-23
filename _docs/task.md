# Backlog

## 1. Setting up an empty backend with a passing test

Goal: Create a minimal Python/FastAPI project managed by `uv` with one passing test.
Description: Set up the backend package, application entry point, and pytest configuration without adding expense-tracking features. Add one smoke test that verifies the FastAPI app can be imported and responds successfully to a health check; get approval before adding any unapproved third-party dependencies.

## 2. Configuring environment-based application settings

Goal: Load required backend settings from environment variables without hardcoded secrets or database URLs.
Description: Add an `.env.example` with documented, non-secret settings and make the app read `DATABASE_URL` from its environment. Fail clearly when required configuration is missing; do not use a hardcoded fallback.

## 3. Connecting SQLAlchemy to configured databases

Goal: Configure SQLAlchemy to use the SQLite or PostgreSQL database selected by `DATABASE_URL`.
Description: Add reusable engine and session setup for FastAPI using the configured database URL. Test local SQLite connection behavior and configuration parsing without requiring a live PostgreSQL server.

## 4. Setting up Alembic migrations

Goal: Configure Alembic to store and run database migrations from `/migrations`.
Description: Connect Alembic to the SQLAlchemy metadata and `DATABASE_URL` configuration. Verify migration discovery and status commands without creating or changing application tables.

## 5. Adding the transaction persistence model

Goal: Store transactions with date, amount, merchant, and category fields.
Description: Define the SQLAlchemy transaction model and its Alembic migration under `/migrations`, using the fields shown in the project’s CSV example. Obtain confirmation before changing the database schema, then add model and migration tests.

## 6. Creating and listing transactions through the API

Goal: Provide FastAPI endpoints to create a transaction and list saved transactions.
Description: Define validated request and response shapes for the transaction fields and persist records through SQLAlchemy. Add API tests for successful requests, invalid input, and empty results.

## 7. Updating and deleting transactions through the API

Goal: Let users update or delete an existing transaction by its identifier.
Description: Add FastAPI endpoints that persist updates and return a clear not-found response for unknown identifiers. Add tests for successful changes, invalid input, and missing records.

## 8. Importing transactions from CSV

Goal: Import valid transaction rows from a CSV file through the backend API.
Description: Support the project’s documented columns: `Date`, `Amount`, `Merchant`, and `Category`. Validate malformed files and rows, report rejected input clearly, and test valid, empty, and invalid imports.

## 9. Exporting transactions to CSV

Goal: Export saved transactions as a downloadable CSV file.
Description: Add a backend API endpoint that returns transaction data using the project’s documented CSV columns. Test the response content, headers, empty export, and values requiring CSV escaping.

## 10. Scaffolding the React and Vite frontend

Goal: Create a minimal React and Vite frontend that runs locally.
Description: Add the frontend package structure, development and build commands, and a basic page that can be served without the backend. Ask before adding third-party dependencies beyond the approved React/Vite stack.

## 11. Displaying transactions in the frontend

Goal: Show saved transactions in the React frontend using the FastAPI API.
Description: Add a transaction list view with loading, empty, and API-error states. Verify the view against a running backend and keep transaction editing and CSV workflows out of scope.

## 12. Creating transactions in the frontend

Goal: Let users submit a transaction from the React frontend.
Description: Add a form for date, amount, merchant, and category, and send validated input to the FastAPI create endpoint. Show success and validation or server errors without clearing unsaved input.

## 13. Running the application with Docker Compose

Goal: Start the containerized application and PostgreSQL database with Docker Compose.
Description: Configure the backend and PostgreSQL services to use `DATABASE_URL` from the environment, and document required setup in the committed project docs. Verify startup and backend health without committing secrets.

## 14. Defining and implementing SMS transaction intake

Goal: Accept SMS transaction data through a documented FastAPI endpoint after its contract is approved.
Description: First confirm the request fields, validation rules, and required access controls; do not assume the local handover guide defines the committed API contract. Implement persistence and tests only after the contract and any required schema changes receive approval.