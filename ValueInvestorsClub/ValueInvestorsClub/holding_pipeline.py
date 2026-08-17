import hashlib
import json
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

try:
    from ValueInvestorsClub.ingestion import IngestionService
    from ValueInvestorsClub.models import Company, Holding, Investor
except ModuleNotFoundError:
    from ValueInvestorsClub.ValueInvestorsClub.ingestion import IngestionService
    from ValueInvestorsClub.ValueInvestorsClub.models import Company, Holding, Investor


class HoldingPipeline:
    """Stage source holdings; legacy writes require an explicit approved bridge."""

    def __init__(self):
        self.engine = create_engine(
            os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/ideas")
        )
        self.parser_version = os.getenv("PARSER_VERSION", "holding-pipeline-1")

    def process_item(self, item, spider=None):
        payload = self._observation_payload(item)
        with Session(self.engine) as session:
            service = IngestionService(session)
            run = service.start_run(
                source=payload["source"],
                target="holdings",
                parser_version=getattr(
                    self,
                    "parser_version",
                    os.getenv("PARSER_VERSION", "holding-pipeline-1"),
                ),
            )
            service.stage_raw(run, payload)
            service.finish_run(run.id)
        return item

    def bridge_approved_item(
        self,
        item,
        *,
        legacy_investor_id: str,
        legacy_company_ticker: str,
    ):
        """Populate legacy holdings only after an external approval decision."""
        if not legacy_investor_id or not legacy_company_ticker:
            raise ValueError("legacy bridge requires approved investor and company IDs")

        from datetime import date as date_cls

        quarter_date = date_cls.fromisoformat(item["quarter_date"])
        with Session(self.engine) as session:
            investor = session.get(Investor, legacy_investor_id)
            if investor is None:
                investor = Investor(
                    id=legacy_investor_id,
                    name=item["investor_name"],
                    source=item["investor_source"],
                    source_slug=item["investor_slug"],
                    profile_url=item["investor_profile_url"],
                )
                session.add(investor)

            company = session.get(Company, legacy_company_ticker)
            if company is None:
                company = Company(
                    ticker=legacy_company_ticker,
                    company_name=item["company_name"],
                )
                session.add(company)
            session.flush()

            holding = session.query(Holding).filter_by(
                investor_id=legacy_investor_id,
                company_id=legacy_company_ticker,
                quarter_date=quarter_date,
            ).one_or_none()
            if holding is None:
                holding = Holding(
                    investor_id=legacy_investor_id,
                    company_id=legacy_company_ticker,
                    quarter_date=quarter_date,
                )
                session.add(holding)
            holding.shares = item["shares"]
            holding.value_usd = item["value_usd"]
            holding.pct_portfolio = item["pct_portfolio"]
            holding.activity = item["activity"]
            session.commit()
        return item

    def _observation_payload(self, item) -> dict:
        payload = dict(item)
        source = item.get("investor_source") or "unknown"
        slug = item.get("investor_slug")
        ticker = item.get("ticker")
        quarter_date = item.get("quarter_date")
        source_url = item.get("source_url") or item.get("investor_profile_url") or "https://example.invalid/source"
        serialized = json.dumps(payload, default=str, sort_keys=True).encode("utf-8")
        return {
            "source": source,
            "investor_key": slug,
            "investor_name": item.get("investor_name"),
            "security_key": ticker,
            "ticker": ticker,
            "company_name": item.get("company_name"),
            "period": quarter_date,
            "shares": item.get("shares"),
            "value_usd": item.get("value_usd"),
            "pct_portfolio": item.get("pct_portfolio"),
            "source_activity": item.get("activity"),
            "source_url": source_url,
            "source_observation_key": item.get("source_observation_key") or f"{source}:{slug}:{ticker}:{quarter_date}",
            "document_hash": item.get("document_hash") or hashlib.sha256(serialized).hexdigest(),
            "raw_payload": item.get("raw_payload") or payload,
        }
