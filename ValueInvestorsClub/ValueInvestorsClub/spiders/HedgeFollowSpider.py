from __future__ import annotations

import json
from urllib.parse import quote_plus

import scrapy

from ..ingestion.hedgefollow import (
    observation_to_item,
    parse_equity_payload,
    parse_fund_page,
)


class HedgeFollowSpider(scrapy.Spider):
    name = "HedgeFollowSpider"
    allowed_domains = ["hedgefollow.com"]

    def __init__(self, fund: str = "Berkshire Hathaway", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fund = fund

    @property
    def fund_url(self) -> str:
        return f"https://hedgefollow.com/funds/{quote_plus(self.fund)}"

    def start_requests(self):
        yield scrapy.Request(self.fund_url, callback=self.parse_fund)

    def parse_fund(self, response):
        identity = parse_fund_page(response.body, url=response.url)
        quarters = identity.quarters or ["latest"]
        for quarter in quarters:
            url = f"{response.url}?requestId=fund_holdings&quarter={quote_plus(quarter)}"
            yield scrapy.Request(
                url,
                callback=self.parse_holdings,
                meta={
                    "fund_key": identity.investor_key,
                    "fund_name": identity.investor_name,
                    "portfolio_manager_name": identity.portfolio_manager_name,
                    "source_url": response.url,
                },
            )

    def parse_holdings(self, response):
        payload = json.loads(response.text)
        rows = parse_equity_payload(
            payload,
            fund_key=response.meta["fund_key"],
            fund_name=response.meta["fund_name"],
            source_url=response.meta["source_url"],
            portfolio_manager_name=response.meta.get("portfolio_manager_name"),
        )
        for row in rows:
            yield observation_to_item(row)
