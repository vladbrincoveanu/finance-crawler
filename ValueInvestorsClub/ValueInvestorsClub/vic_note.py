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


def _yaml_str(value: Any) -> str:
    text = "" if value is None else str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_bool(value: Any) -> str:
    return "true" if value else "false"


def _frontmatter(item: Mapping[str, Any]) -> str:
    comments = item.get("comments") or []
    fields = (
        ("source", _yaml_str("vic")),
        ("source_id", _yaml_str(item.get("idea_id"))),
        ("url", _yaml_str(item.get("link"))),
        ("ticker", _yaml_str(item.get("ticker"))),
        ("company", _yaml_str(item.get("companyName"))),
        ("author", _yaml_str(item.get("username"))),
        ("date", _yaml_str(item.get("date_iso"))),
        ("is_short", _yaml_bool(item.get("isShort"))),
        ("is_contest_winner", _yaml_bool(item.get("isContestWinner"))),
        ("comment_count", str(len(comments))),
    )
    body = "\n".join(f"{key}: {value}" for key, value in fields)
    return f"---\n{body}\n---\n"


def render(item: Mapping[str, Any]) -> tuple[str, str]:
    return note_path(item), _frontmatter(item)
