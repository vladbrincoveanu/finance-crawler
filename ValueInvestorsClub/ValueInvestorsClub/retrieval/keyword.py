from __future__ import annotations

import re
from collections.abc import Iterable


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def keyword_rank(query: str, chunks: Iterable) -> list[str]:
    query_tokens = _tokens(query)
    scored = []
    for chunk in chunks:
        overlap = len(query_tokens & _tokens(chunk.content))
        if overlap:
            scored.append((overlap, chunk.id))
    return [chunk_id for _, chunk_id in sorted(scored, key=lambda item: (-item[0], item[1]))]
