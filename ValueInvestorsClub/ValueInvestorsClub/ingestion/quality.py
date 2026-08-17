from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError


_NUMERIC_FIELDS = {"shares", "value_usd", "pct_portfolio"}


def normalize_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def normalize_ticker(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().upper())


def validation_reason(error: ValidationError) -> str:
    if any(
        item.get("loc") and item["loc"][-1] in _NUMERIC_FIELDS
        for item in error.errors()
    ):
        return "invalid_numeric"
    return "invalid_observation"


def source_record_id(raw: Mapping[str, Any]) -> str:
    value = raw.get("source_record_id") or raw.get("source_observation_key")
    return str(value or "unknown")[:36]
