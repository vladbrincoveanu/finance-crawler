from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CuratedInvestor(Base):
    __tablename__ = "curated_investors"
    __table_args__ = (
        UniqueConstraint(
            "normalized_name",
            name="uq_curated_investors_normalized_name",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    manager_links: Mapped[list[CuratedInvestorManager]] = relationship(
        "CuratedInvestorManager", back_populates="investor"
    )
    aliases: Mapped[list[InvestorAlias]] = relationship(
        "InvestorAlias", back_populates="curated_investor"
    )
    holding_snapshots: Mapped[list[CuratedHoldingSnapshot]] = relationship(
        "CuratedHoldingSnapshot", back_populates="curated_investor"
    )
    holding_events: Mapped[list[CuratedHoldingEvent]] = relationship(
        "CuratedHoldingEvent", back_populates="curated_investor"
    )


class PortfolioManager(Base):
    __tablename__ = "portfolio_managers"
    __table_args__ = (
        UniqueConstraint(
            "normalized_name",
            name="uq_portfolio_managers_normalized_name",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(512), nullable=False)

    investor_links: Mapped[list[CuratedInvestorManager]] = relationship(
        "CuratedInvestorManager", back_populates="manager"
    )


class CuratedCompany(Base):
    __tablename__ = "curated_companies"
    __table_args__ = (
        UniqueConstraint(
            "normalized_name",
            name="uq_curated_companies_normalized_name",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    securities: Mapped[list[CuratedSecurity]] = relationship(
        "CuratedSecurity", back_populates="company"
    )


class CuratedSecurity(Base):
    __tablename__ = "curated_securities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("curated_companies.id"), nullable=False
    )
    primary_ticker: Mapped[str] = mapped_column(String(128), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(64))
    share_class: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    company: Mapped[CuratedCompany] = relationship(
        "CuratedCompany", back_populates="securities"
    )
    aliases: Mapped[list[SecurityAlias]] = relationship(
        "SecurityAlias", back_populates="curated_security"
    )
    holding_snapshots: Mapped[list[CuratedHoldingSnapshot]] = relationship(
        "CuratedHoldingSnapshot", back_populates="curated_security"
    )
    holding_events: Mapped[list[CuratedHoldingEvent]] = relationship(
        "CuratedHoldingEvent", back_populates="curated_security"
    )


class CuratedInvestorManager(Base):
    __tablename__ = "curated_investor_managers"

    investor_id: Mapped[str] = mapped_column(
        ForeignKey("curated_investors.id"), primary_key=True
    )
    manager_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_managers.id"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    evidence_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("source_documents.id")
    )

    investor: Mapped[CuratedInvestor] = relationship(
        "CuratedInvestor", back_populates="manager_links"
    )
    manager: Mapped[PortfolioManager] = relationship(
        "PortfolioManager", back_populates="investor_links"
    )


class IdentityCandidate(Base):
    __tablename__ = "identity_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(36), nullable=False)
    candidate_entity_id: Mapped[str | None] = mapped_column(String(36))
    deterministic_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    model_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    run: Mapped[IngestionRun] = relationship("IngestionRun")
    decisions: Mapped[list[IdentityDecision]] = relationship(
        "IdentityDecision", back_populates="candidate"
    )


class IdentityDecision(Base):
    __tablename__ = "identity_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approve', 'reject', 'defer', 'create_new')",
            name="ck_identity_decisions_decision",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("identity_candidates.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    curated_entity_id: Mapped[str | None] = mapped_column(String(36))
    reviewer_id: Mapped[str | None] = mapped_column(String(36))
    model_name: Mapped[str | None] = mapped_column(String(256))
    model_version: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    candidate: Mapped[IdentityCandidate] = relationship(
        "IdentityCandidate", back_populates="decisions"
    )


class InvestorAlias(Base):
    __tablename__ = "investor_aliases"

    source_investor_id: Mapped[str] = mapped_column(
        ForeignKey("source_investors.id"), primary_key=True
    )
    curated_investor_id: Mapped[str] = mapped_column(
        ForeignKey("curated_investors.id"), nullable=False
    )
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("identity_decisions.id"), nullable=False
    )

    source_investor: Mapped[SourceInvestor] = relationship(
        "SourceInvestor", back_populates="aliases"
    )
    curated_investor: Mapped[CuratedInvestor] = relationship(
        "CuratedInvestor", back_populates="aliases"
    )
    decision: Mapped[IdentityDecision] = relationship("IdentityDecision")


class SecurityAlias(Base):
    __tablename__ = "security_aliases"

    source_security_id: Mapped[str] = mapped_column(
        ForeignKey("source_securities.id"), primary_key=True
    )
    curated_security_id: Mapped[str] = mapped_column(
        ForeignKey("curated_securities.id"), nullable=False
    )
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("identity_decisions.id"), nullable=False
    )

    source_security: Mapped[SourceSecurity] = relationship(
        "SourceSecurity", back_populates="aliases"
    )
    curated_security: Mapped[CuratedSecurity] = relationship(
        "CuratedSecurity", back_populates="aliases"
    )
    decision: Mapped[IdentityDecision] = relationship("IdentityDecision")
