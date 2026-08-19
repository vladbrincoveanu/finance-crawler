# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

# This pipeline will dump the associated data into a postgres sql database.

try:
    from ValueInvestorsClub.ingestion import IngestionService
    from ValueInvestorsClub.models import Idea, Company, Description, User, Catalysts, Comment, Photo
    from ValueInvestorsClub.pipeline_support import scrapy_close_reason
except ImportError:
    # Same dual-context shim as models/*.py: works whether this module is
    # imported as the standalone scrapy project or nested under tests/.
    from ValueInvestorsClub.ValueInvestorsClub.ingestion import IngestionService
    from ValueInvestorsClub.ValueInvestorsClub.models import Idea, Company, Description, User, Catalysts, Comment, Photo
    from ValueInvestorsClub.ValueInvestorsClub.pipeline_support import scrapy_close_reason
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from scrapy import signals
from scrapy.exceptions import DropItem
import uuid
from datetime import datetime
import os
import re
import json
from pathlib import Path


def _safe_segment(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "unknown"
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._-]+", "", s)
    return s or "unknown"


class FileExportPipeline:
    """Best-effort exporter grouped by ticker."""

    def __init__(self):
        self.export_dir = Path(os.getenv("EXPORT_DIR", "out/ideas"))
        self.include_incomplete = os.getenv("EXPORT_INCLUDE_INCOMPLETE", "false").lower() in {"1", "true", "yes"}

    def process_item(self, item, spider=None):
        ticker = (item.get("ticker") or "").strip()
        if not ticker and not self.include_incomplete:
            return item

        date_iso = (item.get("date_iso") or "").strip() or "unknown-date"
        username = (item.get("username") or "").strip() or "unknown-user"
        idea_id = (item.get("idea_id") or "").strip() or "unknown-id"

        ticker_dir = self.export_dir / _safe_segment(ticker or "UNKNOWN")
        ticker_dir.mkdir(parents=True, exist_ok=True)

        out_name = f"{_safe_segment(date_iso)}__{_safe_segment(username)}__{_safe_segment(idea_id)}.json"
        out_path = ticker_dir / out_name

        payload = dict(item)
        payload.setdefault("exported_at_utc", datetime.utcnow().isoformat(timespec="seconds") + "Z")
        out_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
        return item

class SqlPipeline:
    collection_name = 'scrapy_items'

    def __init__(self, ):
        self.engine = create_engine(os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@localhost/ideas'), echo=True)
        self._run_id = None
        self._closed_run_id = None
        self._crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline._crawler = crawler
        crawler.signals.connect(pipeline._on_spider_closed, signal=signals.spider_closed)
        return pipeline

    def _resolve_spider(self, spider=None):
        return spider or getattr(getattr(self, "_crawler", None), "spider", None)

    def open_spider(self, spider=None):
        spider = self._resolve_spider(spider)
        source = getattr(spider, "source", None) or "valueinvestorsclub"
        parser_version = getattr(spider, "parser_version", None) or os.getenv(
            "PARSER_VERSION", "idea-pipeline-v1"
        )
        with Session(self.engine) as session:
            run = IngestionService(session).start_run(
                source=source,
                target="ideas",
                parser_version=parser_version,
            )
            self._run_id = run.id

    def _record_item_result(self, *, accepted: bool, error_message=None):
        with Session(self.engine) as session:
            IngestionService(session).record_item_result(
                self._run_id,
                accepted=accepted,
                error_message=error_message,
            )

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

    def process_item(self, item, spider=None):
        spider = self._resolve_spider(spider)
        if getattr(self, "_run_id", None) is None:
            self.open_spider(spider)

        # Make a idea, catalyst, company, description and user object
        # Then add them to the database
        
        # Critical fields - must have these
        required_fields = ("ticker", "companyName", "date")
        missing = [field for field in required_fields if not item.get(field)]
        if missing:
            error_message = item.get("parse_error") or f"missing {', '.join(missing)}"
            self._record_item_result(
                accepted=False,
                error_message=error_message,
            )
            raise DropItem(error_message)
            
        # Log what we have for debugging
        if spider and hasattr(spider, 'logger'):
            spider.logger.info(f"Processing item: ticker={item.get('ticker')}, "
                             f"company={item.get('companyName')}, "
                             f"username={item.get('username')}, "
                             f"userLink={item.get('userLink')}")
        
        try:
            with Session(self.engine) as session:
                # Handle user - ensure we ALWAYS have a username (not None)
                username = item.get('username') or 'Unknown'  # Never None
                userlink = item.get('userLink') or 'unknown'  # Never None

                # Check if user exists
                # models/__init__.py exports ORM classes, not modules.
                user = session.query(User).filter(User.user_link == userlink).first()
                if user is None:
                    user = User(
                        username=username,
                        user_link=userlink
                    )

                # check if the company exists
                company = session.query(Company).filter(Company.ticker == item['ticker']).first()
                if company is None:
                    company = Company(
                        ticker=item['ticker'],
                        company_name=item['companyName']
                    )
                est_index = item['date'].index('EST')
                date_text = item['date'][:est_index].strip()
                date_text = re.sub(r'(?i)(am|pm)', lambda m: m.group(1).upper(), date_text)
                new_date = datetime.strptime(date_text, "%B %d, %Y - %I:%M%p")

                idea = Idea(
                    id=str(uuid.uuid4()),
                    link=item['link'],
                    company_id=company.ticker,
                    user_id=user.user_link,
                    ingestion_run_id=self._run_id,
                    date=new_date,
                    is_short=bool(item.get('isShort', False)),
                    is_contest_winner=bool(item.get('isContestWinner', False)),
                )

                description = Description(
                    idea_id=idea.id,
                    description=item['description']
                )
                catalysts = Catalysts(
                    idea_id=idea.id,
                    catalysts=item['catalysts']
                )

                comment_rows = [
                    Comment(
                        id=str(uuid.uuid4()),
                        idea_id=idea.id,
                        author=(c.get('author') or '')[:256],
                        posted_at=(c.get('when') or '')[:64],
                        text=(c.get('text') or '')[:32000],
                    )
                    for c in (item.get('comments') or [])
                    if c.get('text')
                ]

                photo_rows = [
                    Photo(id=str(uuid.uuid4()), idea_id=idea.id, url=url[:1024])
                    for url in (item.get('photos') or [])
                ]

                session.add(user)
                session.add(company)
                session.flush()
                session.add(idea)
                session.add(description)
                session.add(catalysts)
                session.add_all(comment_rows)
                session.add_all(photo_rows)
                IngestionService(session).record_item_result(
                    self._run_id,
                    accepted=True,
                    commit=False,
                )
                session.commit()
        except Exception as error:
            self._record_item_result(
                accepted=False,
                error_message=str(error),
            )
            raise


        return item
