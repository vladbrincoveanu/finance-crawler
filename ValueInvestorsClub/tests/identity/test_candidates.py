from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest

from ValueInvestorsClub.ValueInvestorsClub.models import Base
from ValueInvestorsClub.ValueInvestorsClub.models.identity import (
    CuratedCompany,
    CuratedSecurity,
    IdentityCandidate,
    IdentityDecision,
    SecurityAlias,
)
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import IngestionRun
from ValueInvestorsClub.ValueInvestorsClub.models.source import SourceSecurity
from ValueInvestorsClub.ValueInvestorsClub.identity.candidates import CandidateSearch


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def candidate_search(db_session):
    company = CuratedCompany(
        display_name="Berkshire Hathaway",
        normalized_name="berkshire hathaway",
    )
    security = CuratedSecurity(primary_ticker="BRK.B", company=company)
    source_security = SourceSecurity(
        source="hedgefollow",
        source_key="BRK-B",
        ticker_raw="BRK-B",
        company_name_raw="Berkshire Hathaway",
    )
    run = IngestionRun(
        source="hedgefollow",
        target="holdings",
        parser_version="test-1",
    )
    db_session.add_all([company, security, source_security, run])
    db_session.flush()
    candidate = IdentityCandidate(
        run_id=run.id,
        entity_type="security",
        source_record_id=source_security.id,
        candidate_entity_id=security.id,
        deterministic_score=1,
        evidence_json={"reason": "source alias"},
        status="approved",
    )
    db_session.add(candidate)
    db_session.flush()
    decision = IdentityDecision(
        candidate_id=candidate.id,
        entity_type="security",
        decision="approve",
        curated_entity_id=security.id,
    )
    db_session.add(decision)
    db_session.flush()
    db_session.add(
        SecurityAlias(
            source_security_id=source_security.id,
            curated_security_id=security.id,
            decision_id=decision.id,
        )
    )
    db_session.commit()
    return CandidateSearch(db_session)


def test_security_candidates_normalize_ticker_aliases(candidate_search):
    candidates = candidate_search.security_candidates(
        source="hedgefollow",
        ticker="BRK-B",
        company_name="Berkshire Hathaway",
    )

    assert candidates[0].candidate_type == "security"
    assert candidates[0].reasons
    assert len(candidates) <= 5


def test_candidate_search_can_return_no_safe_match(candidate_search, db_session):
    before = db_session.query(CuratedSecurity).count()

    assert (
        candidate_search.security_candidates("dataroma", "UNKNOWN", "Unknown Co")
        == []
    )
    assert db_session.query(CuratedSecurity).count() == before
