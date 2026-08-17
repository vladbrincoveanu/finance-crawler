"""
Routes for companies in the ValueInvestorsClub API.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.database import get_db
from api.models import (
    Company,
    CuratedCompany,
    CuratedHoldingEvent,
    CuratedHoldingSnapshot,
    CuratedSecurity,
)
from api.routes.holdings import curated_holding_response
from api.schemas import (
    CompanyResponse,
    CuratedCompanyDetailResponse,
    CuratedEventResponse,
    CuratedSecurityResponse,
)

router = APIRouter()


@router.get("/companies/", response_model=List[CompanyResponse])
def get_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get companies with optional name/ticker search
    """
    query = db.query(Company)

    if search:
        search = f"%{search}%"
        query = query.filter(
            (Company.ticker.ilike(search)) | (Company.company_name.ilike(search))
        )

    companies = query.order_by(Company.ticker).offset(skip).limit(limit).all()
    return companies


@router.get(
    "/companies/{curated_company_id}",
    response_model=CuratedCompanyDetailResponse,
)
def get_curated_company(curated_company_id: str, db: Session = Depends(get_db)):
    company = db.get(CuratedCompany, curated_company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="curated company not found")

    securities = (
        db.query(CuratedSecurity)
        .filter(CuratedSecurity.company_id == company.id)
        .order_by(CuratedSecurity.primary_ticker)
        .all()
    )
    holdings = (
        db.query(CuratedHoldingSnapshot)
        .join(
            CuratedSecurity,
            CuratedHoldingSnapshot.curated_security_id == CuratedSecurity.id,
        )
        .filter(CuratedSecurity.company_id == company.id)
        .order_by(CuratedHoldingSnapshot.period.desc())
        .all()
    )
    events = (
        db.query(CuratedHoldingEvent)
        .join(
            CuratedSecurity,
            CuratedHoldingEvent.curated_security_id == CuratedSecurity.id,
        )
        .filter(CuratedSecurity.company_id == company.id)
        .order_by(CuratedHoldingEvent.period.desc())
        .all()
    )
    links = sorted(
        {
            curated_holding_response(holding).source_url
            for holding in holdings
            if curated_holding_response(holding).source_url
        }
    )
    return {
        "id": company.id,
        "display_name": company.display_name,
        "normalized_name": company.normalized_name,
        "securities": [
            CuratedSecurityResponse(
                id=security.id,
                ticker=security.primary_ticker,
                exchange=security.exchange,
                share_class=security.share_class,
            )
            for security in securities
        ],
        "holdings": [curated_holding_response(holding) for holding in holdings],
        "events": [
            CuratedEventResponse(
                period=event.period,
                event_type=event.event_type,
                confidence=float(event.confidence) if event.confidence is not None else None,
                evidence_snapshot_ids=event.evidence_snapshot_ids,
            )
            for event in events
        ],
        "source_links": links,
    }
