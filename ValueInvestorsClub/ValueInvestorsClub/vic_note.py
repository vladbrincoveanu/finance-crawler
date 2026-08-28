import re


def safe_segment(value):
    segment = re.sub(r"\s+", "_", str(value or ""))
    segment = re.sub(r"[^A-Za-z0-9._-]", "", segment)
    return segment or "unknown"


def note_path(item):
    ticker = safe_segment(item.get("ticker") or "UNKNOWN")
    date = safe_segment(item.get("date_iso") or "unknown-date")
    user = safe_segment(item.get("username") or "unknown-user")
    idea_id = safe_segment(item.get("idea_id") or "unknown-id")
    return f"vic/{ticker}/{date}__{user}__{idea_id}.md"
