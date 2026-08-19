"""Read-only status evidence for the three source crawlers."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, inspect, literal_column
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import (
    CuratedHoldingSnapshot,
    Idea,
    IngestionRun,
    SourceHoldingSnapshot,
    SourceInvestor,
    SourceSecurity,
    StagingHoldingSnapshot,
)
from api.schemas import (
    CrawlCountsResponse,
    CrawlHoldingSampleResponse,
    CrawlIdeaSampleResponse,
    CrawlRunResponse,
    CrawlSourceStatusResponse,
)

router = APIRouter()

SOURCE_CONFIG = (
    ("dataroma", "Dataroma", "holdings", "/holdings/dataroma"),
    ("hedgefollow", "HedgeFollow", "holdings", "/holdings/hedgefollow"),
    ("valueinvestorsclub", "ValueInvestorsClub.com", "ideas", "/articles"),
)


def _latest_run(db: Session, source: str, target: str) -> IngestionRun | None:
    return (
        db.query(IngestionRun)
        .filter(
            IngestionRun.source == source,
            IngestionRun.target == target,
        )
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .first()
    )


def _run_response(run: IngestionRun | None) -> CrawlRunResponse:
    if run is None:
        return CrawlRunResponse()
    return CrawlRunResponse(
        id=run.id,
        source=run.source,
        target=run.target,
        status=run.status,
        parser_version=run.parser_version,
        started_at=run.started_at,
        finished_at=run.finished_at,
        rows_seen=run.rows_seen,
        rows_accepted=run.rows_accepted,
        rows_rejected=run.rows_rejected,
        rows_duplicate=run.rows_duplicate,
        error_message=run.error_message,
    )


def _source_url(snapshot: SourceHoldingSnapshot) -> str | None:
    if snapshot.fetch is not None and snapshot.fetch.url:
        return snapshot.fetch.url
    if snapshot.source_security.source_url:
        return snapshot.source_security.source_url
    return snapshot.source_investor.profile_url


def _holding_counts_and_sample(
    db: Session, source: str, run: IngestionRun
) -> tuple[CrawlCountsResponse, CrawlHoldingSampleResponse | None]:
    valid_staging = (
        StagingHoldingSnapshot.run_id == run.id,
        StagingHoldingSnapshot.validation_status == "valid",
    )
    staged = (
        db.query(func.count(StagingHoldingSnapshot.id))
        .filter(*valid_staging)
        .scalar()
        or 0
    )
    pending_identity = (
        db.query(func.count(StagingHoldingSnapshot.id))
        .filter(
            *valid_staging,
            StagingHoldingSnapshot.identity_status == "pending",
        )
        .scalar()
        or 0
    )
    curated = (
        db.query(func.count(CuratedHoldingSnapshot.id))
        .join(
            SourceHoldingSnapshot,
            CuratedHoldingSnapshot.source_snapshot_id == SourceHoldingSnapshot.id,
        )
        .filter(SourceHoldingSnapshot.source == source)
        .scalar()
        or 0
    )
    row = (
        db.query(
            StagingHoldingSnapshot,
            SourceHoldingSnapshot,
            SourceInvestor,
            SourceSecurity,
        )
        .join(
            SourceHoldingSnapshot,
            StagingHoldingSnapshot.source_snapshot_id == SourceHoldingSnapshot.id,
        )
        .join(
            SourceInvestor,
            SourceHoldingSnapshot.source_investor_id == SourceInvestor.id,
        )
        .join(
            SourceSecurity,
            SourceHoldingSnapshot.source_security_id == SourceSecurity.id,
        )
        .filter(*valid_staging)
        .order_by(SourceHoldingSnapshot.period.desc(), SourceHoldingSnapshot.id.desc())
        .first()
    )
    sample = None
    if row is not None:
        staging, snapshot, investor, security = row
        sample = CrawlHoldingSampleResponse(
            kind="holding",
            investor_name=investor.name_raw,
            ticker=security.ticker_raw,
            company_name=security.company_name_raw,
            period=snapshot.period,
            shares=staging.shares,
            value_usd=(
                float(staging.value_usd) if staging.value_usd is not None else None
            ),
            pct_portfolio=(
                float(staging.pct_portfolio)
                if staging.pct_portfolio is not None
                else None
            ),
            activity=snapshot.source_activity,
            identity_status=staging.identity_status,
            source_url=_source_url(snapshot),
        )
    return (
        CrawlCountsResponse(
            parser_output=run.rows_seen,
            staged=staged,
            pending_identity=pending_identity,
            curated=curated,
        ),
        sample,
    )


def _idea_run_column(db: Session):
    """Resolve provenance against both mapped and legacy-but-migrated models."""
    columns = {column["name"] for column in inspect(db.get_bind()).get_columns("ideas")}
    if "ingestion_run_id" not in columns:
        return None
    return getattr(Idea, "ingestion_run_id", literal_column("ingestion_run_id"))


def _idea_counts_and_sample(
    db: Session, run: IngestionRun
) -> tuple[CrawlCountsResponse, CrawlIdeaSampleResponse | None]:
    run_column = _idea_run_column(db)
    public = db.query(func.count(Idea.id)).scalar() or 0
    if run_column is None:
        return CrawlCountsResponse(parser_output=run.rows_seen, public=public), None

    idea = (
        db.query(Idea)
        .filter(run_column == run.id)
        .order_by(Idea.date.desc(), Idea.id.desc())
        .first()
    )
    sample = None
    if idea is not None:
        sample = CrawlIdeaSampleResponse(
            kind="idea",
            ticker=idea.company_id,
            company_name=idea.company.company_name if idea.company else None,
            idea_date=idea.date,
            source_url=idea.link,
            link=idea.link,
        )
    return CrawlCountsResponse(parser_output=run.rows_seen, public=public), sample


def _source_status(
    db: Session,
    source: str,
    label: str,
    target: str,
    public_route: str,
) -> CrawlSourceStatusResponse:
    run = _latest_run(db, source, target)
    if run is None:
        counts = CrawlCountsResponse()
        sample = None
    elif target == "holdings":
        counts, sample = _holding_counts_and_sample(db, source, run)
    else:
        counts, sample = _idea_counts_and_sample(db, run)
    return CrawlSourceStatusResponse(
        source=source,
        label=label,
        target=target,
        public_route=public_route,
        latest_run=_run_response(run),
        counts=counts,
        sample=sample,
    )


@router.get("/crawl/status", response_model=List[CrawlSourceStatusResponse])
def get_crawl_status(db: Session = Depends(get_db)):
    return [
        _source_status(db, source, label, target, public_route)
        for source, label, target, public_route in SOURCE_CONFIG
    ]
