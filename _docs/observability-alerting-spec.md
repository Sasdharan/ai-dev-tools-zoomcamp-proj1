# Observability and User-Impact Alerting

## Status

Scope approved and implemented. The final end-to-end alert verification is
tracked against the acceptance criteria below.

## Goal

Make failures in the core expense-tracking journey observable and alert on
failed user-facing API requests. Keep telemetry self-hosted and avoid sending
transaction data or credentials to observability services.

## Scope

- Instrument the existing transaction create and list journey:
  `POST /api/v1/transactions` and `GET /api/v1/transactions`.
- Collect correlated traces, metrics, and structured logs for those requests,
  including SQLAlchemy database work.
- Store and view telemetry in Grafana using Prometheus, Loki, and Tempo, with
  an OpenTelemetry Collector receiving telemetry from the backend.
- Provision a Grafana alert for server errors on transaction API routes.
- Document how to start the stack, access Grafana, and verify the alert.
- Keep existing application behavior and data model unchanged.

## Design

1. The FastAPI backend emits OpenTelemetry signals to an OpenTelemetry
   Collector over OTLP on the internal Compose network.
2. The collector forwards metrics to Prometheus, logs to Loki, and traces to
   Tempo.
3. Grafana provides the UI, with the three data sources configured and linked
   using trace IDs.
4. The Grafana host port must not conflict with the frontend's existing port
   `3000`; expose Grafana on a separate documented port.
5. Telemetry must not include transaction amounts, merchant or category values,
   request/response bodies, credentials, or other user-provided transaction
   data. Do not use transaction IDs, trace IDs, or other unbounded values as
   metric labels.

The key signals are HTTP request count, error count, and latency, plus request
and database spans and structured request logs. Trace IDs must be present in
the corresponding logs and traces so a single request can be followed in
Grafana.

## User-impact alert

- **Rule:** `transaction-api-5xx`
- **Signal:** At least one HTTP 5xx response from a transaction API route in
  the preceding five minutes.
- **Destination:** Grafana Alerting UI. No email, webhook, or other external
  notification service is required for this scope.
- **Excluded signals:** CPU, memory, and health-check failures alone do not
  satisfy this alert requirement.

## Acceptance criteria

1. The backend and observability stack can be started together through the
   documented Docker Compose workflow.
2. A successful create or list request appears in Grafana with an HTTP trace,
   database span where applicable, and a structured log sharing its trace ID.
3. Grafana displays request volume, 5xx errors, and request latency for the
   transaction API, without transaction-specific values in telemetry.
4. A controlled 5xx from a transaction API route causes the alert to enter the
   firing state in Grafana; it returns to normal after the five-minute window
   clears.
5. Tests or verification steps cover telemetry correlation, the alert
   condition, and the absence of sensitive transaction fields in telemetry.
6. Existing backend tests and lint checks continue to pass; the frontend build
   remains unaffected.

## Non-goals

- An on-call or remediation agent.
- Automatic code changes, restarts, or self-healing in response to alerts.
- SaaS telemetry, external notification destinations, or transmitting
  transaction data to third parties.
- Database schema changes.
- Infrastructure saturation alerts unrelated to user impact.

## Implementation sequence

1. Confirm the exact OpenTelemetry Python packages and versions before changing
   dependency manifests.
2. Add backend instrumentation and focused tests for trace/log correlation and
   sensitive-data exclusion.
3. Add the Collector, Prometheus, Loki, Tempo, and Grafana Compose
   configuration, including Grafana data sources and the alert rule.
4. Verify the full stack with a successful transaction request and a controlled
   5xx, then update the run and verification documentation.
