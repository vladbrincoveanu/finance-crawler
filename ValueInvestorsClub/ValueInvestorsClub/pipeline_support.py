from __future__ import annotations

from typing import Any


def scrapy_close_reason(spider: Any, reason: Any = None) -> str | None:
    """Read Scrapy's finish reason when the pipeline callback gets no argument."""
    if reason is None:
        stats = getattr(getattr(spider, "crawler", None), "stats", None)
        get_value = getattr(stats, "get_value", None)
        if callable(get_value):
            reason = get_value("finish_reason")

    normalized = str(reason).strip() if reason is not None else ""
    if normalized in {"", "finished"}:
        return None
    return normalized
