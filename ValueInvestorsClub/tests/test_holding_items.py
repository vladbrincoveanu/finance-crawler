from ValueInvestorsClub.ValueInvestorsClub.holding_items import HoldingItem


def test_holding_item_has_expected_fields():
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
        source_url="https://www.dataroma.com/m/hist/hist.php?f=BRK&s=AAPL",
        source_observation_key="dataroma:BRK:AAPL:2026-06-30",
        document_hash="a" * 64,
        exchange="NASDAQ",
        share_class="A",
        portfolio_manager_name=None,
        raw_payload={"source": "fixture"},
    )
    assert item["ticker"] == "AAPL"
    assert item["activity"] == "hold"
    assert item["source_observation_key"] == "dataroma:BRK:AAPL:2026-06-30"
