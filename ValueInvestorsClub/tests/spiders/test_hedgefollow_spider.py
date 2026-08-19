import asyncio
import hashlib
from decimal import InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

import scrapy
from scrapy.http import HtmlResponse, TextResponse

from ValueInvestorsClub.ValueInvestorsClub.ingestion.hedgefollow import (
    make_id_params,
)
from ValueInvestorsClub.ValueInvestorsClub.spiders.HedgeFollowSpider import HedgeFollowSpider


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "hedgefollow"
FUND_URL = "https://hedgefollow.com/funds/Berkshire+Hathaway"
AJAX_URL = "https://hedgefollow.com/ggg/web_request.php"


def test_hedgefollow_spider_starts_selected_berkshire_fund():
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")

    assert spider.source == "hedgefollow"
    assert spider.parser_version == "hedgefollow-v1"
    requests = list(spider.start_requests())

    assert len(requests) == 1
    assert requests[0].url == "https://hedgefollow.com/funds/Berkshire+Hathaway"


def test_hedgefollow_spider_async_start_yields_fund_request():
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")

    async def collect_requests():
        return [request async for request in spider.start()]

    requests = asyncio.run(collect_requests())

    assert len(requests) == 1
    assert requests[0].url == FUND_URL


def _fund_response() -> HtmlResponse:
    request = scrapy.Request(FUND_URL)
    return HtmlResponse(
        url=FUND_URL,
        body=(FIXTURES / "fund_berkshire.html").read_bytes(),
        request=request,
    )


def _holding_response(body: bytes, request: scrapy.Request) -> TextResponse:
    return TextResponse(url=AJAX_URL, body=body, encoding="utf-8", request=request)


def test_parse_fund_posts_one_bounded_quarter_with_live_form_contract():
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")

    requests = list(spider.parse_fund(_fund_response()))

    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, scrapy.FormRequest)
    assert request.method == "POST"
    assert request.url == AJAX_URL
    assert request.headers["X-Requested-With"] == b"XMLHttpRequest"
    assert request.headers["Referer"] == FUND_URL.encode()

    fields = parse_qs(request.body.decode("ascii"), keep_blank_values=True)
    assert fields["params[requestId]"] == ["fund_holdings"]
    assert fields["params[page]"] == ["filler"]
    assert fields["params[filteredCt]"] == ["100"]
    assert fields["params[limit_per_page]"] == ["100"]
    assert fields["params[filters][trade_value]"] == [""]
    assert fields["params[filters][change_pp_submitted]"] == [""]
    assert fields["params[filters][fund_id]"] == ["1067983"]
    assert fields["params[filters][quarter]"] == ["latest"]
    assert fields["params[filter_cols][fund_id]"] == ["fund_id"]
    assert fields["params[filter_cols][quarter]"] == ["quarter"]
    assert fields["params[filter_cols][onlyBuySell]"] == ["percentChange"]
    assert fields["params[filter_checks][fund_id]"] == ["function"]
    assert fields["id_params[arr][]"] and len(fields["id_params[arr][]"]) == 3
    assert all(1000 <= int(value) <= 9999 for value in fields["id_params[arr][]"])
    assert 11 <= int(fields["id_params[d]"][0]) <= 18
    assert int(fields["id_params[p]"][0]) in {1, 2}
    assert request.meta["fund_id"] == "1067983"
    assert request.meta["quarter"] == "latest"


def test_parse_fund_honors_explicit_quarter_limit_without_duplicates(monkeypatch):
    monkeypatch.setenv("HEDGEFOLLOW_QUARTER_LIMIT", "2")
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")

    requests = list(spider.parse_fund(_fund_response()))

    assert [request.meta["quarter"] for request in requests] == [
        "latest",
        "2026-03-31",
    ]


def test_parse_holdings_decodes_fixture_response_and_yields_common_stock_items():
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")
    request = scrapy.FormRequest(
        AJAX_URL,
        formdata={"params[requestId]": "fund_holdings"},
        meta={
            "fund_key": "Berkshire Hathaway",
            "fund_name": "Berkshire Hathaway",
            "fund_id": "1067983",
            "quarter": "latest",
            "source_url": FUND_URL,
            "portfolio_manager_name": "Warren Buffett",
        },
    )
    response = _holding_response(
        (FIXTURES / "fund_holdings_berkshire.response.txt").read_bytes(),
        request,
    )

    items = list(spider.parse_holdings(response))

    assert {item["ticker"] for item in items} == {"AAPL", "KO"}
    assert all(item["investor_slug"] == "Berkshire Hathaway" for item in items)
    assert {item["document_hash"] for item in items} == {
        hashlib.sha256(response.body).hexdigest()
    }


