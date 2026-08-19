from __future__ import annotations

import hashlib
import os
from decimal import DecimalException
from urllib.parse import quote_plus

import scrapy

from ..ingestion.hedgefollow import (
    HedgeFollowResponseError,
    build_formdata,
    decode_response_payload,
    observation_to_item,
    parse_equity_payload,
    parse_fund_page,
)


class HedgeFollowSpider(scrapy.Spider):
    name = "HedgeFollowSpider"
    source = "hedgefollow"
    parser_version = "hedgefollow-v1"
    allowed_domains = ["hedgefollow.com"]
    ajax_url = "https://hedgefollow.com/ggg/web_request.php"

    def __init__(self, fund: str = "Berkshire Hathaway", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fund = fund

    @property
    def fund_url(self) -> str:
        return f"https://hedgefollow.com/funds/{quote_plus(self.fund)}"

    def start_requests(self):
        yield scrapy.Request(self.fund_url, callback=self.parse_fund)

    async def start(self):
        for request in self.start_requests():
            yield request

    def parse_fund(self, response):
        identity = parse_fund_page(response.body, url=response.url)
        if not identity.fund_id:
            self._record_response_error(response, "fund page did not expose numeric requestId")
            return
        quarters = self._selected_quarters(identity.quarters)
        for quarter in quarters:
            yield scrapy.FormRequest(
                self.ajax_url,
                formdata=build_formdata(fund_id=identity.fund_id, quarter=quarter),
                headers={
                    "Accept": "*/*",
                    "Referer": response.url,
                    "X-Requested-With": "XMLHttpRequest",
                },
                callback=self.parse_holdings,
                meta={
                    "fund_key": identity.investor_key,
                    "fund_name": identity.investor_name,
                    "fund_id": identity.fund_id,
                    "quarter": quarter,
                    "portfolio_manager_name": identity.portfolio_manager_name,
                    "source_url": response.url,
                    "handle_httpstatus_all": True,
                },
            )

    def parse_holdings(self, response):
        if response.status != 200:
            self._record_response_error(response, f"HTTP {response.status}")
            return
        try:
            payload = decode_response_payload(response.body)
        except HedgeFollowResponseError as error:
            self._record_response_error(response, str(error))
            return
        try:
            rows = parse_equity_payload(
                payload,
                fund_key=response.meta["fund_key"],
                fund_name=response.meta["fund_name"],
                source_url=response.meta["source_url"],
                portfolio_manager_name=response.meta.get("portfolio_manager_name"),
                document_hash=hashlib.sha256(response.body).hexdigest(),
            )
        except (DecimalException, TypeError, ValueError) as error:
            self._record_response_error(response, f"invalid holdings payload: {error}")
            return
        for row in rows:
            yield observation_to_item(row)

    def _selected_quarters(self, quarters: list[str]) -> list[str]:
        configured = os.getenv("HEDGEFOLLOW_QUARTERS")
        values = configured.split(",") if configured else quarters
        unique = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        try:
            limit = max(1, int(os.getenv("HEDGEFOLLOW_QUARTER_LIMIT", "1")))
        except ValueError:
            limit = 1
        return (unique or ["latest"])[:limit]

    def _record_response_error(self, response, detail: str) -> None:
        self.logger.error(
            "HedgeFollow response error for %s (status=%s): %s",
            response.url,
            response.status,
            detail,
        )
        crawler = getattr(self, "crawler", None)
        stats = getattr(crawler, "stats", None)
        if stats is not None and hasattr(stats, "inc_value"):
            stats.inc_value("hedgefollow/response_errors")
        engine = getattr(crawler, "engine", None)
        close_spider = getattr(engine, "close_spider", None)
        if callable(close_spider):
            close_spider(self, reason="hedgefollow_response_error")
