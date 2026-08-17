from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
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


class SourceInvestor(Base):
    __tablename__ = "source_investors"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_key",
            name="uq_source_investors_source_source_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str] = mapped_column(String(256), nullable=False)
    name_raw: Mapped[str] = mapped_column(String(512), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(512), nullable=False)
    profile_url: Mapped[str | None] = mapped_column(String(2048))

    portfolio_managers: Mapped[list[SourcePortfolioManager]] = relationship(
        "SourcePortfolioManager", back_populates="source_investor"
    )
    holding_snapshots: Mapped[list[SourceHoldingSnapshot]] = relationship(
        "SourceHoldingSnapshot", back_populates="source_investor"
    )
    aliases: Mapped[list[InvestorAlias]] = relationship(
        "InvestorAlias", back_populates="source_investor"
    )


class SourcePortfolioManager(Base):
    __tablename__ = "source_portfolio_managers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_investor_id: Mapped[str] = mapped_column(
        ForeignKey("source_investors.id"), nullable=False
    )
    name_raw: Mapped[str] = mapped_column(String(512), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))

    source_investor: Mapped[SourceInvestor] = relationship(
        "SourceInvestor", back_populates="portfolio_managers"
    )


class SourceSecurity(Base):
    __tablename__ = "source_securities"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_key",
            name="uq_source_securities_source_source_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str] = mapped_column(String(256), nullable=False)
    ticker_raw: Mapped[str] = mapped_column(String(128), nullable=False)
    company_name_raw: Mapped[str] = mapped_column(String(512), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(64))
    share_class: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(2048))

    holding_snapshots: Mapped[list[SourceHoldingSnapshot]] = relationship(
        "SourceHoldingSnapshot", back_populates="source_security"
    )
    aliases: Mapped[list[SecurityAlias]] = relationship(
        "SecurityAlias", back_populates="source_security"
    )


class SourceHoldingSnapshot(Base):
    __tablename__ = "source_holding_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_observation_key",
            name="uq_source_holding_snapshots_source_observation_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_investor_id: Mapped[str] = mapped_column(
        ForeignKey("source_investors.id"), nullable=False
    )
    source_security_id: Mapped[str] = mapped_column(
        ForeignKey("source_securities.id"), nullable=False
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    shares: Mapped[int | None] = mapped_column(BigInteger)
    value_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pct_portfolio: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    source_activity: Mapped[str | None] = mapped_column(String(32))
    source_observation_key: Mapped[str] = mapped_column(String(512), nullable=False)
    fetch_id: Mapped[str | None] = mapped_column(ForeignKey("source_fetches.id"))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    run: Mapped[IngestionRun | None] = relationship(
        "IngestionRun", back_populates="holding_snapshots"
    )
    source_investor: Mapped[SourceInvestor] = relationship(
        "SourceInvestor", back_populates="holding_snapshots"
    )
    source_security: Mapped[SourceSecurity] = relationship(
        "SourceSecurity", back_populates="holding_snapshots"
    )
    fetch: Mapped[SourceFetch | None] = relationship(
        "SourceFetch", back_populates="holding_snapshots"
    )
    staging_rows: Mapped[list[StagingHoldingSnapshot]] = relationship(
        "StagingHoldingSnapshot", back_populates="source_snapshot"
    )
