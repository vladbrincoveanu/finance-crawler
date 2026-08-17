from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from ..models.curated import CuratedHoldingSnapshot
from ..models.ingestion import StagingHoldingSnapshot
from ..models.source import SourceHoldingSnapshot

from .contracts import ApprovedMapping, PromotionResult


def _completeness(snapshot: SourceHoldingSnapshot) -> str:
    if snapshot.shares is not None and snapshot.value_usd is not None and snapshot.pct_portfolio is not None:
        return "complete"
    return "partial"


def promote_snapshots(
    session: Session,
    run_id: str,
    approved_mappings: Sequence[ApprovedMapping],
) -> PromotionResult:
    mapping_by_source = {
        (mapping.source_investor_id, mapping.source_security_id): mapping
        for mapping in approved_mappings
    }
    accepted = 0
    pending_identity = 0
    rows = (
        session.query(StagingHoldingSnapshot)
        .filter_by(run_id=run_id, validation_status="valid")
        .all()
    )

    for staging in rows:
        snapshot = session.get(SourceHoldingSnapshot, staging.source_snapshot_id)
        mapping = (
            mapping_by_source.get(
                (snapshot.source_investor_id, snapshot.source_security_id)
            )
            if snapshot is not None
            else None
        )
        if mapping is None:
            staging.identity_status = "pending"
            pending_identity += 1
            continue

        existing = session.query(CuratedHoldingSnapshot).filter_by(
            source_snapshot_id=staging.source_snapshot_id
        ).one_or_none()
        if existing is None:
            curated_snapshot = CuratedHoldingSnapshot(
                source_snapshot_id=staging.source_snapshot_id,
                curated_investor_id=mapping.curated_investor_id,
                curated_security_id=mapping.curated_security_id,
                period=snapshot.period,
                shares=snapshot.shares,
                value_usd=snapshot.value_usd,
                pct_portfolio=snapshot.pct_portfolio,
                source_activity=snapshot.source_activity,
                completeness=_completeness(snapshot),
            )
            session.add(curated_snapshot)
        staging.identity_status = "resolved"
        accepted += 1

    session.commit()
    return PromotionResult(accepted=accepted, pending_identity=pending_identity)
