import hashlib
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import (
    SourceDocument,
    SourceFetch,
    StagingHoldingSnapshot,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import (
    SourceHoldingSnapshot,
    SourcePortfolioManager,
)
from ValueInvestorsClub.ValueInvestorsClub.ingestion import (
    IngestionService,
    SourceHoldingObservation,
    SourcePage,
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


@pytest.fixture
def run(service):
    return service.start_run(
        source="dataroma", target="holdings", parser_version="test-1"
    )


def valid_observation(key="dataroma:BRK:AAPL:2026-06-30", **overrides):
    values = {
        "source": "dataroma",
        "investor_key": "BRK",
        "investor_name": "Warren Buffett - Berkshire Hathaway",
        "portfolio_manager_name": None,
        "security_key": "AAPL",
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "instrument_type": "common_stock",
        "exchange": "NASDAQ",
        "share_class": None,
        "period": date(2026, 6, 30),
        "shares": 100,
        "value_usd": Decimal("1000.00"),
        "pct_portfolio": Decimal("2.5"),
        "source_activity": "hold",
        "source_url": "https://www.dataroma.com/m/holdings.php?m=BRK",
        "source_observation_key": key,
        "document_hash": "a" * 64,
        "raw_payload": {"source_observation_key": key},
    }
    values.update(overrides)
    return SourceHoldingObservation(**values)


def test_source_observation_rejects_negative_values_and_unknown_fields():
    with pytest.raises(ValidationError):
        valid_observation(shares=-1)

    with pytest.raises(ValidationError):
        valid_observation(unexpected="value")


def test_record_document_deduplicates_content_and_records_each_fetch(
    service, run, db_session
):
    page = SourcePage(
        source="dataroma",
        url="https://example.test/holdings",
        status_code=200,
        content_type="text/html",
        body=b"<html>same response</html>",
        fetched_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
        parser_version="test-1",
    )

    service.record_document(run.id, page)
    service.record_document(
        run.id,
        page.model_copy(update={"url": "https://example.test/holdings?retry=1"}),
    )

    assert db_session.query(SourceDocument).count() == 1
    assert db_session.query(SourceFetch).count() == 2


def test_staging_links_snapshot_to_matching_fetch(service, run, db_session):
    body = b"<html>matching evidence</html>"
    page = SourcePage(
        source="dataroma",
        url="https://example.test/holdings",
        status_code=200,
        content_type="text/html",
        body=body,
        fetched_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
        parser_version="test-1",
    )
    service.record_document(run.id, page)

    service.stage(
        run,
        valid_observation(document_hash=hashlib.sha256(body).hexdigest()),
    )

    snapshot = db_session.query(SourceHoldingSnapshot).one()
    assert snapshot.fetch_id is not None


def test_invalid_numeric_value_goes_to_quarantine(service, run, db_session):
    raw = valid_observation().model_dump(mode="json")
    raw["value_usd"] = "not-money"

    result = service.stage_raw(run, raw)

    assert result.status == "quarantined"
    assert result.reason_code == "invalid_numeric"
    assert db_session.query(SourceHoldingSnapshot).count() == 0
    assert run.rows_rejected == 1


def test_duplicate_source_observation_is_counted_without_second_fact(
    service, run, db_session
):
    observation = valid_observation()

    first = service.stage(run, observation)
    second = service.stage(run, observation)

    assert first.status == "staged"
    assert second.status == "duplicate"
    assert service.count_source_snapshots(run.id) == 1
    assert db_session.query(StagingHoldingSnapshot).count() == 1
    assert run.rows_duplicate == 1


def test_repeated_portfolio_manager_observation_is_not_duplicated(
    service, run, db_session
):
    service.stage(
        run,
        valid_observation(
            key="dataroma:BRK:AAPL:2026-06-30",
            portfolio_manager_name="Todd Combs",
        ),
    )
    service.stage(
        run,
        valid_observation(
            key="dataroma:BRK:MSFT:2026-06-30",
            security_key="MSFT",
            ticker="MSFT",
            portfolio_manager_name=" Todd   Combs ",
        ),
    )

    assert db_session.query(SourcePortfolioManager).count() == 1
