from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import CuratedHoldingSnapshot, CuratedInvestor
from api.routes.holdings import curated_holding_response
from api.schemas import CuratedAliasResponse, CuratedInvestorDetailResponse


router = APIRouter()


@router.get(
    "/investors/{curated_investor_id}",
    response_model=CuratedInvestorDetailResponse,
)
def get_curated_investor(
    curated_investor_id: str,
    db: Session = Depends(get_db),
):
    investor = db.get(CuratedInvestor, curated_investor_id)
    if investor is None:
        raise HTTPException(status_code=404, detail="curated investor not found")

    holdings = (
        db.query(CuratedHoldingSnapshot)
        .filter(CuratedHoldingSnapshot.curated_investor_id == investor.id)
        .order_by(CuratedHoldingSnapshot.period.desc())
        .all()
    )
    periods = [holding.period for holding in holdings]
    sources = sorted({holding.source_snapshot.source for holding in holdings})
    aliases = [
        CuratedAliasResponse(
            source=alias.source_investor.source,
            source_key=alias.source_investor.source_key,
        )
        for alias in investor.aliases
    ]
    return {
        "id": investor.id,
        "display_name": investor.display_name,
        "normalized_name": investor.normalized_name,
        "status": investor.status,
        "portfolio_managers": [
            link.manager.display_name for link in investor.manager_links
        ],
        "aliases": aliases,
        "holdings": [curated_holding_response(holding) for holding in holdings],
        "coverage": {
            "sources": sources,
            "period_start": min(periods) if periods else None,
            "period_end": max(periods) if periods else None,
            "row_count": len(holdings),
        },
    }
