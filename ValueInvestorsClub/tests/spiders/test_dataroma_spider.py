from pathlib import Path

import scrapy
from scrapy.http import HtmlResponse

from ValueInvestorsClub.ValueInvestorsClub.spiders.DataromaSpider import DataromaSpider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "dataroma"


def _response(name: str, url: str) -> HtmlResponse:
    body = (FIXTURES / name).read_bytes()
    return HtmlResponse(url=url, body=body)


def test_parse_home_yields_one_request_per_investor():
    spider = DataromaSpider()
    response = _response("home.html", "https://www.dataroma.com/m/home.php")

    requests = list(spider.parse_home(response))

    assert len(requests) == 83
    brk = next(r for r in requests if r.meta["investor_slug"] == "BRK")
    assert brk.url == "https://www.dataroma.com/m/holdings.php?m=BRK"
    assert brk.meta["investor_name"] == "Warren Buffett - Berkshire Hathaway"


def test_parse_home_respects_investor_limit(monkeypatch):
    monkeypatch.setenv("DATAROMA_INVESTOR_LIMIT", "2")
    spider = DataromaSpider()
    response = _response("home.html", "https://www.dataroma.com/m/home.php")

    requests = list(spider.parse_home(response))

    assert len(requests) == 2


def test_parse_home_respects_requested_investor_slug():
    spider = DataromaSpider()
    spider.investor_slug = "BRK"
    response = _response("home.html", "https://www.dataroma.com/m/home.php")

    requests = list(spider.parse_home(response))

    assert len(requests) == 1
    assert requests[0].meta["investor_slug"] == "BRK"


def test_parse_holdings_yields_one_history_request_per_stock():
    spider = DataromaSpider()
    holdings_url = "https://www.dataroma.com/m/holdings.php?m=BRK"
    # Response.meta proxies to Request.meta (no setter of its own in scrapy>=2.x),
    # so the meta must be attached via the Request, as it would be in a real crawl.
    request = scrapy.Request(
        holdings_url,
        meta={
            "investor_slug": "BRK",
            "investor_name": "Warren Buffett - Berkshire Hathaway",
            "investor_profile_url": holdings_url,
        },
    )
    body = (FIXTURES / "holdings_brk.html").read_bytes()
    response = HtmlResponse(url=holdings_url, body=body, request=request)

    requests = list(spider.parse_holdings(response))

    aapl = next(r for r in requests if r.meta["ticker"] == "AAPL")
    assert aapl.url == "https://www.dataroma.com/m/hist/hist.php?f=BRK&s=AAPL"
    assert aapl.meta["company_name"] == "Apple Inc."
    assert aapl.meta["investor_slug"] == "BRK"


def test_parse_stock_history_yields_one_holding_item_per_quarter():
    spider = DataromaSpider()
    hist_url = "https://www.dataroma.com/m/hist/hist.php?f=BRK&s=AAPL"
    # Response.meta proxies to Request.meta (no setter of its own in scrapy>=2.x),
    # so the meta must be attached via the Request, as it would be in a real crawl.
    request = scrapy.Request(
        hist_url,
        meta={
            "investor_slug": "BRK",
            "investor_name": "Warren Buffett - Berkshire Hathaway",
            "investor_profile_url": "https://www.dataroma.com/m/holdings.php?m=BRK",
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
        },
    )
    body = (FIXTURES / "hist_brk_aapl.html").read_bytes()
    response = HtmlResponse(url=hist_url, body=body, request=request)

    items = list(spider.parse_stock_history(response))

    q2 = next(i for i in items if i["quarter_date"] == "2026-06-30")
    assert q2["shares"] == 227917808
    assert q2["pct_portfolio"] == 22.04
    assert q2["activity"] == "hold"
    assert round(q2["value_usd"]) == round(227917808 * 289.36)

    q4_2025 = next(i for i in items if i["quarter_date"] == "2025-12-31")
    assert q4_2025["activity"] == "reduce"
