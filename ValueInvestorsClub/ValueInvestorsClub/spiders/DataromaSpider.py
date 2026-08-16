import re
from datetime import date

import scrapy

try:
    # scrapy CLI runtime: PYTHONPATH puts the inner ValueInvestorsClub/ dir first
    from ValueInvestorsClub.holding_items import HoldingItem
except ModuleNotFoundError:
    # pytest runtime: pythonpath is the repo root only, so the package is nested
    from ValueInvestorsClub.ValueInvestorsClub.holding_items import HoldingItem

_QUARTER_END = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}


def _parse_period(text: str) -> str:
    # "2026 \xa0Q2" -> "2026-06-30"
    m = re.search(r"(\d{4}).*?(Q[1-4])", text or "")
    if not m:
        return ""
    year, quarter = int(m.group(1)), m.group(2)
    month, day = _QUARTER_END[quarter]
    return date(year, month, day).isoformat()


def _parse_money(text: str) -> float:
    return float((text or "").replace("$", "").replace(",", "") or 0)


def _parse_activity(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "hold"
    if t.startswith("Buy"):
        return "buy"
    if t.startswith("Add"):
        return "add"
    if t.startswith("Reduce"):
        return "reduce"
    return "hold"


class DataromaSpider(scrapy.Spider):
    name = "DataromaSpider"
    allowed_domains = ["dataroma.com"]
    start_urls = ["https://www.dataroma.com/m/home.php"]

    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse_home)

    def parse_home(self, response):
        for link in response.xpath("//li/a[contains(@href, 'holdings.php?m=')]"):
            href = link.xpath("./@href").get() or ""
            slug = href.split("m=", 1)[-1]
            name = (link.xpath("./text()").get() or "").strip()
            if not slug or not name:
                continue
            yield scrapy.Request(
                response.urljoin(href),
                callback=self.parse_holdings,
                meta={
                    "investor_slug": slug,
                    "investor_name": name,
                    "investor_profile_url": response.urljoin(href),
                },
            )

    def parse_holdings(self, response):
        investor_slug = response.meta["investor_slug"]
        for row in response.xpath("//table[@id='grid']/tbody/tr"):
            hist_href = row.xpath("./td[@class='hist']/a/@href").get()
            ticker = row.xpath("./td[@class='stock']/a/text()").get()
            company_name = row.xpath("./td[@class='stock']/a/span/text()").get() or ""
            if not hist_href or not ticker:
                continue
            yield scrapy.Request(
                response.urljoin(hist_href),
                callback=self.parse_stock_history,
                meta={
                    "investor_slug": investor_slug,
                    "investor_name": response.meta["investor_name"],
                    "investor_profile_url": response.meta["investor_profile_url"],
                    "ticker": ticker.strip(),
                    "company_name": company_name.lstrip("- ").strip(),
                },
            )

    def parse_stock_history(self, response):
        for row in response.xpath("//table[@id='grid']/tbody/tr"):
            cells = row.xpath("./td")
            if len(cells) < 6:
                continue
            quarter_date = _parse_period(cells[0].xpath("string()").get())
            shares_text = (cells[1].xpath("string()").get() or "").replace(",", "").strip()
            if not quarter_date or not shares_text:
                continue
            shares = int(shares_text)
            pct = float((cells[2].xpath("string()").get() or "0").strip() or 0)
            activity = _parse_activity(cells[3].xpath("string()").get())
            price = _parse_money(cells[5].xpath("string()").get())

            yield HoldingItem(
                investor_name=response.meta["investor_name"],
                investor_source="dataroma",
                investor_slug=response.meta["investor_slug"],
                investor_profile_url=response.meta["investor_profile_url"],
                ticker=response.meta["ticker"],
                company_name=response.meta["company_name"],
                quarter_date=quarter_date,
                shares=shares,
                value_usd=shares * price,
                pct_portfolio=pct,
                activity=activity,
            )
