import os
from datetime import datetime, timezone
from hmac import compare_digest
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import (
    IdentityCandidateResponse,
    IdentityDecisionRequest,
    IdentityDecisionResponse,
    QuarantineResponse,
)
from ValueInvestorsClub.ValueInvestorsClub.identity.decisions import DecisionService
from ValueInvestorsClub.ValueInvestorsClub.models.identity import IdentityCandidate
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import QuarantineRecord


router = APIRouter()


def require_review_admin(
    authorization: Optional[str] = Header(default=None),
    review_admin_token: Optional[str] = Header(
        default=None, alias="X-Review-Admin-Token"
    ),
) -> None:
    expected = os.getenv("REVIEW_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="review administration is not configured",
        )
    bind_host = os.getenv("REVIEW_BIND_HOST", "0.0.0.0").lower()
    if bind_host not in {"127.0.0.1", "localhost", "::1"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="review administration must be bound to localhost",
        )

    token = review_admin_token
    if token is None and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token is None or not compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid review administration token",
        )


@router.get(
    "/review/identity",
    response_model=List[IdentityCandidateResponse],
    dependencies=[Depends(require_review_admin)],
)
def get_identity_review_queue(
    db: Session = Depends(get_db),
):
    return (
        db.query(IdentityCandidate)
        .filter(IdentityCandidate.status == "pending")
        .order_by(IdentityCandidate.id)
        .limit(100)
        .all()
    )


@router.post(
    "/review/identity/{candidate_id}/decision",
    response_model=IdentityDecisionResponse,
    dependencies=[Depends(require_review_admin)],
)
def decide_identity(
    candidate_id: str,
    request: IdentityDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        decision = DecisionService(db).record_human_decision(
            candidate_id,
            request.decision,
            curated_entity_id=request.curated_entity_id,
            reviewer_id=request.reviewer_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return decision


@router.get(
    "/review/quarantine",
    response_model=List[QuarantineResponse],
    dependencies=[Depends(require_review_admin)],
)
def get_quarantine_queue(db: Session = Depends(get_db)):
    return (
        db.query(QuarantineRecord)
        .filter(QuarantineRecord.review_status == "open")
        .order_by(QuarantineRecord.created_at)
        .limit(100)
        .all()
    )


@router.post(
    "/review/quarantine/{record_id}/reprocess",
    response_model=QuarantineResponse,
    dependencies=[Depends(require_review_admin)],
)
def reprocess_quarantine(record_id: str, db: Session = Depends(get_db)):
    record = db.get(QuarantineRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="quarantine record not found")
    record.review_status = "reprocessed"
    record.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record
