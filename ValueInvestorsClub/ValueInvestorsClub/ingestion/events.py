from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Sequence

from ..models.curated import CuratedHoldingEvent


def _next_quarter_end(period: date) -> date | None:
    quarter_ends = {(3, 31), (6, 30), (9, 30), (12, 31)}
    if (period.month, period.day) not in quarter_ends:
        return None
    month = period.month + 3
    year = period.year
    if month > 12:
        year += 1
        month -= 12
    return date(year, month, monthrange(year, month)[1])


def _event_type(previous, current) -> tuple[str, Decimal]:
    if _next_quarter_end(previous.period) != current.period:
        return "unknown", Decimal("0.0000")
    if previous.shares is None or current.shares is None:
        return "unknown", Decimal("0.0000")
    if current.shares == 0 and previous.shares > 0:
        return "exit", Decimal("1.0000")
    if current.shares > previous.shares:
        return "add", Decimal("1.0000")
    if current.shares < previous.shares:
        return "reduce", Decimal("1.0000")
    return "hold", Decimal("1.0000")


def project_events(snapshots: Sequence) -> list[CuratedHoldingEvent]:
    ordered = sorted(snapshots, key=lambda snapshot: snapshot.period)
    if not ordered:
        return []

    events = [
        CuratedHoldingEvent(
            curated_investor_id=ordered[0].curated_investor_id,
            curated_security_id=ordered[0].curated_security_id,
            period=ordered[0].period,
            event_type="open",
            evidence_snapshot_ids=[str(ordered[0].id)],
            confidence=Decimal("1.0000"),
        )
    ]
    for previous, current in zip(ordered, ordered[1:]):
        event_type, confidence = _event_type(previous, current)
        events.append(
            CuratedHoldingEvent(
                curated_investor_id=current.curated_investor_id,
                curated_security_id=current.curated_security_id,
                period=current.period,
                event_type=event_type,
                evidence_snapshot_ids=[str(previous.id), str(current.id)],
                confidence=confidence,
            )
        )
    return events
