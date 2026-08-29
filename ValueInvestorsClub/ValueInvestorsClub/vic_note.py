from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


def safe_segment(value: str) -> str:
    segment = re.sub(r"\s+", "_", str(value or "").strip())
    segment = re.sub(r"[^A-Za-z0-9._-]", "", segment)
    return segment if segment and segment not in {".", ".."} else "unknown"


def note_path(item: Mapping[str, Any]) -> str:
    ticker = safe_segment(item.get("ticker") or "UNKNOWN")
    date = safe_segment(item.get("date_iso") or "unknown-date")
    user = safe_segment(item.get("username") or "unknown-user")
    idea_id = safe_segment(item.get("idea_id") or "unknown-id")
    return f"vic/{ticker}/{date}__{user}__{idea_id}.md"
