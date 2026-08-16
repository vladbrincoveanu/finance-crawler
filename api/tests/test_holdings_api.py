"""
Integration tests for the holdings API endpoint.
"""
from datetime import date

from ValueInvestorsClub.ValueInvestorsClub.models.Company import Company
from ValueInvestorsClub.ValueInvestorsClub.models.Investor import Investor
from ValueInvestorsClub.ValueInvestorsClub.models.Holding import Holding


def test_get_holdings_returns_joined_rows(client, db_session):
    company = Company(ticker="AAPL", company_name="Apple Inc.")
    investor = Investor(
        id="dataroma:BRK",
        name="Warren Buffett - Berkshire Hathaway",
        source="dataroma",
        source_slug="BRK",
        profile_url="https://www.dataroma.com/m/holdings.php?m=BRK",
    )
    db_session.add_all([company, investor])
    db_session.commit()

    holding = Holding(
        investor_id="dataroma:BRK",
        company_id="AAPL",
        quarter_date=date(2026, 6, 30),
        shares=227917808,
        value_usd=65950296000.0,
        pct_portfolio=22.04,
        activity="hold",
    )
    db_session.add(holding)
    db_session.commit()

    response = client.get("/holdings/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["investor_name"] == "Warren Buffett - Berkshire Hathaway"
    assert data[0]["ticker"] == "AAPL"
    assert data[0]["shares"] == 227917808


def test_get_holdings_empty_list_when_no_data(client, db_session):
    response = client.get("/holdings/")
    assert response.status_code == 200
    assert response.json() == []
