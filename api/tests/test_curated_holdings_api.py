from datetime import date, datetime, timezone
from decimal import Decimal

from ValueInvestorsClub.ValueInvestorsClub.models.curated import (
    CuratedHoldingEvent,
    CuratedHoldingSnapshot,
)
from ValueInvestorsClub.ValueInvestorsClub.models.identity import (
    CuratedCompany,
    CuratedInvestor,
    CuratedInvestorManager,
    CuratedSecurity,
    PortfolioManager,
)
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import (
    IngestionRun,
    SourceDocument,
    SourceFetch,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import (
    SourceHoldingSnapshot,
    SourceInvestor,
    SourcePortfolioManager,
    SourceSecurity,
)


def seed_curated_rows(db_session):
    run = IngestionRun(
        source="mixed",
        target="holdings",
        parser_version="test-1",
    )
    dataroma_document = SourceDocument(
        source="dataroma",
        content_hash="d" * 64,
        canonical_url="https://dataroma.test/brk",
        content_type="text/html",
        status_code=200,
        body="dataroma source",
        fetched_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    hedgefollow_document = SourceDocument(
        source="hedgefollow",
        content_hash="h" * 64,
        canonical_url="https://hedgefollow.test/brk",
        content_type="application/json",
        status_code=200,
        body="hedgefollow source",
        fetched_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )
    dataroma_fetch = SourceFetch(
        run=run,
        document=dataroma_document,
        url=dataroma_document.canonical_url,
        status_code=200,
        fetched_at=dataroma_document.fetched_at,
        parser_version="test-1",
    )
    hedgefollow_fetch = SourceFetch(
        run=run,
        document=hedgefollow_document,
        url=hedgefollow_document.canonical_url,
        status_code=200,
        fetched_at=hedgefollow_document.fetched_at,
        parser_version="test-1",
    )
    source_investor_dataroma = SourceInvestor(
        source="dataroma",
        source_key="BRK",
        name_raw="Warren Buffett - Berkshire Hathaway",
        name_normalized="warren buffett berkshire hathaway",
    )
    source_investor_hedgefollow = SourceInvestor(
        source="hedgefollow",
        source_key="Berkshire Hathaway",
        name_raw="Berkshire Hathaway",
        name_normalized="berkshire hathaway",
    )
    source_manager = SourcePortfolioManager(
        source_investor=source_investor_dataroma,
        name_raw="Warren Buffett",
        name_normalized="warren buffett",
    )
    source_security_dataroma = SourceSecurity(
        source="dataroma",
        source_key="BRK.B",
        ticker_raw="BRK.B",
        company_name_raw="Berkshire Hathaway CL B",
    )
    source_security_hedgefollow = SourceSecurity(
        source="hedgefollow",
        source_key="BRK-B",
        ticker_raw="BRK-B",
        company_name_raw="Berkshire Hathaway CL B",
    )
    unresolved_source_investor = SourceInvestor(
        source="dataroma",
        source_key="UNKNOWN",
        name_raw="Unresolved Fund",
        name_normalized="unresolved fund",
    )
    unresolved_source_security = SourceSecurity(
        source="dataroma",
        source_key="UNKNOWN",
        ticker_raw="UNKNOWN",
        company_name_raw="Unknown Company",
    )
    company = CuratedCompany(
        display_name="Berkshire Hathaway",
        normalized_name="berkshire hathaway",
    )
    security = CuratedSecurity(
        primary_ticker="BRK.B",
        company=company,
        exchange="NYSE",
        share_class="B",
    )
    investor = CuratedInvestor(
        display_name="Berkshire Hathaway",
        normalized_name="berkshire hathaway",
    )
    manager = PortfolioManager(
        display_name="Warren Buffett",
        normalized_name="warren buffett",
    )
    manager_link = CuratedInvestorManager(
        investor=investor,
        manager=manager,
        source="dataroma",
        evidence_id=dataroma_document.id,
    )
    dataroma_source_snapshot = SourceHoldingSnapshot(
        run=run,
        source="dataroma",
        source_investor=source_investor_dataroma,
        source_security=source_security_dataroma,
        period=date(2026, 6, 30),
        shares=120,
        value_usd=Decimal("1000.00"),
        pct_portfolio=Decimal("2.50"),
        source_activity="hold",
        source_observation_key="dataroma:BRK:BRK.B:2026-06-30",
        fetch=dataroma_fetch,
    )
    hedgefollow_source_snapshot = SourceHoldingSnapshot(
        run=run,
        source="hedgefollow",
        source_investor=source_investor_hedgefollow,
        source_security=source_security_hedgefollow,
        period=date(2026, 3, 31),
        shares=118,
        value_usd=Decimal("980.00"),
        pct_portfolio=Decimal("2.40"),
        source_activity="Buy",
        source_observation_key="hedgefollow:Berkshire Hathaway:BRK-B:2026-03-31",
        fetch=hedgefollow_fetch,
    )
    dataroma_curated_snapshot = CuratedHoldingSnapshot(
        source_snapshot=dataroma_source_snapshot,
        curated_investor=investor,
        curated_security=security,
        period=dataroma_source_snapshot.period,
        shares=120,
        value_usd=Decimal("1000.00"),
        pct_portfolio=Decimal("2.50"),
        source_activity="hold",
        completeness="complete",
    )
    hedgefollow_curated_snapshot = CuratedHoldingSnapshot(
        source_snapshot=hedgefollow_source_snapshot,
        curated_investor=investor,
        curated_security=security,
        period=hedgefollow_source_snapshot.period,
        shares=118,
        value_usd=Decimal("980.00"),
        pct_portfolio=Decimal("2.40"),
        source_activity="Buy",
        completeness="partial",
    )
    unresolved_source_snapshot = SourceHoldingSnapshot(
        run=run,
        source="dataroma",
        source_investor=unresolved_source_investor,
        source_security=unresolved_source_security,
        period=date(2026, 6, 30),
        shares=1,
        source_observation_key="dataroma:UNKNOWN:UNKNOWN:2026-06-30",
    )
    event = CuratedHoldingEvent(
        curated_investor=investor,
        curated_security=security,
        period=date(2026, 6, 30),
        event_type="add",
        evidence_snapshot_ids=[dataroma_curated_snapshot.id or "pending"],
        confidence=Decimal("1.0000"),
    )
    db_session.add_all(
        [
            run,
            dataroma_document,
            hedgefollow_document,
            dataroma_fetch,
            hedgefollow_fetch,
            source_investor_dataroma,
            source_investor_hedgefollow,
            unresolved_source_investor,
            source_manager,
            source_security_dataroma,
            source_security_hedgefollow,
            unresolved_source_security,
            company,
            security,
            investor,
            manager,
            manager_link,
            dataroma_source_snapshot,
            hedgefollow_source_snapshot,
            dataroma_curated_snapshot,
            hedgefollow_curated_snapshot,
            unresolved_source_snapshot,
            event,
        ]
    )
    db_session.commit()
    return company, investor


RESPONSE_FIELDS = {
    "source",
    "investor_id",
    "investor_name",
    "portfolio_manager_name",
    "company_id",
    "company_name",
    "security_id",
    "ticker",
    "period",
    "shares",
    "value_usd",
    "pct_portfolio",
    "source_activity",
    "completeness",
    "source_url",
}


def test_curated_holdings_returns_exact_provenance_contract(client, db_session):
    company, _ = seed_curated_rows(db_session)

    response = client.get("/holdings/?source=dataroma&limit=1")

    assert response.status_code == 200
    row = response.json()[0]
    assert set(row) == RESPONSE_FIELDS
    assert row["source"] == "dataroma"
    assert row["ticker"] == "BRK.B"
    assert row["portfolio_manager_name"] == "Warren Buffett"
    assert row["source_url"] == "https://dataroma.test/brk"
    assert row["completeness"] == "complete"
    assert len(client.get("/holdings/?limit=100").json()) == 2

    detail = client.get(f"/companies/{company.id}")
    assert detail.status_code == 200
    assert detail.json()["display_name"] == "Berkshire Hathaway"
    assert detail.json()["holdings"]


def test_curated_holdings_support_pagination_and_partial_coverage(client, db_session):
    seed_curated_rows(db_session)

    first = client.get("/holdings/?skip=0&limit=1")
    second = client.get("/holdings/?skip=1&limit=1")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()[0]["source"] != second.json()[0]["source"]
    assert second.json()[0]["completeness"] == "partial"
    assert second.json()[0]["shares"] == 118
