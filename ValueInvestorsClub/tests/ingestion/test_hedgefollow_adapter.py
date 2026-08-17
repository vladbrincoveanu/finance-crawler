import json
from pathlib import Path

from ValueInvestorsClub.ValueInvestorsClub.ingestion.hedgefollow import (
    parse_equity_payload,
    parse_fund_page,
    parse_history_payload,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "hedgefollow"


def _json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parse_fund_page_extracts_berkshire_identity():
    result = parse_fund_page(
        (FIXTURES / "fund_berkshire.html").read_text(encoding="utf-8"),
        url="https://hedgefollow.com/funds/Berkshire+Hathaway",
    )

    assert result.investor_key == "Berkshire Hathaway"
    assert result.investor_name == "Berkshire Hathaway"
    assert result.portfolio_manager_name == "Warren Buffett"
    assert result.quarters == ["latest", "2026-03-31"]


def test_parse_equity_payload_excludes_options():
    rows = parse_equity_payload(
        _json("fund_holdings_berkshire.json"),
        fund_key="Berkshire Hathaway",
        fund_name="Berkshire Hathaway",
        source_url="https://hedgefollow.com/funds/Berkshire+Hathaway",
    )

    assert rows
    assert all(row.instrument_type == "common_stock" for row in rows)
    assert {row.ticker for row in rows} >= {"AAPL", "KO"}


def test_parse_history_preserves_quarter_and_source_activity():
    rows = parse_history_payload(
        _json("fund_history_berkshire.json"),
        fund_key="Berkshire Hathaway",
        fund_name="Berkshire Hathaway",
        source_url="https://hedgefollow.com/funds/Berkshire+Hathaway",
    )

    assert any(row.period.isoformat() == "2026-03-31" for row in rows)
    assert any(row.source_activity in {"Buy", "Add", "Reduce", "Hold", None} for row in rows)
