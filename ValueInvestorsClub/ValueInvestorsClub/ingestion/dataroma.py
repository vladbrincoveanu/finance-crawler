from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from ..holding_items import HoldingItem
from ..ingestion.contracts import SourceHoldingObservation, SourcePage


PARSER_VERSION = "dataroma-v1"


def document_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def page_from_response(response, parser_version: str = PARSER_VERSION) -> SourcePage:
    content_type = response.headers.get(b"Content-Type", b"text/html")
    if isinstance(content_type, bytes):
        content_type = content_type.decode("latin-1")
    return SourcePage(
        source="dataroma",
        url=response.url,
        status_code=response.status,
        content_type=content_type,
        body=response.body,
        fetched_at=datetime.now(timezone.utc),
        parser_version=parser_version,
    )


def observation_from_item(item: HoldingItem) -> SourceHoldingObservation:
    payload = dict(item)
    source_url = item.get("source_url") or item.get("investor_profile_url")
    observation_key = item.get("source_observation_key") or (
        f"dataroma:{item['investor_slug']}:{item['ticker']}:{item['quarter_date']}"
    )
    raw_payload: dict[str, Any] = item.get("raw_payload") or payload
    serialized = json.dumps(raw_payload, default=str, sort_keys=True).encode("utf-8")
    return SourceHoldingObservation(
        source="dataroma",
        investor_key=item["investor_slug"],
        investor_name=item["investor_name"],
        portfolio_manager_name=item.get("portfolio_manager_name"),
        security_key=item["ticker"],
        ticker=item["ticker"],
        company_name=item["company_name"],
        period=item["quarter_date"],
        shares=item.get("shares"),
        value_usd=(
            Decimal(str(item["value_usd"])) if item.get("value_usd") is not None else None
        ),
        pct_portfolio=(
            Decimal(str(item["pct_portfolio"]))
            if item.get("pct_portfolio") is not None
            else None
        ),
        source_activity=item.get("activity"),
        source_url=source_url,
        source_observation_key=observation_key,
        document_hash=item.get("document_hash") or document_hash(serialized),
        raw_payload=raw_payload,
    )