def test_parse_holdings_closes_spider_with_clear_status_for_non_json_response(caplog):
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")
    closed = []
    stats = {}
    spider.crawler = SimpleNamespace(
        engine=SimpleNamespace(close_spider=lambda current, reason: closed.append(reason)),
        stats=SimpleNamespace(inc_value=lambda key: stats.__setitem__(key, stats.get(key, 0) + 1)),
    )
    request = scrapy.FormRequest(
        AJAX_URL,
        formdata={"params[requestId]": "fund_holdings"},
        meta={
            "fund_key": "Berkshire Hathaway",
            "fund_name": "Berkshire Hathaway",
            "source_url": FUND_URL,
        },
    )
    response = _holding_response(b"\xff\xfe", request)

    with caplog.at_level("ERROR"):
        assert list(spider.parse_holdings(response)) == []

    assert closed == ["hedgefollow_response_error"]
    assert stats["hedgefollow/response_errors"] == 1
    assert "HedgeFollow" in caplog.text


def test_parse_holdings_closes_spider_when_decoded_rows_are_invalid(monkeypatch):
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")
    closed = []
    spider.crawler = SimpleNamespace(
        engine=SimpleNamespace(close_spider=lambda current, reason: closed.append(reason)),
        stats=SimpleNamespace(inc_value=lambda key: None),
    )
    monkeypatch.setattr(
        "ValueInvestorsClub.ValueInvestorsClub.spiders.HedgeFollowSpider.parse_equity_payload",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid quarter")),
    )
    request = scrapy.FormRequest(
        AJAX_URL,
        formdata={"params[requestId]": "fund_holdings"},
        meta={
            "fund_key": "Berkshire Hathaway",
            "fund_name": "Berkshire Hathaway",
            "source_url": FUND_URL,
        },
    )
    response = _holding_response(
        (FIXTURES / "fund_holdings_berkshire.response.txt").read_bytes(),
        request,
    )

    assert list(spider.parse_holdings(response)) == []
    assert closed == ["hedgefollow_response_error"]


def test_parse_holdings_closes_spider_when_numeric_values_are_invalid(monkeypatch):
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")
    closed = []
    spider.crawler = SimpleNamespace(
        engine=SimpleNamespace(close_spider=lambda current, reason: closed.append(reason)),
        stats=SimpleNamespace(inc_value=lambda key: None),
    )
    monkeypatch.setattr(
        "ValueInvestorsClub.ValueInvestorsClub.spiders.HedgeFollowSpider.parse_equity_payload",
        lambda *args, **kwargs: (_ for _ in ()).throw(InvalidOperation("invalid value")),
    )
    request = scrapy.FormRequest(
        AJAX_URL,
        formdata={"params[requestId]": "fund_holdings"},
        meta={
            "fund_key": "Berkshire Hathaway",
            "fund_name": "Berkshire Hathaway",
            "source_url": FUND_URL,
        },
    )
    response = _holding_response(
        (FIXTURES / "fund_holdings_berkshire.response.txt").read_bytes(),
        request,
    )

    assert list(spider.parse_holdings(response)) == []
    assert closed == ["hedgefollow_response_error"]


def test_make_id_params_uses_live_token_contract(monkeypatch):
    values = iter([1234, 5678, 9012, 14, 2])
    monkeypatch.setattr(
        "ValueInvestorsClub.ValueInvestorsClub.ingestion.hedgefollow_transport.random.randint",
        lambda _minimum, _maximum: next(values),
    )
    monkeypatch.setattr(
        "ValueInvestorsClub.ValueInvestorsClub.ingestion.hedgefollow_transport.time.time",
        lambda: 1_700_000_000.123,
    )

    result = make_id_params()

    assert result["arr"] == [1234, 5678, 9012]
    assert result["ts"] == 1_700_000_000
    assert result["d"] == 14
    assert result["p"] == 2
    assert result["tk"] == (1_700_000_000 + 1234 - 5678 + 9012) // 14
    assert result["mts"] == 1_700_000_000_123
