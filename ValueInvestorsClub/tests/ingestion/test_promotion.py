from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base
from ValueInvestorsClub.ValueInvestorsClub.models.curated import CuratedHoldingSnapshot
from ValueInvestorsClub.ValueInvestorsClub.models.identity import (
    CuratedCompany,
    CuratedInvestor,
    CuratedSecurity,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import (
    SourceHoldingSnapshot,
    SourceInvestor,
    SourceSecurity,
)
from ValueInvestorsClub.ValueInvestorsClub.ingestion import (
    ApprovedMapping,
    IngestionService,
    SourceHoldingObservation,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def service(db_session):
    return IngestionService(db_session)


def observation(key, security_key, ticker, shares=100):
    return SourceHoldingObservation(
        source="dataroma",
        investor_key="BRK",
        investor_name="Berkshire Hathaway",
        security_key=security_key,
        ticker=ticker,
        company_name="Apple Inc." if ticker == "AAPL" else "Microsoft Corp.",
        period=date(2026, 6, 30),
        shares=shares,
        value_usd=1000,
        pct_portfolio=2.5,
        source_activity="hold",
        source_url="https://example.test/holdings/BRK",
        source_observation_key=key,
        document_hash="b" * 64,
        raw_payload={"key": key},
    )


def test_promotion_excludes_unresolved_rows(service, db_session):
    run = service.start_run("dataroma", "holdings", "test-1")
    service.stage(run, observation("dataroma:BRK:AAPL:2026-06-30", "AAPL", "AAPL"))
    service.stage(run, observation("dataroma:BRK:MSFT:2026-06-30", "MSFT", "MSFT"))

    source_investor = db_session.query(SourceInvestor).one()
    source_security = (
        db_session.query(SourceSecurity)
        .filter_by(source_key="AAPL")
        .one()
    )
    curated_investor = CuratedInvestor(
        display_name="Berkshire Hathaway", normalized_name="berkshire hathaway"
    )
    curated_company = CuratedCompany(
        display_name="Apple Inc.", normalized_name="apple inc"
    )
    curated_security = CuratedSecurity(
        primary_ticker="AAPL", company=curated_company
    )
    db_session.add_all([curated_investor, curated_company, curated_security])
    db_session.commit()

    promoted = service.promote(
        run_id=run.id,
        approved_mappings=[
            ApprovedMapping(
                source_investor_id=source_investor.id,
                curated_investor_id=curated_investor.id,
                source_security_id=source_security.id,
                curated_security_id=curated_security.id,
            )
        ],
    )

    assert promoted.accepted == 1
    assert promoted.pending_identity == 1
    assert service.public_curated_count() == 1
    unresolved = (
        db_session.query(SourceHoldingSnapshot)
        .filter(SourceHoldingSnapshot.source_security_id != source_security.id)
        .one()
    )
    assert db_session.query(CuratedHoldingSnapshot).one().source_snapshot_id != unresolved.id


def test_event_projection_marks_missing_period_as_unknown(service):
    snapshots = [
        CuratedHoldingSnapshot(
            id="snapshot-2025",
            source_snapshot_id="source-2025",
            curated_investor_id="investor-1",
            curated_security_id="security-1",
            period=date(2025, 12, 31),
            shares=100,
        ),
        CuratedHoldingSnapshot(
            id="snapshot-2026",
            source_snapshot_id="source-2026",
            curated_investor_id="investor-1",
            curated_security_id="security-1",
            period=date(2026, 6, 30),
            shares=120,
        ),
    ]

    events = service.project_events(snapshots)

    assert any(event.event_type == "unknown" for event in events)
    assert all(event.event_type != "exit" for event in events)
