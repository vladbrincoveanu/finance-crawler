from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models.identity import (
    CuratedCompany,
    CuratedInvestor,
    CuratedSecurity,
    IdentityCandidate,
    InvestorAlias,
    SecurityAlias,
)
from ..models.source import SourceInvestor, SourceSecurity


def _normalize_identifier(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _normalize_name(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass(frozen=True)
class CandidateOption:
    candidate_id: str
    candidate_type: Literal["investor", "security"]
    candidate_entity_id: str
    deterministic_score: Decimal | float
    reasons: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


class CandidateSearch:
    def __init__(self, session: Session):
        self.session = session

    def security_candidates(
        self, source: str, ticker: str, company_name: str
    ) -> list[CandidateOption]:
        candidates: dict[str, CandidateOption] = {}
        normalized_ticker = _normalize_identifier(ticker)

        alias_rows = (
            self.session.query(SecurityAlias, SourceSecurity, CuratedSecurity)
            .join(SourceSecurity, SecurityAlias.source_security_id == SourceSecurity.id)
            .join(CuratedSecurity, SecurityAlias.curated_security_id == CuratedSecurity.id)
            .filter(SourceSecurity.source == source)
            .all()
        )
        for _, source_security, curated_security in alias_rows:
            source_identifiers = {
                _normalize_identifier(source_security.source_key),
                _normalize_identifier(source_security.ticker_raw),
            }
            if normalized_ticker in source_identifiers:
                candidates[curated_security.id] = CandidateOption(
                    candidate_id=curated_security.id,
                    candidate_type="security",
                    candidate_entity_id=curated_security.id,
                    deterministic_score=Decimal("1.0000"),
                    reasons=["exact_source_alias"],
                    evidence={
                        "source_security_id": source_security.id,
                        "source_key": source_security.source_key,
                    },
                )

        for curated_security in self.session.query(CuratedSecurity).all():
            if _normalize_identifier(curated_security.primary_ticker) == normalized_ticker:
                candidates.setdefault(
                    curated_security.id,
                    CandidateOption(
                        candidate_id=curated_security.id,
                        candidate_type="security",
                        candidate_entity_id=curated_security.id,
                        deterministic_score=Decimal("0.9000"),
                        reasons=["normalized_identifier"],
                        evidence={"primary_ticker": curated_security.primary_ticker},
                    ),
                )

        normalized_company = _normalize_name(company_name)
        name_rows = (
            self.session.query(CuratedSecurity, CuratedCompany)
            .join(CuratedCompany, CuratedSecurity.company_id == CuratedCompany.id)
            .all()
        )
        for curated_security, company in name_rows:
            if _normalize_name(company.normalized_name) == normalized_company:
                candidates.setdefault(
                    curated_security.id,
                    CandidateOption(
                        candidate_id=curated_security.id,
                        candidate_type="security",
                        candidate_entity_id=curated_security.id,
                        deterministic_score=Decimal("0.8000"),
                        reasons=["normalized_company_name"],
                        evidence={"company_name": company.display_name},
                    ),
                )

        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            try:
                fuzzy_rows = (
                    self.session.query(CuratedSecurity, CuratedCompany)
                    .join(CuratedCompany, CuratedSecurity.company_id == CuratedCompany.id)
                    .filter(func.similarity(CuratedCompany.normalized_name, normalized_company) >= 0.35)
                    .order_by(func.similarity(CuratedCompany.normalized_name, normalized_company).desc())
                    .limit(5)
                    .all()
                )
                for curated_security, company in fuzzy_rows:
                    candidates.setdefault(
                        curated_security.id,
                        CandidateOption(
                            candidate_id=curated_security.id,
                            candidate_type="security",
                            candidate_entity_id=curated_security.id,
                            deterministic_score=Decimal("0.3500"),
                            reasons=["trigram_company_similarity"],
                            evidence={"company_name": company.display_name},
                        ),
                    )
            except SQLAlchemyError:
                self.session.rollback()

        return sorted(
            candidates.values(),
            key=lambda candidate: candidate.deterministic_score,
            reverse=True,
        )[:5]

    def investor_candidates(self, source_record_id: str) -> list[CandidateOption]:
        source_investor = self.session.get(SourceInvestor, source_record_id)
        if source_investor is None:
            return []

        candidates: dict[str, CandidateOption] = {}
        alias_rows = (
            self.session.query(InvestorAlias, CuratedInvestor)
            .join(
                CuratedInvestor,
                InvestorAlias.curated_investor_id == CuratedInvestor.id,
            )
            .filter(InvestorAlias.source_investor_id == source_record_id)
            .all()
        )
        for _, curated_investor in alias_rows:
            candidates[curated_investor.id] = CandidateOption(
                candidate_id=curated_investor.id,
                candidate_type="investor",
                candidate_entity_id=curated_investor.id,
                deterministic_score=Decimal("1.0000"),
                reasons=["exact_source_alias"],
                evidence={"source_investor_id": source_record_id},
            )

        normalized_name = _normalize_name(source_investor.name_normalized)
        for curated_investor in self.session.query(CuratedInvestor).all():
            if _normalize_name(curated_investor.normalized_name) == normalized_name:
                candidates.setdefault(
                    curated_investor.id,
                    CandidateOption(
                        candidate_id=curated_investor.id,
                        candidate_type="investor",
                        candidate_entity_id=curated_investor.id,
                        deterministic_score=Decimal("0.8000"),
                        reasons=["normalized_name"],
                        evidence={"source_name": source_investor.name_raw},
                    ),
                )
        return sorted(
            candidates.values(),
            key=lambda candidate: candidate.deterministic_score,
            reverse=True,
        )[:5]

    def persist_candidates(
        self,
        run_id: str,
        entity_type: Literal["investor", "security"],
        source_record_id: str,
        candidates: list[CandidateOption],
    ) -> list[IdentityCandidate]:
        rows = [
            IdentityCandidate(
                run_id=run_id,
                entity_type=entity_type,
                source_record_id=source_record_id,
                candidate_entity_id=candidate.candidate_entity_id,
                deterministic_score=candidate.deterministic_score,
                evidence_json={
                    "reasons": candidate.reasons,
                    **candidate.evidence,
                },
                status="pending",
            )
            for candidate in candidates
        ]
        self.session.add_all(rows)
        self.session.commit()
        return rows
