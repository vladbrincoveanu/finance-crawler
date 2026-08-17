from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .Base import Base


def _uuid() -> str:
    return str(uuid4())


class CuratedHoldingSnapshot(Base):
    __tablename__ = "curated_holding_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "source_snapshot_id",
            name="uq_curated_holding_snapshots_source_snapshot",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("source_holding_snapshots.id"), nullable=False
    )
    curated_investor_id: Mapped[str] = mapped_column(
        ForeignKey("curated_investors.id"), nullable=False
    )
    curated_security_id: Mapped[str] = mapped_column(
        ForeignKey("curated_securities.id"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    shares: Mapped[int | None] = mapped_column(BigInteger)
    value_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pct_portfolio: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    source_activity: Mapped[str | None] = mapped_column(String(32))
    completeness: Mapped[str] = mapped_column(
        String(32), nullable=False, default="complete"
    )

    source_snapshot: Mapped[SourceHoldingSnapshot] = relationship(
        "SourceHoldingSnapshot"
    )
    curated_investor: Mapped[CuratedInvestor] = relationship(
        "CuratedInvestor", back_populates="holding_snapshots"
    )
    curated_security: Mapped[CuratedSecurity] = relationship(
        "CuratedSecurity", back_populates="holding_snapshots"
    )


class CuratedHoldingEvent(Base):
    __tablename__ = "curated_holding_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('open', 'add', 'reduce', 'hold', 'exit', 'unknown')",
            name="ck_curated_holding_events_event_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    curated_investor_id: Mapped[str] = mapped_column(
        ForeignKey("curated_investors.id"), nullable=False
    )
    curated_security_id: Mapped[str] = mapped_column(
        ForeignKey("curated_securities.id"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_snapshot_ids: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    curated_investor: Mapped[CuratedInvestor] = relationship(
        "CuratedInvestor", back_populates="holding_events"
    )
    curated_security: Mapped[CuratedSecurity] = relationship(
        "CuratedSecurity", back_populates="holding_events"
    )
