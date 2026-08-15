from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base, Company, Investor, Holding


def test_holding_links_investor_and_company():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    with Session(engine) as session:
        investor = Investor(id="dataroma:BRK", name="Warren Buffett - Berkshire Hathaway",
                             source="dataroma", source_slug="BRK",
                             profile_url="https://www.dataroma.com/m/holdings.php?m=BRK")
        company = Company(ticker="AAPL", company_name="Apple Inc.")
        holding = Holding(
            investor_id=investor.id,
            company_id=company.ticker,
            quarter_date=date(2026, 6, 30),
            shares=227917808,
            value_usd=65950296000,
            pct_portfolio=22.04,
            activity="hold",
        )
        session.add_all([investor, company, holding])
        session.commit()

        fetched = session.query(Holding).one()
        assert fetched.investor.name == "Warren Buffett - Berkshire Hathaway"
        assert fetched.company.company_name == "Apple Inc."
        assert fetched.quarter_date == date(2026, 6, 30)
