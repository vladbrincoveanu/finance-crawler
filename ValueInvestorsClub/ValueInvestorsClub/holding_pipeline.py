import hashlib
import json
import os
from datetime import datetime, timezone

from scrapy import signals
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

try:
    from ValueInvestorsClub.ingestion import IngestionService, SourcePage
    from ValueInvestorsClub.models import Company, Holding, Investor
    from ValueInvestorsClub.pipeline_support import scrapy_close_reason
except ModuleNotFoundError:
    from ValueInvestorsClub.ValueInvestorsClub.ingestion import IngestionService, SourcePage
    from ValueInvestorsClub.ValueInvestorsClub.models import Company, Holding, Investor
    from ValueInvestorsClub.ValueInvestorsClub.pipeline_support import scrapy_close_reason


class HoldingPipeline:
    """Stage source holdings; legacy writes require an explicit approved bridge."""

    def __init__(self):
        self.engine = create_engine(
            os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/ideas")
        )
        self.parser_version = os.getenv("PARSER_VERSION", "holding-pipeline-1")
        self._run_id = None
        self._closed_run_id = None
        self._crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline._crawler = crawler
        crawler.signals.connect(pipeline._on_spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(pipeline._on_response_received, signal=signals.response_received)
        return pipeline

    def _resolve_spider(self, spider=None):
        return spider or getattr(getattr(self, "_crawler", None), "spider", None)

    def open_spider(self, spider=None):
        spider = self._resolve_spider(spider)
        source = getattr(spider, "source", None)
        if not source:
            source = {
                "DataromaSpider": "dataroma",
                "HedgeFollowSpider": "hedgefollow",
            }.get(getattr(spider, "name", None), "unknown")
        parser_version = getattr(spider, "parser_version", None) or getattr(
            self, "parser_version", os.getenv("PARSER_VERSION", "holding-pipeline-1")
        )
        with Session(self.engine) as session:
            run = IngestionService(session).start_run(
                source=source,
                target="holdings",
                parser_version=parser_version,
            )
            self._run_id = run.id

    def process_item(self, item, spider=None):
        spider = self._resolve_spider(spider)
        if getattr(self, "_run_id", None) is None:
            self.open_spider(spider)
        payload = self._observation_payload(item)
        with Session(self.engine) as session:
            service = IngestionService(session)
            service.stage_raw(self._run_id, payload)
        return item

    def close_spider(self, spider=None, reason=None):
        spider = self._resolve_spider(spider)
        run_id = getattr(self, "_run_id", None)
        if run_id is None:
            return
        close_error = scrapy_close_reason(spider, reason)
        with Session(self.engine) as session:
            IngestionService(session).finish_run(run_id, error_message=close_error)
        self._closed_run_id = run_id
        self._run_id = None

    def _on_spider_closed(self, spider=None, reason=None):
        run_id = getattr(self, "_closed_run_id", None)
        close_error = scrapy_close_reason(spider, reason)
        if run_id is not None and close_error:
            with Session(self.engine) as session:
                IngestionService(session).finish_run(run_id, error_message=close_error)
        self._closed_run_id = None

    def _on_response_received(self, response, request=None, spider=None):
        run_id = getattr(self, "_run_id", None)
        source = getattr(spider, "source", None)
        if run_id is None or source not in {"dataroma", "hedgefollow"}:
            return
        raw_content_type = response.headers.get(b"Content-Type", b"application/octet-stream")
        if isinstance(raw_content_type, list):
            raw_content_type = raw_content_type[0] if raw_content_type else b"application/octet-stream"
        content_type = raw_content_type.decode("latin-1", errors="replace")
        page = SourcePage(
            source=source,
            url=response.url,
            status_code=response.status,
            content_type=content_type,
            body=response.body,
            fetched_at=datetime.now(timezone.utc),
            parser_version=getattr(spider, "parser_version", "holding-pipeline-1"),
        )
        with Session(self.engine) as session:
            IngestionService(session).record_document(run_id, page)

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
        source_url = item.get("source_url") or item.get("investor_profile_url")
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
