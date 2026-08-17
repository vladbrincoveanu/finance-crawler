from __future__ import annotations

import hashlib
import math


def embed_text(text: str, dimensions: int = 384) -> list[float]:
    """Deterministic local embedding boundary for tests and offline development."""
    values = [0.0] * dimensions
    for token in text.casefold().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        values[index] += 1.0
    magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / magnitude for value in values]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
