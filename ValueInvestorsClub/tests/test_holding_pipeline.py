from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base, Investor, Holding, Company
from ValueInvestorsClub.ValueInvestorsClub.holding_items import HoldingItem
from ValueInvestorsClub.ValueInvestorsClub.holding_pipeline import HoldingPipeline


def test_process_item_upserts_investor_company_and_holding(monkeypatch):
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
        assert session.query(Investor).count() == 1
        assert session.query(Company).count() == 1
        assert session.query(Holding).count() == 1
        holding = session.query(Holding).one()
        assert holding.investor_id == "dataroma:BRK"
        assert holding.shares == 227917808
