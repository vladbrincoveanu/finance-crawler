import os
import re
from datetime import date
from hashlib import sha256

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
    source = "dataroma"
    parser_version = "dataroma-v1"
    allowed_domains = ["dataroma.com"]
    start_urls = ["https://www.dataroma.com/m/home.php"]

    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse_home)

    def parse_home(self, response):
        limit = int(os.getenv("DATAROMA_INVESTOR_LIMIT", "0"))
        requested_slug = (getattr(self, "investor_slug", "") or "").strip()
        links = response.xpath("//li/a[contains(@href, 'holdings.php?m=')]")
        if requested_slug:
            links = [
                link
                for link in links
                if (link.xpath("./@href").get() or "").split("m=", 1)[-1]
                == requested_slug
            ]
        if limit > 0:
            links = links[:limit]
        for link in links:
            href = link.xpath("./@href").get() or ""
            slug = href.split("m=", 1)[-1]
            name = (link.xpath("./text()").get() or "").strip()
            if not slug or not name or (requested_slug and slug != requested_slug):
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
                    "source_url": response.urljoin(hist_href),
                },
            )

    def parse_stock_history(self, response):
        response_document_hash = sha256(response.body).hexdigest()
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
            source_observation_key = (
                f"dataroma:{response.meta['investor_slug']}:{response.meta['ticker']}:{quarter_date}"
            )

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
                source_url=response.url,
                source_observation_key=source_observation_key,
                document_hash=response_document_hash,
                exchange=None,
                share_class=None,
                portfolio_manager_name=None,
                raw_payload={
                    "period_text": cells[0].xpath("string()").get(),
                    "shares_text": shares_text,
                    "activity_text": cells[3].xpath("string()").get(),
                    "price_text": cells[5].xpath("string()").get(),
                },
            )
