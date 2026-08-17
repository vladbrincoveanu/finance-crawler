from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .Base import Base


def _uuid() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CompanyChapter(Base):
    __tablename__ = "company_chapters"
    __table_args__ = (
        UniqueConstraint("curated_company_id", name="uq_company_chapters_company"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    curated_company_id: Mapped[str] = mapped_column(
        ForeignKey("curated_companies.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )

    chunks: Mapped[list[EvidenceChunk]] = relationship(
        "EvidenceChunk", back_populates="chapter", cascade="all, delete-orphan"
    )


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    chapter_id: Mapped[str] = mapped_column(
        ForeignKey("company_chapters.id"), nullable=False
    )
    section_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("curated_companies.id"), nullable=False
    )
    security_id: Mapped[str | None] = mapped_column(
        ForeignKey("curated_securities.id")
    )
    investor_id: Mapped[str | None] = mapped_column(
        ForeignKey("curated_investors.id")
    )
    period_start: Mapped[Any | None] = mapped_column(Date)
    period_end: Mapped[Any | None] = mapped_column(Date)
    source_snapshot_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    citation_urls: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    chapter: Mapped[CompanyChapter] = relationship(
        "CompanyChapter", back_populates="chunks"
    )


class RetrievalRun(Base):
    __tablename__ = "retrieval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    candidate_chunk_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rank_signals: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    latency_ms: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class RetrievalFeedback(Base):
    __tablename__ = "retrieval_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    retrieval_run_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_runs.id"), nullable=False
    )
    usefulness_label: Mapped[str | None] = mapped_column(String(32))
    citation_correctness_label: Mapped[str | None] = mapped_column(String(32))
    retrieved_citation_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
