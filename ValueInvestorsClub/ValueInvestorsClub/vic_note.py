from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

BEGIN_MARKER = "<!-- vic:begin -->"
END_MARKER = "<!-- vic:end -->"


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
    return json.dumps(text, ensure_ascii=True)


def _yaml_bool(value: Any) -> str:
    return "true" if value is True else "false"


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


def _paragraphs(text: str) -> str:
    """Rejoin cleaned lines with blank lines so Markdown renders paragraphs."""
    lines = [line.strip() for line in (text or "").split("\n") if line.strip()]
    return "\n\n".join(lines)


def _section(heading: str, text: str) -> str:
    body = _paragraphs(text)
    if not body:
        return ""
    return f"## {heading}\n\n{body}\n\n"


def _body(item: Mapping[str, Any]) -> str:
    company = item.get("companyName") or "Unknown company"
    ticker = item.get("ticker") or "UNKNOWN"
    author = item.get("username") or "unknown"
    date_iso = item.get("date_iso") or ""
    side = "Short" if item.get("isShort") else "Long"

    parts = [
        f"{BEGIN_MARKER}\n",
        f"# {company} ([[{ticker}]])\n\n",
        f"Idea by [[{author}]] · {date_iso} · {side}\n\n",
        _section("Thesis", item.get("description") or ""),
        _section("Catalysts", item.get("catalysts") or ""),
        f"## Source\n\n[Original on VIC]({item.get('link') or ''})\n\n",
        f"{END_MARKER}\n",
    ]
    return "".join(parts)


def render(item: Mapping[str, Any]) -> tuple[str, str]:
    return note_path(item), _frontmatter(item) + "\n" + _body(item)
