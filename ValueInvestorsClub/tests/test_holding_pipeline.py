import hashlib
from datetime import date
import inspect
from types import SimpleNamespace

from scrapy.http import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base, Company, Holding, Investor
from ValueInvestorsClub.ValueInvestorsClub.holding_items import HoldingItem
from ValueInvestorsClub.ValueInvestorsClub.holding_pipeline import HoldingPipeline
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import (
    IngestionRun,
    QuarantineRecord,
    SourceFetch,
    StagingHoldingSnapshot,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import SourceHoldingSnapshot


def test_process_item_stages_source_snapshot_and_deduplicates():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    spider = SimpleNamespace(source="dataroma", parser_version="dataroma-v1")

    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        investor_profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )

    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.process_item(item, spider)  # re-processing the same quarter must not duplicate
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.source == "dataroma"
        assert run.target == "holdings"
        assert run.parser_version == "dataroma-v1"
        assert run.rows_seen == 2
        assert run.rows_accepted == 1
        assert run.rows_rejected == 0
        assert run.rows_duplicate == 1
        assert run.status == "partial"
        assert session.query(SourceHoldingSnapshot).count() == 1
        assert session.query(StagingHoldingSnapshot).count() == 1
        assert session.query(Investor).count() == 0
        assert session.query(Company).count() == 0
        assert session.query(Holding).count() == 0


def test_holding_pipeline_lifecycle_methods_accept_scrapy_managed_spider_context():
    assert inspect.signature(HoldingPipeline.open_spider).parameters["spider"].default is None
    assert inspect.signature(HoldingPipeline.process_item).parameters["spider"].default is None
    assert inspect.signature(HoldingPipeline.close_spider).parameters["spider"].default is None


def test_holding_pipeline_resolves_spider_from_crawler_when_scrapy_omits_argument():
    spider = SimpleNamespace(source="dataroma")
    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline._crawler = SimpleNamespace(spider=spider)

    assert pipeline._resolve_spider() is spider


def test_empty_holding_crawl_is_failed():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    spider = SimpleNamespace(source="hedgefollow", parser_version="hedgefollow-v1")

    pipeline.open_spider(spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.status == "failed"
        assert run.rows_seen == 0
        assert run.error_message == "no rows seen"


def test_duplicate_only_holding_crawl_is_complete():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    spider = SimpleNamespace(source="dataroma", parser_version="dataroma-v1")
    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        investor_profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )

    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)
    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        runs = session.query(IngestionRun).order_by(IngestionRun.started_at).all()
        assert len(runs) == 2
        assert runs[1].rows_seen == 1
        assert runs[1].rows_accepted == 0
        assert runs[1].rows_duplicate == 1
        assert runs[1].status == "complete"


def test_holding_close_error_is_persisted():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    spider = SimpleNamespace(source="dataroma", parser_version="dataroma-v1")

    pipeline.open_spider(spider)
    pipeline.close_spider(spider, reason="fatal parser error")

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.status == "failed"
        assert run.error_message == "fatal parser error"


def test_holding_close_uses_scrapy_finish_reason_when_reason_is_omitted():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    stats = SimpleNamespace(
        get_value=lambda key: "fatal parser error" if key == "finish_reason" else None
    )
    spider = SimpleNamespace(
        source="dataroma",
        parser_version="dataroma-v1",
        crawler=SimpleNamespace(stats=stats),
    )
    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        investor_profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )

    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.status == "failed"
        assert run.error_message == "fatal parser error"


def test_holding_spider_closed_signal_records_reason_after_pipeline_close():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    spider = SimpleNamespace(source="dataroma", parser_version="dataroma-v1")

    pipeline.open_spider(spider)
    pipeline.close_spider(spider)
    pipeline._on_spider_closed(spider, reason="shutdown")

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.status == "failed"
        assert run.error_message == "shutdown"


def test_holding_response_is_recorded_and_snapshot_links_fetch():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    spider = SimpleNamespace(source="dataroma", parser_version="dataroma-v1")
    body = b"source page body"
    response = Response(
        url="https://www.dataroma.com/m/holdings.php?m=BRK",
        status=200,
        body=body,
        headers={b"Content-Type": [b"text/html; charset=utf-8"]},
    )
    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        investor_profile_url=response.url,
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
        source_url=response.url,
        document_hash=hashlib.sha256(body).hexdigest(),
    )

    pipeline.open_spider(spider)
    pipeline._on_response_received(response, None, spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        fetch = session.query(SourceFetch).one()
        snapshot = session.query(SourceHoldingSnapshot).one()
        staging = session.query(StagingHoldingSnapshot).one()
        assert fetch.url == response.url
        assert snapshot.fetch_id == fetch.id
        assert staging.period == date(2026, 6, 30)


def test_missing_holding_source_url_is_quarantined_without_fake_provenance():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    spider = SimpleNamespace(source="dataroma", parser_version="dataroma-v1")
    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )

    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        quarantine = session.query(QuarantineRecord).one()
        assert run.rows_rejected == 1
        assert run.status == "partial"
        assert session.query(SourceHoldingSnapshot).count() == 0
        assert quarantine.raw_payload["source_url"] is None
        assert "example.invalid" not in str(quarantine.raw_payload)


def test_bridge_approved_item_is_the_explicit_legacy_write_path():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)
    pipeline = HoldingPipeline.__new__(HoldingPipeline)
    pipeline.engine = engine
    item = HoldingItem(
        investor_name="Warren Buffett - Berkshire Hathaway",
        investor_source="dataroma",
        investor_slug="BRK",
        investor_profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
        ticker="AAPL",
        company_name="Apple Inc.",
        quarter_date="2026-06-30",
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )

    pipeline.bridge_approved_item(
        item,
        legacy_investor_id="approved:dataroma:BRK",
        legacy_company_ticker="AAPL",
    )

    with Session(engine) as session:
        assert session.query(Investor).count() == 1
        assert session.query(Company).count() == 1
        assert session.query(Holding).count() == 1
