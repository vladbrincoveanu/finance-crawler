#!/usr/bin/env python3
"""Write a local BRK holdings baseline after an explicitly run crawl."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Holding, Investor


def collect_baseline(session: Session, investor_id: str = "dataroma:BRK") -> dict:
    investor = session.get(Investor, investor_id)
    holdings = (
        session.query(Holding)
        .filter(Holding.investor_id == investor_id)
        .order_by(Holding.quarter_date)
        .all()
    )
    aapl = [holding for holding in holdings if holding.company_id == "AAPL"]
    return {
        "investor_id": investor_id,
        "investor_name": investor.name if investor else None,
        "row_count": len(holdings),
        "first_period": holdings[0].quarter_date.isoformat() if holdings else None,
        "last_period": holdings[-1].quarter_date.isoformat() if holdings else None,
        "aapl_shares": aapl[-1].shares if aapl else None,
        "aapl_value_usd": float(aapl[-1].value_usd) if aapl else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/dataroma-brk-baseline.json"),
    )
    args = parser.parse_args()
    database_url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/ideas"
    )
    engine = create_engine(database_url)
    with Session(engine) as session:
        baseline = collect_baseline(session)
    args.output.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote Dataroma baseline to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
