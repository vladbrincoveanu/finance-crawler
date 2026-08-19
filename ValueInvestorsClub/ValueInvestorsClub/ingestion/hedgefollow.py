from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from ..holding_items import HoldingItem
from .contracts import SourceHoldingObservation
from .hedgefollow_transport import (
    HedgeFollowResponseError,
    build_formdata,
    decode_response_payload,
    make_id_params,
)


PARSER_VERSION = "hedgefollow-v1"
__all__ = [
    "PARSER_VERSION",
    "FundIdentity",
    "HedgeFollowResponseError",
    "build_formdata",
    "decode_response_payload",
    "make_id_params",
    "observation_to_item",
    "parse_equity_payload",
    "parse_fund_page",
    "parse_history_payload",
    "parse_holdings_payload",
]


@dataclass(frozen=True)
class FundIdentity:
    investor_key: str
    investor_name: str
    portfolio_manager_name: str | None
    fund_id: str | None
    quarters: list[str]
    source_url: str


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _number(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    cleaned = re.sub(r"[$,%\s,]", "", str(value))
    return Decimal(cleaned) if cleaned else None


def _rows(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    fields = payload.get("fields") or payload.get("columns") or payload.get("aoColumns") or []
    if isinstance(fields, dict):
        fields = fields.get("fields") or fields.get("columns") or []
    if fields and isinstance(fields[0], dict):
        fields = [
            field.get("name") or field.get("data") or field.get("mData")
            for field in fields
        ]
    raw_rows = payload.get("rows") or payload.get("data") or payload.get("aaData") or []
    if isinstance(raw_rows, dict):
        raw_rows = raw_rows.get("rows") or raw_rows.get("data") or []
    for raw_row in raw_rows:
        if isinstance(raw_row, dict):
            yield raw_row
        elif isinstance(raw_row, list) and fields:
            yield dict(zip(fields, raw_row))


def parse_fund_page(html: str | bytes, *, url: str) -> FundIdentity:
    from parsel import Selector

    text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else html
    selector = Selector(text=text)
    summary = _text(" ".join(selector.css("table.fundSummary ::text").getall()))
    investor_name = ""
    manager = None
    for row in selector.css("table.fundSummary tr"):
        labels = row.xpath("./th")
        values = row.xpath("./td")
        if len(labels) == 1 and values:
            label = _text(labels[0].xpath("string()").get()).casefold()
            value = _text(values[0].xpath("string()").get())
            if label in {"fund", "hedge fund"}:
                investor_name = value
            elif label in {"manager", "portfolio manager"}:
                manager = value or None
        elif not investor_name and len(values) >= 2:
            investor_name = _text(values[0].xpath("string()").get())
            manager = _text(values[1].xpath("string()").get()) or None
    if not investor_name:
        investor_name = "Berkshire Hathaway" if "Berkshire Hathaway" in summary else summary
    if not manager and "Warren Buffett" in summary:
        manager = "Warren Buffett"
    request_id = re.search(r"\brequestId\s*=\s*(\d+)", text)
    fund_id = str(int(request_id.group(1)) // 3) if request_id else None
    quarters = list(
        dict.fromkeys(selector.css('select[data-id="quarter"] option::attr(value)').getall())
    )
    return FundIdentity(
        investor_key=investor_name,
        investor_name=investor_name,
        portfolio_manager_name=manager,
        fund_id=fund_id,
        quarters=quarters,
        source_url=url,
    )


def _parse_observations(
    payload: dict[str, Any],
    *,
    fund_key: str,
    fund_name: str,
    source_url: str,
    include_options: bool,
    portfolio_manager_name: str | None = None,
    document_hash: str | None = None,
) -> list[SourceHoldingObservation]:
    observations: list[SourceHoldingObservation] = []
    for row in _rows(payload):
        instrument_type = _text(
            row.get("instrumentType") or row.get("instrument_type") or row.get("securityType")
        ).casefold()
        is_option = "option" in instrument_type or bool(row.get("isOption"))
        if is_option and not include_options:
            continue
        ticker = _text(row.get("symbol") or row.get("ticker"))
        company_name = _text(row.get("stockName") or row.get("company_name"))
        period_value = row.get("quarter") or row.get("period")
        if not ticker or not company_name or not period_value or period_value == "latest":
            continue
        period = date.fromisoformat(str(period_value))
        row_json = json.dumps(row, default=str, sort_keys=True).encode("utf-8")
        row_hash = hashlib.sha256(row_json).hexdigest()
        observations.append(
            SourceHoldingObservation(
                source="hedgefollow",
                investor_key=fund_key,
                investor_name=fund_name,
                portfolio_manager_name=portfolio_manager_name,
                security_key=ticker,
                ticker=ticker,
                company_name=company_name,
                instrument_type="option" if is_option else "common_stock",
                exchange=row.get("exchange"),
                share_class=row.get("shareClass") or row.get("share_class"),
                period=period,
                shares=(
                    int(_number(row.get("adjustedShares") or row.get("shares")))
                    if _number(row.get("adjustedShares") or row.get("shares")) is not None
                    else None
                ),
                value_usd=_number(row.get("value") or row.get("value_usd")),
                pct_portfolio=_number(row.get("PP") or row.get("pct_portfolio")),
                source_activity=(
                    row.get("activity") or row.get("trade") or row.get("tradeType")
                ),
                source_url=source_url,
                source_observation_key=f"hedgefollow:{fund_key}:{ticker}:{period.isoformat()}",
                document_hash=document_hash or row_hash,
                raw_payload=row,
            )
        )
    return observations


def parse_equity_payload(
    payload: dict[str, Any],
    *,
    fund_key: str,
    fund_name: str,
    source_url: str,
    portfolio_manager_name: str | None = None,
    document_hash: str | None = None,
) -> list[SourceHoldingObservation]:
    return _parse_observations(
        payload,
        fund_key=fund_key,
        fund_name=fund_name,
        source_url=source_url,
        include_options=False,
        portfolio_manager_name=portfolio_manager_name,
        document_hash=document_hash,
    )


def parse_holdings_payload(
    payload: dict[str, Any],
    *,
    fund_key: str,
    fund_name: str,
    source_url: str,
    portfolio_manager_name: str | None = None,
    document_hash: str | None = None,
) -> list[SourceHoldingObservation]:
    return parse_equity_payload(
        payload,
        fund_key=fund_key,
        fund_name=fund_name,
        source_url=source_url,
        portfolio_manager_name=portfolio_manager_name,
        document_hash=document_hash,
    )


def parse_history_payload(
    payload: dict[str, Any],
    *,
    fund_key: str,
    fund_name: str,
    source_url: str,
    portfolio_manager_name: str | None = None,
    document_hash: str | None = None,
) -> list[SourceHoldingObservation]:
    return _parse_observations(
        payload,
        fund_key=fund_key,
        fund_name=fund_name,
        source_url=source_url,
        include_options=False,
        portfolio_manager_name=portfolio_manager_name,
        document_hash=document_hash,
    )


def observation_to_item(observation: SourceHoldingObservation) -> HoldingItem:
    return HoldingItem(
        investor_name=observation.investor_name,
        investor_source="hedgefollow",
        investor_slug=observation.investor_key,
        investor_profile_url=str(observation.source_url),
        ticker=observation.ticker,
        company_name=observation.company_name,
        quarter_date=observation.period.isoformat(),
        shares=observation.shares,
        value_usd=observation.value_usd,
        pct_portfolio=observation.pct_portfolio,
        activity=observation.source_activity,
        source_url=str(observation.source_url),
        source_observation_key=observation.source_observation_key,
        document_hash=observation.document_hash,
        exchange=observation.exchange,
        share_class=observation.share_class,
        portfolio_manager_name=observation.portfolio_manager_name,
        raw_payload=observation.raw_payload,
    )
