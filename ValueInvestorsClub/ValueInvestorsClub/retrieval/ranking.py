from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankedChunk:
    chunk_id: str
    score: float


def reciprocal_rank_fusion(
    keyword_ids: list[str], vector_ids: list[str], k: int = 60
) -> list[RankedChunk]:
    scores: dict[str, float] = {}
    for rank, chunk_id in enumerate(keyword_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    for rank, chunk_id in enumerate(vector_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    return [
        RankedChunk(chunk_id=chunk_id, score=score)
        for chunk_id, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ]
