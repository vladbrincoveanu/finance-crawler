"""Curated and compatibility holding routes."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import (
    Company,
    CuratedHoldingSnapshot,
    CuratedInvestor,
    CuratedSecurity,
    Holding,
    Investor,
    SourceHoldingSnapshot,
)
from api.schemas import CuratedHoldingResponse, HoldingResponse


router = APIRouter()


def source_url(snapshot: SourceHoldingSnapshot) -> str:
    if snapshot.fetch is not None:
        return snapshot.fetch.url
    if snapshot.source_security.source_url:
        return snapshot.source_security.source_url
    return snapshot.source_investor.profile_url or ""


def curated_holding_response(
    snapshot: CuratedHoldingSnapshot,
) -> CuratedHoldingResponse:
    source_snapshot = snapshot.source_snapshot
    source_investor = source_snapshot.source_investor
    manager = (
        source_investor.portfolio_managers[0].name_raw
        if source_investor.portfolio_managers
        else None
    )
    return CuratedHoldingResponse(
        source=source_snapshot.source,
        investor_id=snapshot.curated_investor_id,
        investor_name=snapshot.curated_investor.display_name,
        portfolio_manager_name=manager,
        company_id=snapshot.curated_security.company_id,
        company_name=snapshot.curated_security.company.display_name,
        security_id=snapshot.curated_security_id,
        ticker=snapshot.curated_security.primary_ticker,
        period=snapshot.period,
        shares=snapshot.shares,
        value_usd=float(snapshot.value_usd) if snapshot.value_usd is not None else None,
        pct_portfolio=(
            float(snapshot.pct_portfolio)
            if snapshot.pct_portfolio is not None
            else None
        ),
        source_activity=snapshot.source_activity,
        completeness=snapshot.completeness,
        source_url=source_url(source_snapshot),
    )


@router.get("/holdings/", response_model=List[CuratedHoldingResponse])
def get_holdings(
    source: Optional[str] = None,
    investor_id: Optional[str] = None,
    company_id: Optional[str] = None,
    security_id: Optional[str] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=0, le=1000),
    db: Session = Depends(get_db),
):
    query = (
        db.query(CuratedHoldingSnapshot)
        .join(
            SourceHoldingSnapshot,
            CuratedHoldingSnapshot.source_snapshot_id == SourceHoldingSnapshot.id,
        )
        .join(
            CuratedInvestor,
            CuratedHoldingSnapshot.curated_investor_id == CuratedInvestor.id,
        )
        .join(
            CuratedSecurity,
            CuratedHoldingSnapshot.curated_security_id == CuratedSecurity.id,
        )
    )
    if source:
        query = query.filter(SourceHoldingSnapshot.source == source)
    if investor_id:
        query = query.filter(CuratedHoldingSnapshot.curated_investor_id == investor_id)
    if company_id:
        query = query.filter(CuratedSecurity.company_id == company_id)
    if security_id:
        query = query.filter(CuratedHoldingSnapshot.curated_security_id == security_id)
    if period_start:
        query = query.filter(CuratedHoldingSnapshot.period >= period_start)
    if period_end:
        query = query.filter(CuratedHoldingSnapshot.period <= period_end)

    rows = (
        query.order_by(CuratedHoldingSnapshot.period.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [curated_holding_response(row) for row in rows]


@router.get("/holdings/legacy/", response_model=List[HoldingResponse])
def get_legacy_holdings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=0, le=1000),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Holding, Investor, Company)
        .join(Investor, Holding.investor_id == Investor.id)
        .join(Company, Holding.company_id == Company.ticker)
        .order_by(Holding.quarter_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        HoldingResponse(
            investor_name=investor.name,
            ticker=company.ticker,
            company_name=company.company_name,
            quarter_date=holding.quarter_date,
            shares=holding.shares,
            value_usd=float(holding.value_usd),
            pct_portfolio=float(holding.pct_portfolio),
            activity=holding.activity,
        )
        for holding, investor, company in rows
    ]
