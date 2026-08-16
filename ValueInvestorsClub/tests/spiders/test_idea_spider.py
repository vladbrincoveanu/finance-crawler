from pathlib import Path

from scrapy.http import HtmlResponse

from ValueInvestorsClub.ValueInvestorsClub.spiders.IdeaSpider import IdeaSpider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "idea"


def _response(name: str, url: str) -> HtmlResponse:
    body = (FIXTURES / name).read_bytes()
    return HtmlResponse(url=url, body=body)


def test_parse_extracts_date_iso_and_idea_id():
    spider = IdeaSpider()
    response = _response(
        "idea_page.html", "https://www.valueinvestorsclub.com/idea/Acme/5698302853"
    )

    items = list(spider.parse(response))

    assert len(items) == 1
    item = items[0]
    assert item["idea_id"] == "5698302853"
    assert item["date_iso"] == "2020-01-28"


def test_parse_extracts_photos():
    spider = IdeaSpider()
    response = _response(
        "idea_page.html", "https://www.valueinvestorsclub.com/idea/Acme/5698302853"
    )

    item = next(iter(spider.parse(response)))

    assert item["photos"] == [
        "https://www.valueinvestorsclub.com/images/moat-chart.png",
        "https://cdn.valueinvestorsclub.com/images/product.jpg",
    ]


def test_parse_extracts_comments():
    spider = IdeaSpider()
    response = _response(
        "idea_page.html", "https://www.valueinvestorsclub.com/idea/Acme/5698302853"
    )

    item = next(iter(spider.parse(response)))

    assert len(item["comments"]) == 2
    authors = {c["author"] for c in item["comments"]}
    assert authors == {"johnsmith", "janedoe"}
    assert "great writeup" in item["messages"]
