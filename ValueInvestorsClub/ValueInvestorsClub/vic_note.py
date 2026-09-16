from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit

BEGIN_MARKER = "<!-- vic:begin -->"
END_MARKER = "<!-- vic:end -->"

_FRONTMATTER_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):[ \t]*(.*)$")
_MARKDOWN_ESCAPES = re.compile(r"([\\`*_[\]()!|{}~])")
_YAML_MARKDOWN_ESCAPES = "<>[]()#*`!|{}~"


def safe_segment(value: Any) -> str:
    segment = re.sub(r"\s+", "_", str(value or "").strip())
    segment = re.sub(r"[^A-Za-z0-9._-]", "", segment)
    return segment if segment and segment not in {".", ".."} else "unknown"


def _source_url(item: Mapping[str, Any]) -> str:
    for key in ("link", "url", "source_url"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _canonical_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme and parsed.netloc:
            return urlunsplit(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    parsed.path,
                    parsed.query,
                    "",
                )
            )
    except ValueError:
        pass
    return value


def canonical_identity(item: Mapping[str, Any]) -> str | None:
    idea_id = str(item.get("idea_id") or "").strip()
    if idea_id:
        identity = safe_segment(idea_id)
        if identity != "unknown":
            return identity

    source_url = _source_url(item)
    if not source_url:
        return None
    digest = hashlib.sha256(_canonical_url(source_url).encode("utf-8")).hexdigest()
    return f"url-{digest}"


def note_path(item: Mapping[str, Any]) -> str | None:
    identity = canonical_identity(item)
    if identity is None:
        return None
    ticker = safe_segment(item.get("ticker") or "UNKNOWN")
    date = safe_segment(item.get("date_iso") or "unknown-date")
    user = safe_segment(item.get("username") or "unknown-user")
    return f"vic/{ticker}/{date}__{user}__{identity}.md"


def _yaml_str(value: Any) -> str:
    serialized = json.dumps("" if value is None else str(value), ensure_ascii=True)
    for character in _YAML_MARKDOWN_ESCAPES:
        serialized = serialized.replace(character, f"\\u{ord(character):04x}")
    return serialized


def _is_true(value: Any) -> bool:
    return value is True


def _yaml_bool(value: Any) -> str:
    return "true" if _is_true(value) else "false"


def _rendered_comments(comments: Any) -> list[str]:
    rendered = []
    for comment in comments or []:
        if not isinstance(comment, Mapping):
            continue
        quoted = _blockquote(comment.get("text"))
        if not quoted:
            continue
        author = _single_line(comment.get("author")) or "anonymous"
        when = _single_line(comment.get("when"))
        header = f"**{_escape_inline(author)}**"
        if when:
            header += f" · {_escape_inline(when)}"
        rendered.append(f"{header}\n{quoted}")
    return rendered


def _frontmatter(item: Mapping[str, Any], comment_count: int | None = None) -> str:
    if comment_count is None:
        comment_count = len(_rendered_comments(item.get("comments")))
    fields = (
        ("source", _yaml_str("vic")),
        ("source_id", _yaml_str(canonical_identity(item))),
        ("url", _yaml_str(_source_url(item))),
        ("ticker", _yaml_str(item.get("ticker"))),
        ("company", _yaml_str(item.get("companyName"))),
        ("author", _yaml_str(item.get("username"))),
        ("date", _yaml_str(item.get("date_iso"))),
        ("is_short", _yaml_bool(item.get("isShort"))),
        ("is_contest_winner", _yaml_bool(item.get("isContestWinner"))),
        ("comment_count", str(comment_count)),
    )
    body = "\n".join(f"{key}: {value}" for key, value in fields)
    return f"---\n{body}\n---\n"


def _neutralize_markers(text: str) -> str:
    return text.replace("<!--", "&lt;!--").replace("-->", "--&gt;")


def _escape_markdown(text: Any) -> str:
    value = _neutralize_markers(str(text or ""))
    value = html.escape(value, quote=False)
    lines = []
    for raw_line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if re.match(r"^#{1,6}(?:\s|$)", line):
            line = "\\" + line
        if re.match(r"^(?:[-+]|\*{3,})(?:\s|$)", line):
            line = "\\" + line
        if re.match(r"^\d+[.)](?:\s|$)", line):
            line = re.sub(r"^(\d+)([.)])", r"\1\\\2", line)
        line = line.replace("%%", r"\%\%")
        line = line.replace("==", r"\=\=")
        line = re.sub(r":(?=//)", r"\:", line)
        lines.append(_MARKDOWN_ESCAPES.sub(r"\\\1", line))
    return "\n".join(lines)


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def _escape_inline(value: Any) -> str:
    return _escape_markdown(_single_line(value)).replace("\n", " ").strip()


def _paragraphs(text: Any) -> str:
    """Rejoin cleaned lines with blank lines so Markdown renders paragraphs."""
    lines = [line for line in _escape_markdown(text).split("\n") if line.strip()]
    return "\n\n".join(lines)


def _section(heading: str, text: Any) -> str:
    body = _paragraphs(text)
    if not body:
        return ""
    return f"## {heading}\n\n{body}\n\n"


def _blockquote(text: Any) -> str:
    body = _paragraphs(text)
    if not body:
        return ""
    return "\n".join(f"> {line}" if line else ">" for line in body.split("\n"))


def _discussion(comments: Any) -> str:
    blocks = _rendered_comments(comments)
    if not blocks:
        return ""
    return "## Discussion\n\n" + "\n\n".join(blocks) + "\n\n"


