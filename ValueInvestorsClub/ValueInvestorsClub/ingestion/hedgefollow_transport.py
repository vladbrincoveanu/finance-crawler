from __future__ import annotations

import base64
import binascii
import json
import random
import re
import time
from typing import Any


RESPONSE_XOR_KEY = (12, 124, 43, 99)


class HedgeFollowResponseError(ValueError):
    """Raised when HedgeFollow returns a response outside its live contract."""


def make_id_params() -> dict[str, int | list[int]]:
    """Build the short-lived request token expected by HedgeFollow's JS client."""
    arr = [random.randint(1000, 9999) for _ in range(3)]
    ts = int(time.time())
    d = random.randint(11, 18)
    p = random.randint(1, 2)
    checksum = sum(
        (1 if (index + p) % 2 == 0 else -1) * value
        for index, value in enumerate(arr)
    )
    return {
        "arr": arr,
        "ts": ts,
        "d": d,
        "p": p,
        "tk": (ts + checksum) // d,
        "mts": int(time.time() * 1000),
    }


def build_formdata(
    *, fund_id: str, quarter: str, id_params: dict[str, int | list[int]] | None = None
) -> list[tuple[str, str]]:
    filters = {
        "trade_value": "",
        "change_pp_submitted": "",
        "fund_id": fund_id,
        "quarter": quarter,
        "onlyBuySell": "all",
        "percent_of_portf": "all",
        "filter_ticker": "",
        "filter_stock_name": "",
    }
    filter_cols = {
        "trade_value": "trade_value",
        "change_pp_submitted": "change_pp_submitted",
        "fund_id": "fund_id",
        "quarter": "quarter",
        "onlyBuySell": "percentChange",
        "percent_of_portf": "PP",
        "filter_ticker": "symbol",
        "filter_stock_name": "stockName",
    }
    filter_checks = {
        "trade_value": "range",
        "change_pp_submitted": "absolute_greater_than",
        "fund_id": "function",
        "quarter": "function",
        "onlyBuySell": "function",
        "percent_of_portf": "range",
        "filter_ticker": "exact_text",
        "filter_stock_name": "text",
    }
    formdata = [
        ("params[requestId]", "fund_holdings"),
        ("params[page]", "filler"),
        ("params[filteredCt]", "100"),
        ("params[totalCt]", "100"),
        ("params[offset]", "0"),
        ("params[limit_per_page]", "100"),
        ("params[sortVar]", "PP"),
        ("params[sortOrder]", "-1"),
        ("symbol", "filler"),
        ("infotrac", "anotherfiller"),
    ]
    for group_name, values in (
        ("filters", filters),
        ("filter_cols", filter_cols),
        ("filter_checks", filter_checks),
    ):
        formdata.extend(
            (f"params[{group_name}][{key}]", str(value))
            for key, value in values.items()
        )

    token = id_params or make_id_params()
    formdata.extend(("id_params[arr][]", str(value)) for value in token["arr"])
    formdata.extend(
        (f"id_params[{key}]", str(token[key]))
        for key in ("ts", "d", "p", "tk", "mts")
    )
    return formdata


def _extract_ret_data_object(text: str) -> str:
    marker = re.search(r"(?:var\s+)?retDataObj\s*=", text)
    if not marker:
        raise HedgeFollowResponseError("HedgeFollow response did not contain retDataObj")
    start = text.find("{", marker.end())
    if start < 0:
        raise HedgeFollowResponseError("HedgeFollow retDataObj had no object body")

    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise HedgeFollowResponseError("HedgeFollow retDataObj was not closed")


def decode_response_payload(body: bytes | str) -> dict[str, Any]:
    try:
        encoded = body.decode("ascii", errors="strict") if isinstance(body, bytes) else body
        encrypted = base64.b64decode("".join(encoded.split()), validate=True)
        javascript = bytes(
            value ^ RESPONSE_XOR_KEY[index % len(RESPONSE_XOR_KEY)]
            for index, value in enumerate(encrypted)
        ).decode("utf-8")
    except (UnicodeDecodeError, ValueError, binascii.Error) as error:
        raise HedgeFollowResponseError(
            "HedgeFollow response was not valid base64/XOR data"
        ) from error

    object_text = _extract_ret_data_object(javascript)
    object_text = re.sub(
        r"([,{]\s*)([A-Za-z_$][\w$]*)\s*:",
        r'\1"\2":',
        object_text,
    )
    try:
        payload = json.loads(object_text)
    except json.JSONDecodeError as error:
        raise HedgeFollowResponseError(
            "HedgeFollow retDataObj was not valid JSON-like data"
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise HedgeFollowResponseError("HedgeFollow retDataObj did not contain data rows")
    return payload
