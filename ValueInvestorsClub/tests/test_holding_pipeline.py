from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base, Company, Holding, Investor
from ValueInvestorsClub.ValueInvestorsClub.holding_items import HoldingItem
from ValueInvestorsClub.ValueInvestorsClub.holding_pipeline import HoldingPipeline
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import (
    IngestionRun,
    StagingHoldingSnapshot,
)
from ValueInvestorsClub.ValueInvestorsClub.models.source import SourceHoldingSnapshot


def test_process_item_stages_source_snapshot_and_deduplicates():
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

    pipeline.process_item(item)
    pipeline.process_item(item)  # re-processing the same quarter must not duplicate

    with Session(engine) as session:
        assert session.query(IngestionRun).count() == 2
        assert session.query(SourceHoldingSnapshot).count() == 1
        assert session.query(StagingHoldingSnapshot).count() == 1
        assert session.query(Investor).count() == 0
        assert session.query(Company).count() == 0
        assert session.query(Holding).count() == 0


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
