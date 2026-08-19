import json
from pathlib import Path

from ValueInvestorsClub.ValueInvestorsClub.ingestion.hedgefollow import (
    decode_response_payload,
    parse_equity_payload,
    parse_fund_page,
    parse_history_payload,
)
from ValueInvestorsClub.ValueInvestorsClub.ingestion.hedgefollow_transport import (
    RESPONSE_XOR_KEY,
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
    assert result.fund_id == "1067983"
    assert result.quarters == ["latest", "2026-03-31"]


def test_parse_fund_page_extracts_generic_summary_row_identity():
    result = parse_fund_page(
        """
        <title>Baupost Group Ma Portfolio | Seth Klarman</title>
        <table class="fundSummary">
          <tr><th>Hedge Fund</th><th>Portfolio Manager</th></tr>
          <tr><td>Baupost Group Ma</td><td>Seth Klarman</td></tr>
        </table>
        <script>requestId = 3185304;</script>
        <select data-id="quarter"><option value="latest"></option></select>
        """,
        url="https://hedgefollow.com/funds/Baupost+Group+Ma",
    )

    assert result.investor_key == "Baupost Group Ma"
    assert result.investor_name == "Baupost Group Ma"
    assert result.portfolio_manager_name == "Seth Klarman"
    assert result.fund_id == "1061768"


def test_decode_response_payload_unwraps_live_xor_base64_fixture():
    payload = decode_response_payload(
        (FIXTURES / "fund_holdings_berkshire.response.txt").read_text(encoding="ascii")
    )

    assert payload["params"]["requestId"] == "fund_holdings"
    assert {row["symbol"] for row in payload["data"]} == {
        "AAPL",
        "KO",
        "AAPL260621C00200000",
    }


def test_hedgefollow_transport_exposes_live_decoder_key():
    assert RESPONSE_XOR_KEY == (12, 124, 43, 99)


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
