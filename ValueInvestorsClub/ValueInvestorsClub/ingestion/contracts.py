from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class SourcePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["dataroma", "hedgefollow"]
    url: AnyUrl
    status_code: int
    content_type: str
    body: bytes
    fetched_at: datetime
    parser_version: str


class SourceHoldingObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["dataroma", "hedgefollow"]
    investor_key: str = Field(min_length=1)
    investor_name: str = Field(min_length=1)
    portfolio_manager_name: str | None = None
    security_key: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    instrument_type: Literal["common_stock", "option"] = "common_stock"
    exchange: str | None = None
    share_class: str | None = None
    period: date
    shares: int | None = Field(default=None, ge=0)
    value_usd: Decimal | None = Field(default=None, ge=0)
    pct_portfolio: Decimal | None = Field(default=None, ge=0, le=100)
    source_activity: str | None = None
    source_url: AnyUrl
    source_observation_key: str = Field(min_length=1)
    document_hash: str = Field(min_length=1)
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class StageResult:
    status: Literal["staged", "duplicate", "quarantined"]
    reason_code: str | None = None
    snapshot_id: str | None = None


@dataclass(frozen=True)
class ApprovedMapping:
    source_investor_id: str
    curated_investor_id: str
    source_security_id: str
    curated_security_id: str


@dataclass(frozen=True)
class PromotionResult:
    accepted: int
    pending_identity: int
