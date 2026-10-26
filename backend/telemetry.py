import atexit
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    InMemoryMetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.engine import Engine

REQUEST_LOGGER = logging.getLogger("expense_tracker.request")
tracer_provider: TracerProvider
meter_provider: MeterProvider
metric_reader: InMemoryMetricReader | PeriodicExportingMetricReader
logger_provider: LoggerProvider
_shutdown_registered = False


class _StructuredRequestFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = (
            "http_method",
            "http_route",
            "http_status_code",
            "duration_ms",
            "trace_id",
            "span_id",
        )
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        payload.update(
            {
                field: getattr(record, field)
                for field in fields
                if hasattr(record, field)
            }
        )
        return json.dumps(payload, separators=(",", ":"))


def _transaction_route(path: str) -> str:
    base_path = "/api/v1/transactions"
    if path in {
        base_path,
        f"{base_path}/export",
        f"{base_path}/import",
    }:
        return path
    if path.startswith(f"{base_path}/"):
        return f"{base_path}/{{transaction_id}}"
    return "/unmatched"


def _sanitize_server_request_span(span: Any, scope: dict[str, Any]) -> None:
    if span is None or not span.is_recording():
        return

    route = _transaction_route(scope.get("path", ""))
    span.set_attribute("http.route", route)
    span.set_attribute("url.path", route)
    span.set_attribute("url.query", "")
    span.set_attribute("url.full", f"http://localhost{route}")
    span.set_attribute("http.target", route)
    span.set_attribute("http.url", f"http://localhost{route}")


def _configure_request_logging(app: FastAPI) -> None:
    REQUEST_LOGGER.setLevel(logging.INFO)
    REQUEST_LOGGER.propagate = False
    if not any(
        isinstance(handler, logging.StreamHandler)
        for handler in REQUEST_LOGGER.handlers
    ):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(_StructuredRequestFormatter())
        REQUEST_LOGGER.addHandler(stream_handler)

    @app.middleware("http")
    async def log_transaction_request(request: Request, call_next: Any) -> Any:
        if not request.url.path.startswith("/api/v1/transactions"):
            return await call_next(request)

        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", None)
            safe_route = route or _transaction_route(request.url.path)
            span = trace.get_current_span()
            span_context = span.get_span_context()
            trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else ""
            span_id = f"{span_context.span_id:016x}" if span_context.is_valid else ""

            if span.is_recording():
                span.set_attribute("http.route", safe_route)
                span.set_attribute("url.path", safe_route)
                span.set_attribute("url.query", "")
                span.set_attribute("url.full", f"http://localhost{safe_route}")
                span.set_attribute("http.target", safe_route)
                span.set_attribute("http.url", f"http://localhost{safe_route}")

            REQUEST_LOGGER.info(
                "transaction_api_request",
                extra={
                    "http_method": request.method,
                    "http_route": safe_route,
                    "http_status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
                    "trace_id": trace_id,
                    "span_id": span_id,
                },
            )


def configure_telemetry(app: FastAPI, engine: Engine) -> None:
    global _shutdown_registered, logger_provider, meter_provider, metric_reader
    global tracer_provider

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    resource = Resource.create(
        {
            "service.name": os.environ.get(
                "OTEL_SERVICE_NAME", "personal-expense-tracker-api"
            )
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    if endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
    trace.set_tracer_provider(tracer_provider)

    if endpoint:
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint),
            export_interval_millis=10_000,
        )
    else:
        metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    if endpoint:
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint))
        )
        REQUEST_LOGGER.addHandler(
            LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        )

    LoggingInstrumentor().instrument(set_logging_format=False)
    _configure_request_logging(app)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        excluded_urls=r"/health$",
        http_capture_headers_server_request=[],
        http_capture_headers_server_response=[],
        server_request_hook=_sanitize_server_request_span,
    )
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        enable_commenter=False,
        enable_attribute_commenter=False,
    )
    if not _shutdown_registered:
        atexit.register(_shutdown_telemetry)
        _shutdown_registered = True


def _shutdown_telemetry() -> None:
    logger_provider.shutdown()
    meter_provider.shutdown()
    tracer_provider.shutdown()
