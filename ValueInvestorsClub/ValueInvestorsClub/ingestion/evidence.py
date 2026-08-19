from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.curated import CuratedHoldingEvent, CuratedHoldingSnapshot
from ..models.ingestion import (
    IngestionRun,
    QuarantineRecord,
    SourceDocument,
    SourceFetch,
    StagingHoldingSnapshot,
)
from ..models.source import (
    SourceHoldingSnapshot,
    SourceInvestor,
    SourcePortfolioManager,
    SourceSecurity,
)

from .contracts import (
    ApprovedMapping,
    PromotionResult,
    SourceHoldingObservation,
    SourcePage,
    StageResult,
)
from .events import project_events
from .promotion import promote_snapshots
from .quality import normalize_name, normalize_ticker, source_record_id, validation_reason


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> dict[str, Any] | list[Any] | str | int | float | bool | None:
    return json.loads(json.dumps(value, default=str))


class IngestionService:
    def __init__(self, session: Session):
        self.session = session

    def start_run(self, source: str, target: str, parser_version: str) -> IngestionRun:
        run = IngestionRun(
            source=source,
            target=target,
            parser_version=parser_version,
            status="running",
        )
        self.session.add(run)
        self.session.commit()
        return run

    def record_item_result(
        self,
        run: IngestionRun | str,
        *,
        accepted: bool,
        duplicate: bool = False,
        error_message: str | None = None,
        commit: bool = True,
    ) -> IngestionRun:
        run_record = self._run(run)
        run_record.rows_seen += 1
        if duplicate:
            run_record.rows_duplicate += 1
        elif accepted:
            run_record.rows_accepted += 1
        else:
            run_record.rows_rejected += 1
        if error_message:
            run_record.error_message = error_message
        if commit:
            self.session.commit()
        return run_record

    def record_document(self, run_id: str, page: SourcePage) -> SourceDocument:
        content_hash = hashlib.sha256(page.body).hexdigest()
        document = self.session.query(SourceDocument).filter_by(
            source=page.source, content_hash=content_hash
        ).one_or_none()
        if document is None:
            document = SourceDocument(
                source=page.source,
                content_hash=content_hash,
                canonical_url=str(page.url),
                content_type=page.content_type,
                status_code=page.status_code,
                body=page.body.decode("utf-8", errors="replace"),
                fetched_at=page.fetched_at,
            )
            self.session.add(document)
            self.session.flush()

        fetch = SourceFetch(
            run_id=run_id,
            document_id=document.id,
            url=str(page.url),
            status_code=page.status_code,
            fetched_at=page.fetched_at,
            parser_version=page.parser_version,
        )
        self.session.add(fetch)
        self.session.commit()
        return document

    def stage_raw(
        self, run: IngestionRun | str, raw_observation: Mapping[str, Any]
    ) -> StageResult:
        try:
            observation = SourceHoldingObservation.model_validate(raw_observation)
        except ValidationError as error:
            run_record = self._run(run)
            self.record_item_result(
                run_record,
                accepted=False,
                commit=False,
            )
            quarantine = QuarantineRecord(
                run_id=run_record.id,
                source=str(raw_observation.get("source") or run_record.source),
                record_type="holding_snapshot",
                source_record_id=source_record_id(raw_observation),
                reason_code=validation_reason(error),
                reason_detail=str(error),
                raw_payload=_json_safe(dict(raw_observation)),
                review_status="open",
            )
            self.session.add(quarantine)
            self.session.commit()
            return StageResult(status="quarantined", reason_code=quarantine.reason_code)
        return self.stage(run, observation)

    def stage(
        self, run: IngestionRun | str, observation: SourceHoldingObservation
    ) -> StageResult:
        run_record = self._run(run)
        existing = self.session.query(SourceHoldingSnapshot).filter_by(
            source=observation.source,
            source_observation_key=observation.source_observation_key,
        ).one_or_none()
        if existing is not None:
            self.record_item_result(
                run_record, accepted=False, duplicate=True, commit=False
            )
            self.session.commit()
            return StageResult(status="duplicate", snapshot_id=existing.id)

        source_investor = self.session.query(SourceInvestor).filter_by(
            source=observation.source, source_key=observation.investor_key
        ).one_or_none()
        if source_investor is None:
            source_investor = SourceInvestor(
                source=observation.source,
                source_key=observation.investor_key,
                name_raw=observation.investor_name,
                name_normalized=normalize_name(observation.investor_name),
                profile_url=str(observation.source_url),
            )
            self.session.add(source_investor)

        source_security = self.session.query(SourceSecurity).filter_by(
            source=observation.source, source_key=observation.security_key
        ).one_or_none()
        if source_security is None:
            source_security = SourceSecurity(
                source=observation.source,
                source_key=observation.security_key,
                ticker_raw=normalize_ticker(observation.ticker),
                company_name_raw=observation.company_name,
                exchange=observation.exchange,
                share_class=observation.share_class,
                source_url=str(observation.source_url),
            )
            self.session.add(source_security)

        self.session.flush()
        fetch = (
            self.session.query(SourceFetch)
            .join(SourceDocument, SourceFetch.document_id == SourceDocument.id)
            .filter(
                SourceFetch.run_id == run_record.id,
                SourceDocument.source == observation.source,
                SourceDocument.content_hash == observation.document_hash,
            )
            .order_by(SourceFetch.fetched_at.desc())
            .first()
        )

        if observation.portfolio_manager_name:
            manager_name_normalized = normalize_name(observation.portfolio_manager_name)
            manager = self.session.query(SourcePortfolioManager).filter_by(
                source_investor_id=source_investor.id,
                name_normalized=manager_name_normalized,
            ).one_or_none()
            if manager is None:
                manager = SourcePortfolioManager(
                    source_investor=source_investor,
                    name_raw=observation.portfolio_manager_name,
                    name_normalized=manager_name_normalized,
                    source_url=str(observation.source_url),
                )
                self.session.add(manager)

        snapshot = SourceHoldingSnapshot(
            run=run_record,
            source=observation.source,
            source_investor=source_investor,
            source_security=source_security,
            period=observation.period,
            shares=observation.shares,
            value_usd=observation.value_usd,
            pct_portfolio=observation.pct_portfolio,
            source_activity=(
                observation.source_activity.strip().casefold()
                if observation.source_activity
                else None
            ),
            source_observation_key=observation.source_observation_key,
            fetch=fetch,
            raw_payload=observation.raw_payload,
        )
        self.session.add(snapshot)
        self.session.flush()
        staging = StagingHoldingSnapshot(
            run=run_record,
            source_snapshot=snapshot,
            period=observation.period,
            shares=observation.shares,
            value_usd=observation.value_usd,
            pct_portfolio=observation.pct_portfolio,
            validation_status="valid",
            identity_status="pending",
        )
        self.session.add(staging)
        self.record_item_result(run_record, accepted=True, commit=False)
        self.session.commit()
        return StageResult(status="staged", snapshot_id=snapshot.id)

    def promote(
        self, run_id: str, approved_mappings: Sequence[ApprovedMapping]
    ) -> PromotionResult:
        return promote_snapshots(self.session, run_id, approved_mappings)

    def project_events(
        self, snapshots: Sequence[CuratedHoldingSnapshot]
    ) -> list[CuratedHoldingEvent]:
        return project_events(snapshots)

    def finish_run(
        self, run_id: str, error_message: str | None = None
    ) -> IngestionRun:
        run = self._run(run_id)
        if error_message:
            run.status = "failed"
            run.error_message = error_message
        elif run.rows_seen == 0:
            run.status = "failed"
            run.error_message = run.error_message or "no rows seen"
        elif run.rows_rejected or self.pending_identity_count(run.id):
            run.status = "partial"
        else:
            run.status = "complete"
        run.finished_at = _utc_now()
        self.session.commit()
        return run

    def pending_identity_count(self, run_id: str) -> int:
        return self.session.query(func.count(StagingHoldingSnapshot.id)).filter_by(
            run_id=run_id, identity_status="pending"
        ).scalar()

    def count_source_snapshots(self, run_id: str) -> int:
        return self.session.query(func.count(SourceHoldingSnapshot.id)).filter_by(
            run_id=run_id
        ).scalar()

    def public_curated_count(self) -> int:
        return self.session.query(func.count(CuratedHoldingSnapshot.id)).scalar()

    def _run(self, run: IngestionRun | str) -> IngestionRun:
        if isinstance(run, IngestionRun):
            return run
        record = self.session.get(IngestionRun, run)
        if record is None:
            raise ValueError(f"Unknown ingestion run: {run}")
        return record
