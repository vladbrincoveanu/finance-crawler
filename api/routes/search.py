from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import SearchResultResponse
from ValueInvestorsClub.ValueInvestorsClub.retrieval.service import RetrievalService


router = APIRouter()


@router.get("/search", response_model=List[SearchResultResponse])
def search(
    q: str = Query(..., min_length=1),
    company_id: Optional[str] = None,
    security_id: Optional[str] = None,
    investor_id: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    results = RetrievalService(db).search(
        q,
        company_id=company_id,
        security_id=security_id,
        investor_id=investor_id,
        source=source,
        limit=limit,
    )
    return results
