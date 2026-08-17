from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.orm import Session

from ..models.identity import (
    CuratedCompany,
    CuratedInvestor,
    CuratedSecurity,
    IdentityCandidate,
    IdentityDecision,
    InvestorAlias,
    SecurityAlias,
)
from ..models.source import SourceInvestor, SourceSecurity
from ..ingestion.quality import normalize_name, normalize_ticker


class DecisionService:
    def __init__(self, session: Session):
        self.session = session

    def record_human_decision(
        self,
        candidate_id: str,
        decision: Literal["approve", "reject", "defer", "create_new"],
        *,
        curated_entity_id: str | None = None,
        reviewer_id: str | None = None,
    ) -> IdentityDecision:
        candidate = self.session.get(IdentityCandidate, candidate_id)
        if candidate is None:
            raise ValueError(f"Unknown identity candidate: {candidate_id}")
        if decision == "approve" and not curated_entity_id:
            raise ValueError("approve requires curated_entity_id")

        audit = IdentityDecision(
            candidate_id=candidate.id,
            entity_type=candidate.entity_type,
            decision=decision,
            curated_entity_id=curated_entity_id,
            reviewer_id=reviewer_id,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        self.session.flush()

        if decision == "create_new":
            curated_entity_id = self._create_canonical_entity(candidate)
            audit.curated_entity_id = curated_entity_id
        if decision in {"approve", "create_new"}:
            if not curated_entity_id:
                raise ValueError("approved identity decision requires canonical entity")
            self._write_alias(candidate, curated_entity_id, audit.id)

        candidate.status = "approved" if decision in {"approve", "create_new"} else decision
        self.session.commit()
        return audit

    def _create_canonical_entity(self, candidate: IdentityCandidate) -> str:
        if candidate.entity_type == "investor":
            source_investor = self.session.get(SourceInvestor, candidate.source_record_id)
            if source_investor is None:
                raise ValueError("source investor record is missing")
            entity = CuratedInvestor(
                display_name=source_investor.name_raw,
                normalized_name=normalize_name(source_investor.name_normalized),
            )
        elif candidate.entity_type == "security":
            source_security = self.session.get(SourceSecurity, candidate.source_record_id)
            if source_security is None:
                raise ValueError("source security record is missing")
            company = CuratedCompany(
                display_name=source_security.company_name_raw,
                normalized_name=normalize_name(source_security.company_name_raw),
            )
            entity = CuratedSecurity(
                primary_ticker=normalize_ticker(source_security.ticker_raw),
                company=company,
            )
        else:
            raise ValueError(f"unsupported identity entity type: {candidate.entity_type}")
        self.session.add(entity)
        self.session.flush()
        return entity.id

    def _write_alias(
        self, candidate: IdentityCandidate, curated_entity_id: str, decision_id: str
    ) -> None:
        if candidate.entity_type == "investor":
            alias = self.session.get(InvestorAlias, candidate.source_record_id)
            if alias is None:
                alias = InvestorAlias(source_investor_id=candidate.source_record_id)
                self.session.add(alias)
            alias.curated_investor_id = curated_entity_id
            alias.decision_id = decision_id
        elif candidate.entity_type == "security":
            alias = self.session.get(SecurityAlias, candidate.source_record_id)
            if alias is None:
                alias = SecurityAlias(source_security_id=candidate.source_record_id)
                self.session.add(alias)
            alias.curated_security_id = curated_entity_id
            alias.decision_id = decision_id
