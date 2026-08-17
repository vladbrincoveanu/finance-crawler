from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from collections.abc import Iterator, Mapping
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


logger = logging.getLogger(__name__)
_tracer = trace.get_tracer("value-investors-club")


def configure_telemetry() -> None:
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": os.getenv("OTEL_SERVICE_NAME", "value-investors-club-api"),
            }
        )
    )
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        try:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
            )
        except Exception as error:  # exporter setup must not block the API
            logger.warning(
                "telemetry_exporter_setup_failed",
                extra={"error": str(error), "endpoint": endpoint},
            )
    trace.set_tracer_provider(provider)


@contextmanager
def span(name: str, attributes: Mapping[str, Any] | None = None) -> Iterator[None]:
    with _tracer.start_as_current_span(name, attributes=dict(attributes or {})):
        yield


def log_event(logger_instance: logging.Logger, event: str, **fields: Any) -> None:
    logger_instance.info(
        json.dumps({"event": event, **fields}, default=str, sort_keys=True)
    )
