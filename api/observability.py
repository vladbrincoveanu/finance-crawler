from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


logger = logging.getLogger(__name__)


class IngestionMetrics:
    def __init__(self, exporter_url: str | None = None):
        self.exporter_url = exporter_url
        self.registry = CollectorRegistry()
        self._local: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._warned_exporter = False
        self._runs = Counter(
            "ingestion_runs",
            "Ingestion runs by source and status",
            ["source", "status"],
            registry=self.registry,
        )
        self._rows = Counter(
            "ingestion_rows",
            "Ingestion rows by source and outcome",
            ["source", "outcome"],
            registry=self.registry,
        )
        self._duration = Histogram(
            "ingestion_run_duration_seconds",
            "Ingestion run duration by source",
            ["source"],
            registry=self.registry,
        )
        self._rejection_ratio = Gauge(
            "ingestion_rejection_ratio",
            "Ingestion rejection ratio by source",
            ["source"],
            registry=self.registry,
        )
        self._database_ready = Gauge(
            "database_ready",
            "Whether the configured database is ready",
            registry=self.registry,
        )

    def record(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        normalized_labels = tuple(sorted((labels or {}).items()))
        key = (name, normalized_labels)
        self._local[key] = self._local.get(key, 0) + value

        label_values = dict(labels or {})
        if name == "ingestion_runs_total":
            self._runs.labels(
                source=label_values.get("source", "unknown"),
                status=label_values.get("status", "unknown"),
            ).inc(value)
        elif name == "ingestion_rows_total":
            self._rows.labels(
                source=label_values.get("source", "unknown"),
                outcome=label_values.get("outcome", "unknown"),
            ).inc(value)
        elif name == "ingestion_run_duration_seconds":
            self._duration.labels(source=label_values.get("source", "unknown")).observe(value)
        elif name == "ingestion_rejection_ratio":
            self._rejection_ratio.labels(source=label_values.get("source", "unknown")).set(value)
        elif name == "database_ready":
            self._database_ready.set(value)

        if self.exporter_url and not self._warned_exporter:
            logger.warning(
                "telemetry_exporter_unavailable",
                extra={"exporter_url": self.exporter_url},
            )
            self._warned_exporter = True

    def local_value(
        self, name: str, labels: Mapping[str, str] | None = None
    ) -> float:
        return self._local.get((name, tuple(sorted((labels or {}).items()))), 0)

    def render(self) -> bytes:
        return generate_latest(self.registry)


def build_metrics(exporter_url: str | None = None) -> IngestionMetrics:
    return IngestionMetrics(exporter_url=exporter_url)


metrics = build_metrics()
metrics_content_type = CONTENT_TYPE_LATEST
