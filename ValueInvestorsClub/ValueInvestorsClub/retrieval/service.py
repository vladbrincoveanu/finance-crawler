from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ..models.retrieval import EvidenceChunk, RetrievalRun
from .keyword import keyword_rank
from .ranking import reciprocal_rank_fusion
from .vector import cosine_similarity, embed_text


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    section_type: str
    content: str
    citation_urls: list[str]
    source_snapshot_ids: list[str]
    score: float


class RetrievalService:
    model_version = "offline-hash-embedding-v1"

    def __init__(self, session: Session):
        self.session = session

    def search(
        self,
        query: str,
        *,
        company_id: str | None = None,
        security_id: str | None = None,
        investor_id: str | None = None,
        source: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        started = time.perf_counter()
        chunks_query = self.session.query(EvidenceChunk)
        if company_id:
            chunks_query = chunks_query.filter(EvidenceChunk.company_id == company_id)
        if security_id:
            chunks_query = chunks_query.filter(EvidenceChunk.security_id == security_id)
        if investor_id:
            chunks_query = chunks_query.filter(EvidenceChunk.investor_id == investor_id)
        chunks = chunks_query.all()
        if source:
            # Source is represented by citation URL provenance in the baseline.
            chunks = [
                chunk
                for chunk in chunks
                if any(source.casefold() in url.casefold() for url in chunk.citation_urls)
            ]
        keyword_ids = keyword_rank(query, chunks)
        query_vector = embed_text(query)
        vector_ids = [
            chunk.id
            for chunk in sorted(
                chunks,
                key=lambda chunk: cosine_similarity(
                    query_vector, chunk.embedding or embed_text(chunk.content)
                ),
                reverse=True,
            )
        ]
        ranked = reciprocal_rank_fusion(keyword_ids, vector_ids)[:limit]
        by_id = {chunk.id: chunk for chunk in chunks}
        results = [
            SearchResult(
                chunk_id=ranked_chunk.chunk_id,
                section_type=by_id[ranked_chunk.chunk_id].section_type,
                content=by_id[ranked_chunk.chunk_id].content,
                citation_urls=by_id[ranked_chunk.chunk_id].citation_urls,
                source_snapshot_ids=by_id[ranked_chunk.chunk_id].source_snapshot_ids,
                score=ranked_chunk.score,
            )
            for ranked_chunk in ranked
        ]
        run = RetrievalRun(
            query=query,
            filters_json={
                "company_id": company_id,
                "security_id": security_id,
                "investor_id": investor_id,
                "source": source,
            },
            candidate_chunk_ids=[result.chunk_id for result in results],
            rank_signals={"keyword_ids": keyword_ids, "vector_ids": vector_ids},
            model_version=self.model_version,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
        self.session.add(run)
        self.session.commit()
        return results
