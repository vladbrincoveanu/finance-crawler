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
