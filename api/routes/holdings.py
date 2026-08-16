"""
Routes for holdings in the ValueInvestorsClub API.
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import List

from api.database import get_db
from api.models import Holding, Investor, Company
from api.schemas import HoldingResponse

router = APIRouter()


@router.get("/holdings/", response_model=List[HoldingResponse])
def get_holdings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get holdings, joined with investor and company info.
    """
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
