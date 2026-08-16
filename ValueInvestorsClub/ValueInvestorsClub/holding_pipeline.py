import os
from datetime import date as date_cls

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

try:
    # scrapy CLI runtime: PYTHONPATH puts the inner ValueInvestorsClub/ dir first
    from ValueInvestorsClub.models import Base, Investor, Company, Holding
except ModuleNotFoundError:
    # pytest runtime: pythonpath is the repo root only, so the package is nested
    from ValueInvestorsClub.ValueInvestorsClub.models import Base, Investor, Company, Holding


class HoldingPipeline:
    """Upserts HoldingItems (Dataroma, HedgeFollow, ...) into Investor/Company/Holding tables."""

    def __init__(self):
        self.engine = create_engine(
            os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/ideas")
        )
        Base.Base.metadata.create_all(self.engine)

    def process_item(self, item, spider=None):
        investor_id = f"{item['investor_source']}:{item['investor_slug']}"
        quarter_date = date_cls.fromisoformat(item["quarter_date"])

        with Session(self.engine) as session:
            investor = session.get(Investor, investor_id)
            if investor is None:
                investor = Investor(
                    id=investor_id,
                    name=item["investor_name"],
                    source=item["investor_source"],
                    source_slug=item["investor_slug"],
                    profile_url=item["investor_profile_url"],
                )
                session.add(investor)

            company = session.get(Company, item["ticker"])
            if company is None:
                company = Company(ticker=item["ticker"], company_name=item["company_name"])
                session.add(company)
            session.commit()

            holding = (
                session.query(Holding)
                .filter_by(investor_id=investor_id, company_id=item["ticker"], quarter_date=quarter_date)
                .first()
            )
            if holding is None:
                holding = Holding(
                    investor_id=investor_id,
                    company_id=item["ticker"],
                    quarter_date=quarter_date,
                )
                session.add(holding)

            holding.shares = item["shares"]
            holding.value_usd = item["value_usd"]
            holding.pct_portfolio = item["pct_portfolio"]
            holding.activity = item["activity"]
            session.commit()

        return item
