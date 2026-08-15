from pathlib import Path
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
