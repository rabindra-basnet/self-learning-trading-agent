"""Yahoo raw client — HTTP specifics confined here.

Exposes only validated vendor payloads (`YahooChartResult`) for `mapping.py`.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.exceptions.taxonomy import MalformedDataError
from app.infrastructure.tooling.http import JsonHttpClient
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.config import YahooConfig
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.dtos import (
    YahooChartResult,
    YahooEnvelope,
)
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.errors import (
    handle_yahoo_error,
    handle_yahoo_validation_error,
)

_PROVIDER = "yahoo"


class YahooRawClient:
    def __init__(self, config: YahooConfig) -> None:
        self._http = JsonHttpClient(
            config.base_url,
            provider=_PROVIDER,
            timeout_sec=config.timeout_sec,
            headers={"User-Agent": config.user_agent, "Accept": "application/json"},
        )

    async def fetch_chart(
        self,
        symbol_code: str,
        interval: str,
        *,
        period1: int | None = None,
        period2: int | None = None,
        window: str = "1mo",
    ) -> YahooChartResult:
        params: dict[str, Any] = {"interval": interval, "includePrePost": "false"}
        if period1 is not None and period2 is not None:
            params["period1"] = period1
            params["period2"] = period2
        else:
            params["range"] = window
        payload = await self._http.get_json(f"/v8/finance/chart/{symbol_code}", params)
        try:
            envelope = YahooEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise handle_yahoo_validation_error(exc) from exc
        if envelope.chart.error:
            raise handle_yahoo_error(envelope.chart.error)
        if not envelope.chart.result:
            raise MalformedDataError("yahoo chart returned no result", provider=_PROVIDER)
        return envelope.chart.result[0]

    async def close(self) -> None:
        await self._http.aclose()
