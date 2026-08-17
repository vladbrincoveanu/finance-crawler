from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

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


def test_curated_security_belongs_to_company(db_session):
    company = CuratedCompany(
        display_name="Berkshire Hathaway",
        normalized_name="berkshire hathaway",
    )
    security = CuratedSecurity(
        primary_ticker="BRK.B",
        company=company,
        share_class="B",
    )
    investor = CuratedInvestor(
        display_name="Berkshire Hathaway",
        normalized_name="berkshire hathaway",
    )
    db_session.add_all([company, security, investor])
    db_session.commit()

    assert security.company.display_name == "Berkshire Hathaway"
    assert investor.display_name == "Berkshire Hathaway"


def test_source_observation_retains_source_identity_and_period(db_session):
    source_investor = SourceInvestor(
        source="dataroma",
        source_key="BRK",
        name_raw="Warren Buffett - Berkshire Hathaway",
        name_normalized="warren buffett berkshire hathaway",
    )
    source_security = SourceSecurity(
        source="dataroma",
        source_key="AAPL",
        ticker_raw="AAPL",
        company_name_raw="Apple Inc.",
    )
    observation = SourceHoldingSnapshot(
        source="dataroma",
        source_investor=source_investor,
        source_security=source_security,
        period=date(2026, 6, 30),
        shares=227917808,
        value_usd=Decimal("65950296000.00"),
        pct_portfolio=Decimal("22.04"),
        source_activity="hold",
        source_observation_key="dataroma:BRK:AAPL:2026-06-30",
    )
    db_session.add(observation)
    db_session.commit()

    assert db_session.query(SourceHoldingSnapshot).count() == 1
    assert observation.source == "dataroma"
    assert observation.source_observation_key.endswith("2026-06-30")
    assert observation.period == date(2026, 6, 30)
    assert observation.source_activity == "hold"


def test_duplicate_source_observation_key_raises_integrity_error(db_session):
    source_investor = SourceInvestor(
        source="dataroma",
        source_key="BRK",
        name_raw="Berkshire Hathaway",
        name_normalized="berkshire hathaway",
    )
    source_security = SourceSecurity(
        source="dataroma",
        source_key="AAPL",
        ticker_raw="AAPL",
        company_name_raw="Apple Inc.",
    )
    first = SourceHoldingSnapshot(
        source="dataroma",
        source_investor=source_investor,
        source_security=source_security,
        period=date(2026, 6, 30),
        source_observation_key="dataroma:BRK:AAPL:2026-06-30",
    )
    second = SourceHoldingSnapshot(
        source="dataroma",
        source_investor=source_investor,
        source_security=source_security,
        period=date(2026, 6, 30),
        source_observation_key="dataroma:BRK:AAPL:2026-06-30",
    )
    db_session.add_all([first, second])

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_source_ticker_from_different_sources_remains_distinct(db_session):
    dataroma_security = SourceSecurity(
        source="dataroma",
        source_key="BRK-B",
        ticker_raw="BRK.B",
        company_name_raw="Berkshire Hathaway Inc.",
    )
    hedgefollow_security = SourceSecurity(
        source="hedgefollow",
        source_key="BRK-B",
        ticker_raw="BRK-B",
        company_name_raw="Berkshire Hathaway Inc.",
    )
    db_session.add_all([dataroma_security, hedgefollow_security])
    db_session.commit()

    assert dataroma_security.id != hedgefollow_security.id
    assert {dataroma_security.source, hedgefollow_security.source} == {
        "dataroma",
        "hedgefollow",
    }