def _safe_http_url(value: str) -> str | None:
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        if parsed.scheme.lower() not in {"http", "https"} or not hostname:
            return None
        parsed.port
    except ValueError:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if any(char in parsed.netloc for char in '<>\\"\'()[]'):
        return None
    if not re.fullmatch(r"[A-Za-z0-9.-]+", hostname) and ":" not in hostname:
        return None
    return urlunsplit(parsed)


def _code_span(value: str) -> str:
    text = _neutralize_markers(value).replace("\r", " ").replace("\n", " ")
    runs = re.findall(r"`+", text)
    fence = "`" * (max((len(run) for run in runs), default=0) + 1)
    return f"{fence} {text} {fence}"


def _source_link(value: Any) -> str:
    source_url = _source_url({"link": value})
    safe_url = _safe_http_url(source_url)
    if safe_url is None:
        return f"Original on VIC: {_code_span(source_url)}" if source_url else "Original on VIC"
    destination = safe_url.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"[Original on VIC]({destination})"


def _body(item: Mapping[str, Any], rendered_comments: list[str] | None = None) -> str:
    company = _single_line(item.get("companyName")) or "Unknown company"
    ticker = safe_segment(item.get("ticker") or "UNKNOWN")
    author = safe_segment(item.get("username") or "unknown")
    date_iso = _single_line(item.get("date_iso"))
    side = "Short" if _is_true(item.get("isShort")) else "Long"
    if rendered_comments is None:
        rendered_comments = _rendered_comments(item.get("comments"))

    parts = [
        f"{BEGIN_MARKER}\n",
        f"# {_escape_inline(company)} ([['{ticker}']])\n\n".replace("[['", "[[").replace("']])", "]])"),
        f"Idea by [[{author}]] · {_escape_inline(date_iso)} · {side}\n\n",
        _section("Thesis", item.get("description")),
        _section("Catalysts", item.get("catalysts")),
        "## Discussion\n\n" + "\n\n".join(rendered_comments) + "\n\n" if rendered_comments else "",
        f"## Source\n\n{_source_link(item.get('link') or item.get('url') or item.get('source_url'))}\n\n",
        f"{END_MARKER}\n",
    ]
    return "".join(parts)


def render(item: Mapping[str, Any]) -> tuple[str, str] | None:
    path = note_path(item)
    if path is None:
        return None
    comments = _rendered_comments(item.get("comments"))
    return path, _frontmatter(item, len(comments)) + "\n" + _body(item, comments)


def _marker_line_bounds(text: str, marker: str, start: int = 0) -> tuple[int, int] | None:
    offset = start
    for line in text[start:].splitlines(keepends=True):
        line_start = offset
        offset += len(line)
        if line.rstrip("\r\n").strip() == marker:
            return line_start, offset
    return None


def _frontmatter_block(text: str) -> tuple[list[str], int, int] | None:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n").strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n").strip() == "---":
            end = sum(len(part) for part in lines[: index + 1])
            return lines[: index + 1], index, end
    return None


def _field_lines(block: list[str]) -> dict[str, str]:
    fields = {}
    for line in block[1:-1]:
        match = _FRONTMATTER_LINE.match(line.rstrip("\r\n"))
        if match:
            fields[match.group(1)] = line.rstrip("\r\n")
    return fields


def _merge_frontmatter(existing_prefix: str, generated_prefix: str) -> str:
    existing_block = _frontmatter_block(existing_prefix)
    generated_block = _frontmatter_block(generated_prefix)
    if existing_block is None or generated_block is None:
        return existing_prefix

    existing_lines, closing_index, existing_end = existing_block
    generated_fields = _field_lines(generated_block[0])
    seen = set()
    merged_lines = [existing_lines[0]]
    for line in existing_lines[1:closing_index]:
        match = _FRONTMATTER_LINE.match(line.rstrip("\r\n"))
        if match and match.group(1) in generated_fields:
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            merged_lines.append(generated_fields[match.group(1)] + ending)
            seen.add(match.group(1))
        else:
            merged_lines.append(line)
    ending = "\r\n" if existing_lines[-1].endswith("\r\n") else "\n" if existing_lines[-1].endswith("\n") else ""
    for key, value in generated_fields.items():
        if key not in seen and not any(
            _FRONTMATTER_LINE.match(line.rstrip("\r\n"))
            and _FRONTMATTER_LINE.match(line.rstrip("\r\n")).group(1) == key
            for line in merged_lines
        ):
            merged_lines.append(value + ending)
    merged_lines.append(existing_lines[closing_index])
    return "".join(merged_lines) + existing_prefix[existing_end:]


def merge(existing: str | None, document: str) -> str:
    """Replace generated content while keeping manual frontmatter and tail text."""
    if existing is None:
        return document
    existing_begin = _marker_line_bounds(existing, BEGIN_MARKER)
    if existing_begin is None:
        return existing
    existing_end = _marker_line_bounds(existing, END_MARKER, existing_begin[1])
    document_begin = _marker_line_bounds(document, BEGIN_MARKER)
    document_end = _marker_line_bounds(document, END_MARKER, document_begin[1]) if document_begin else None
    if existing_end is None or document_begin is None or document_end is None:
        return existing

    prefix = _merge_frontmatter(existing[: existing_begin[0]], document[: document_begin[0]])
    generated = document[document_begin[0] : document_end[1]]
    tail = existing[existing_end[1] :]
    return prefix + generated + tail
