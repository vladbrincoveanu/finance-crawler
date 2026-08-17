from pathlib import Path

import scrapy
from scrapy.http import HtmlResponse

from ValueInvestorsClub.ValueInvestorsClub.ingestion.dataroma import (
    observation_from_item,
    page_from_response,
)
from ValueInvestorsClub.ValueInvestorsClub.spiders.DataromaSpider import DataromaSpider


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "dataroma"


def _response(name: str, url: str) -> HtmlResponse:
    return HtmlResponse(url=url, body=(FIXTURES / name).read_bytes())


def test_dataroma_adapter_emits_page_and_stable_source_observation():
    spider = DataromaSpider()
    url = "https://www.dataroma.com/m/hist/hist.php?f=BRK&s=AAPL"
    response = HtmlResponse(
        url=url,
        body=(FIXTURES / "hist_brk_aapl.html").read_bytes(),
        request=scrapy.Request(
            url,
            meta={
                "investor_slug": "BRK",
                "investor_name": "Warren Buffett - Berkshire Hathaway",
                "investor_profile_url": "https://www.dataroma.com/m/holdings.php?m=BRK",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
            },
        ),
    )
    item = next(item for item in spider.parse_stock_history(response) if item["quarter_date"] == "2026-06-30")

    page = page_from_response(response)
    observation = observation_from_item(item)

    assert page.source == "dataroma"
    assert page.body == response.body
    assert observation.source_observation_key == "dataroma:BRK:AAPL:2026-06-30"
    assert observation.document_hash == page.content_hash
    assert str(observation.source_url) == response.url
    assert observation.period.isoformat() == "2026-06-30"
