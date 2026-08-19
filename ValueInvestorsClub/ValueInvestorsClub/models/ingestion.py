from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .Base import Base


def _uuid() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'complete', 'partial', 'failed')",
            name="ck_ingestion_runs_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rows_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_duplicate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    fetches: Mapped[list[SourceFetch]] = relationship(
        "SourceFetch", back_populates="run"
    )
    holding_snapshots: Mapped[list[SourceHoldingSnapshot]] = relationship(
        "SourceHoldingSnapshot", back_populates="run"
    )
    staging_holding_snapshots: Mapped[list[StagingHoldingSnapshot]] = relationship(
        "StagingHoldingSnapshot", back_populates="run"
    )
    quarantine_records: Mapped[list[QuarantineRecord]] = relationship(
        "QuarantineRecord", back_populates="run"
    )


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "content_hash",
            name="uq_source_documents_source_content_hash",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    fetches: Mapped[list[SourceFetch]] = relationship(
        "SourceFetch", back_populates="document"
    )


class SourceFetch(Base):
    __tablename__ = "source_fetches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("source_documents.id"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)

    run: Mapped[IngestionRun] = relationship("IngestionRun", back_populates="fetches")
    document: Mapped[SourceDocument] = relationship(
        "SourceDocument", back_populates="fetches"
    )
    holding_snapshots: Mapped[list[SourceHoldingSnapshot]] = relationship(
        "SourceHoldingSnapshot", back_populates="fetch"
    )


class StagingHoldingSnapshot(Base):
    __tablename__ = "staging_holding_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "source_snapshot_id",
            name="uq_staging_holding_snapshots_run_source_snapshot",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=False
    )
    source_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("source_holding_snapshots.id"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    shares: Mapped[int | None] = mapped_column(BigInteger)
    value_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pct_portfolio: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    validation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    identity_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    reason_code: Mapped[str | None] = mapped_column(String(64))

    run: Mapped[IngestionRun] = relationship(
        "IngestionRun", back_populates="staging_holding_snapshots"
    )
    source_snapshot: Mapped[SourceHoldingSnapshot] = relationship(
        "SourceHoldingSnapshot", back_populates="staging_rows"
    )


class QuarantineRecord(Base):
    __tablename__ = "quarantine_records"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('open', 'reprocessed', 'rejected', 'accepted')",
            name="ck_quarantine_records_review_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    record_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_detail: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    run: Mapped[IngestionRun] = relationship(
        "IngestionRun", back_populates="quarantine_records"
    )
