from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base
from ValueInvestorsClub.ValueInvestorsClub.models.curated import CuratedHoldingEvent
from ValueInvestorsClub.ValueInvestorsClub.models.source import (
    SourceHoldingSnapshot,
    SourceInvestor,
    SourceSecurity,
)


def test_source_snapshot_does_not_derive_curated_event_on_insert():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    with Session(engine) as session:
        investor = SourceInvestor(
            source="dataroma",
            source_key="BRK",
            name_raw="Berkshire Hathaway",
            name_normalized="berkshire hathaway",
        )
        security = SourceSecurity(
            source="dataroma",
            source_key="AAPL",
            ticker_raw="AAPL",
            company_name_raw="Apple Inc.",
        )
        snapshot = SourceHoldingSnapshot(
            source="dataroma",
            source_investor=investor,
            source_security=security,
            period=date(2026, 6, 30),
            source_activity="hold",
            source_observation_key="dataroma:BRK:AAPL:2026-06-30",
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.source_activity == "hold"
        assert session.query(CuratedHoldingEvent).count() == 0
