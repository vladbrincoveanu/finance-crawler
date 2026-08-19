"""Contract tests for the read-only three-source crawl status endpoint."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import inspect, text

from api.models import (
    Company,
    CuratedCompany,
    CuratedHoldingSnapshot,
    CuratedInvestor,
    CuratedSecurity,
    Idea,
    IngestionRun,
    SourceHoldingSnapshot,
    SourceInvestor,
    SourceSecurity,
    StagingHoldingSnapshot,
    User,
)
from api.routes.crawl import _source_url

LATEST_RUN_FIELDS = {
    "id",
    "source",
    "target",
    "status",
    "parser_version",
    "started_at",
    "finished_at",
    "rows_seen",
    "rows_accepted",
    "rows_rejected",
    "rows_duplicate",
    "error_message",
}

COUNT_FIELDS = {
    "parser_output",
    "staged",
    "pending_identity",
    "curated",
    "public",
}


def test_holding_sample_prefers_public_provenance_url_over_transport_fetch_url():
    snapshot = SimpleNamespace(
        fetch=SimpleNamespace(url="https://hedgefollow.com/ggg/web_request.php"),
        source_security=SimpleNamespace(
            source_url="https://hedgefollow.com/funds/Baupost+Group+Ma"
        ),
    )

    assert _source_url(snapshot) == "https://hedgefollow.com/funds/Baupost+Group+Ma"


def _run(
    source: str,
    target: str,
    run_id: str,
    started_at: datetime,
    **values,
) -> IngestionRun:
    return IngestionRun(
        id=run_id,
        source=source,
        target=target,
        parser_version=values.pop("parser_version", f"{source}-v1"),
        status=values.pop("status", "complete"),
        started_at=started_at,
        finished_at=values.pop("finished_at", started_at),
        **values,
    )


def _ensure_idea_run_column(db_session) -> None:
    """Keep this API test compatible with pre-provenance legacy test schemas."""
    columns = {
        column["name"]
        for column in inspect(db_session.bind).get_columns("ideas")
    }
    if "ingestion_run_id" not in columns:
        db_session.execute(
            text("ALTER TABLE ideas ADD COLUMN ingestion_run_id VARCHAR(36)")
        )


def _set_idea_run(db_session, idea: Idea, run: IngestionRun) -> None:
    if hasattr(Idea, "ingestion_run_id"):
        idea.ingestion_run_id = run.id
    else:
        db_session.execute(
            text("UPDATE ideas SET ingestion_run_id = :run_id WHERE id = :idea_id"),
            {"run_id": run.id, "idea_id": idea.id},
        )


def _holding_rows(
    run: IngestionRun,
    source: str,
    source_key: str,
    ticker: str,
    company_name: str,
    observation_key: str,
    period: date,
    *,
    validation_status: str = "valid",
    identity_status: str = "resolved",
    source_url: str,
):
    investor = SourceInvestor(
        source=source,
        source_key=f"investor-{source_key}",
        name_raw=f"{company_name} Fund",
        name_normalized=f"{company_name.lower()} fund",
        profile_url=f"https://{source}.test/investors/{source_key}",
    )
    security = SourceSecurity(
        source=source,
        source_key=source_key,
        ticker_raw=ticker,
        company_name_raw=company_name,
        source_url=source_url,
    )
    snapshot = SourceHoldingSnapshot(
        run=run,
        source=source,
        source_investor=investor,
        source_security=security,
        period=period,
        shares=100,
        value_usd=Decimal("1000.00"),
        pct_portfolio=Decimal("2.50"),
        source_activity="hold",
        source_observation_key=observation_key,
    )
    staging = StagingHoldingSnapshot(
        run=run,
        source_snapshot=snapshot,
        period=period,
        shares=100,
        value_usd=Decimal("1000.00"),
        pct_portfolio=Decimal("2.50"),
        validation_status=validation_status,
        identity_status=identity_status,
    )
    return investor, security, snapshot, staging


def seed_source_status_rows(db_session) -> None:
    _ensure_idea_run_column(db_session)
    first_time = datetime(2026, 8, 1, tzinfo=timezone.utc)
    dataroma_old_run = _run(
        "dataroma", "holdings", "dataroma-old", first_time, rows_seen=9
    )
    dataroma_run = _run(
        "dataroma",
        "holdings",
        "dataroma-current",
        datetime(2026, 8, 3, tzinfo=timezone.utc),
        rows_seen=3,
        rows_accepted=2,
    )
    dataroma_other_target = _run(
        "dataroma",
        "other",
        "dataroma-other-target",
        datetime(2026, 8, 4, tzinfo=timezone.utc),
        rows_seen=99,
    )
    hedgefollow_run = _run(
        "hedgefollow",
        "holdings",
        "hedgefollow-current",
        datetime(2026, 8, 4, tzinfo=timezone.utc),
        status="partial",
        rows_seen=2,
        rows_accepted=1,
        error_message="one holding needs identity review",
    )
    idea_run = _run(
        "valueinvestorsclub",
        "ideas",
        "vic-current",
        datetime(2026, 8, 5, tzinfo=timezone.utc),
        rows_seen=2,
        rows_accepted=1,
        rows_rejected=1,
    )

    old_dataroma_rows = _holding_rows(
        dataroma_old_run,
        "dataroma",
        "OLD",
        "OLD",
        "Old Company",
        "dataroma:old",
        date(2026, 3, 31),
        source_url="https://dataroma.test/old",
    )
    dataroma_rows = _holding_rows(
        dataroma_run,
        "dataroma",
        "AAPL",
        "AAPL",
        "Apple Inc.",
        "dataroma:current",
        date(2026, 6, 30),
        source_url="https://dataroma.test/current/aapl",
    )
    dataroma_invalid_rows = _holding_rows(
        dataroma_run,
        "dataroma",
        "INVALID",
        "INVALID",
        "Invalid Company",
        "dataroma:invalid",
        date(2026, 6, 29),
        validation_status="invalid",
        source_url="https://dataroma.test/current/invalid",
    )
    hedgefollow_rows = _holding_rows(
        hedgefollow_run,
        "hedgefollow",
        "BRK-B",
        "BRK-B",
        "Berkshire Hathaway",
        "hedgefollow:current",
        date(2026, 6, 30),
        identity_status="pending",
        source_url="https://hedgefollow.test/current/brk-b",
    )

    old_curated_company = CuratedCompany(
        display_name="Old Company", normalized_name="old company"
    )
    old_curated_security = CuratedSecurity(
        primary_ticker="OLD", company=old_curated_company
    )
    old_curated_investor = CuratedInvestor(
        display_name="Old Company Fund", normalized_name="old company fund"
    )
    current_curated_company = CuratedCompany(
        display_name="Apple Inc.", normalized_name="apple inc"
    )
    current_curated_security = CuratedSecurity(
        primary_ticker="AAPL", company=current_curated_company
    )
    current_curated_investor = CuratedInvestor(
        display_name="Apple Inc. Fund", normalized_name="apple inc fund"
    )
    old_curated = CuratedHoldingSnapshot(
        source_snapshot=old_dataroma_rows[2],
        curated_investor=old_curated_investor,
        curated_security=old_curated_security,
        period=old_dataroma_rows[2].period,
        shares=100,
        value_usd=Decimal("1000.00"),
        pct_portfolio=Decimal("2.50"),
        completeness="complete",
    )
    current_curated = CuratedHoldingSnapshot(
        source_snapshot=dataroma_rows[2],
        curated_investor=current_curated_investor,
        curated_security=current_curated_security,
        period=dataroma_rows[2].period,
        shares=100,
        value_usd=Decimal("1000.00"),
        pct_portfolio=Decimal("2.50"),
        completeness="complete",
    )

    company = Company(ticker="ACME", company_name="Acme Corp")
    user = User(username="investor", user_link="/member/investor")
    current_idea = Idea(
        id="idea-current",
        link="https://valueinvestorsclub.test/idea/Acme/1",
        company_id=company.ticker,
        user_id=user.user_link,
        date=datetime(2026, 8, 5, 12, 0),
        is_short=False,
        is_contest_winner=False,
    )
    old_idea = Idea(
        id="idea-old",
        link="https://valueinvestorsclub.test/idea/Old/2",
        company_id=company.ticker,
        user_id=user.user_link,
        date=datetime(2025, 8, 5, 12, 0),
        is_short=True,
        is_contest_winner=False,
    )

    db_session.add_all(
        [
            dataroma_old_run,
            dataroma_run,
            dataroma_other_target,
            hedgefollow_run,
            idea_run,
            *old_dataroma_rows,
            *dataroma_rows,
            *dataroma_invalid_rows,
            *hedgefollow_rows,
            old_curated_company,
            old_curated_security,
            old_curated_investor,
            current_curated_company,
            current_curated_security,
            current_curated_investor,
            old_curated,
            current_curated,
            company,
            user,
            current_idea,
            old_idea,
        ]
    )
    db_session.flush()
    _set_idea_run(db_session, current_idea, idea_run)
    db_session.commit()


def test_crawl_status_returns_exact_three_source_contract(client, db_session):
    seed_source_status_rows(db_session)

    response = client.get("/crawl/status")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert [row["source"] for row in data] == [
        "dataroma",
        "hedgefollow",
        "valueinvestorsclub",
    ]
    assert all(
        set(row) == {
            "source",
            "label",
            "target",
            "public_route",
            "latest_run",
            "counts",
            "sample",
        }
        for row in data
    )
    assert set(data[0]["latest_run"]) == LATEST_RUN_FIELDS
    assert set(data[0]["counts"]) == COUNT_FIELDS

    dataroma = data[0]
    assert dataroma["target"] == "holdings"
    assert dataroma["public_route"] == "/holdings/dataroma"
    assert dataroma["latest_run"]["id"] == "dataroma-current"
    assert dataroma["counts"] == {
        "parser_output": 3,
        "staged": 1,
        "pending_identity": 0,
        "curated": 2,
        "public": 0,
    }
    assert dataroma["sample"] == {
        "kind": "holding",
        "investor_name": "Apple Inc. Fund",
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "period": "2026-06-30",
        "shares": 100,
        "value_usd": 1000.0,
        "pct_portfolio": 2.5,
        "activity": "hold",
        "identity_status": "resolved",
        "source_url": "https://dataroma.test/current/aapl",
    }

    hedgefollow = data[1]
    assert hedgefollow["latest_run"]["status"] == "partial"
    assert hedgefollow["latest_run"]["error_message"] == (
        "one holding needs identity review"
    )
    assert hedgefollow["counts"] == {
        "parser_output": 2,
        "staged": 1,
        "pending_identity": 1,
        "curated": 0,
        "public": 0,
    }
    assert hedgefollow["sample"]["kind"] == "holding"
    assert hedgefollow["sample"]["ticker"] == "BRK-B"

    vic = data[2]
    assert vic["target"] == "ideas"
    assert vic["public_route"] == "/articles"
    assert vic["counts"] == {
        "parser_output": 2,
        "staged": 0,
        "pending_identity": 0,
        "curated": 0,
        "public": 2,
    }
    assert vic["sample"]["kind"] == "idea"
    assert vic["sample"]["link"].endswith("/Acme/1")
    assert vic["sample"]["source_url"].endswith("/Acme/1")


def test_crawl_status_uses_id_tiebreaker_and_includes_running_failed_runs(
    client, db_session
):
    started_at = datetime(2026, 8, 7, tzinfo=timezone.utc)
    db_session.add_all(
        [
            _run(
                "dataroma",
                "holdings",
                "dataroma-tie-a",
                started_at,
                status="complete",
                rows_seen=1,
            ),
            _run(
                "dataroma",
                "holdings",
                "dataroma-tie-z",
                started_at,
                status="running",
                finished_at=None,
                rows_seen=0,
            ),
            _run(
                "hedgefollow",
                "holdings",
                "hedgefollow-failed",
                started_at,
                status="failed",
                finished_at=None,
                error_message="HTTP 403",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/crawl/status")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["latest_run"]["id"] == "dataroma-tie-z"
    assert data[0]["latest_run"]["status"] == "running"
    assert data[1]["latest_run"]["status"] == "failed"
    assert data[1]["latest_run"]["error_message"] == "HTTP 403"
    assert data[0]["counts"] == {
        "parser_output": 0,
        "staged": 0,
        "pending_identity": 0,
        "curated": 0,
        "public": 0,
    }
    assert data[0]["sample"] is None


def test_crawl_status_returns_fixed_empty_records_without_runs(client):
    response = client.get("/crawl/status")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    for row in data:
        assert row["latest_run"] == {
            "id": None,
            "source": None,
            "target": None,
            "status": None,
            "parser_version": None,
            "started_at": None,
            "finished_at": None,
            "rows_seen": 0,
            "rows_accepted": 0,
            "rows_rejected": 0,
            "rows_duplicate": 0,
            "error_message": None,
        }
        assert row["counts"] == {
            "parser_output": 0,
            "staged": 0,
            "pending_identity": 0,
            "curated": 0,
            "public": 0,
        }
        assert row["sample"] is None
