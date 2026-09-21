from __future__ import annotations

from typing import Any

import ccxt.async_support as ccxt


def build_ccxt_exchange(exchange_id: str, api_key: str, secret: str) -> Any:
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({
        "apiKey": api_key,
        "secret": secret,
        "enableRateLimit": True,
    })
