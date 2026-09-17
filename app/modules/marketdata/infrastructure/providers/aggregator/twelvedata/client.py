"""Twelve Data raw client — HTTP specifics confined here.

Exposes only validated vendor payloads for `mapping.py`; the `apikey` never
appears in logs or error messages.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.exceptions.taxonomy import MalformedDataError
from app.infrastructure.tooling.http import JsonHttpClient
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.config import (
    TwelveDataConfig,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.dtos import (
    TwelveQuote,
    TwelveTimeSeries,
)
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.errors import (
    handle_twelvedata_error,
)

_PROVIDER = "twelvedata"


class TwelveDataRawClient:
    def __init__(self, config: TwelveDataConfig) -> None:
        self._config = config
        self._http = JsonHttpClient(
            config.base_url,
            provider=_PROVIDER,
            timeout_sec=config.timeout_sec,
            headers={"Accept": "application/json"},
        )

    async def fetch_time_series(
        self,
        symbol_code: str,
        interval: str,
        *,
        outputsize: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> TwelveTimeSeries:
        params: dict[str, Any] = {
            "symbol": symbol_code,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self._config.api_key.get_secret_value(),
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        payload = await self._http.get_json("/time_series", params)
        self._raise_if_error(payload)
        try:
            return TwelveTimeSeries.model_validate(payload)
        except ValidationError as exc:
            raise self._malformed(exc) from exc

    async def fetch_quote(self, symbol_code: str) -> TwelveQuote:
        payload = await self._http.get_json(
            "/quote",
            {"symbol": symbol_code, "apikey": self._config.api_key.get_secret_value()},
        )
        self._raise_if_error(payload)
        try:
            return TwelveQuote.model_validate(payload)
        except ValidationError as exc:
            raise self._malformed(exc) from exc

    async def close(self) -> None:
        await self._http.aclose()

    @staticmethod
    def _raise_if_error(payload: Any) -> None:
        if isinstance(payload, dict) and payload.get("status") == "error":
            code = payload.get("code")
            raise handle_twelvedata_error(
                code if isinstance(code, int) else None,
                str(payload.get("message") or ""),
            )

    @staticmethod
    def _malformed(exc: ValidationError) -> MalformedDataError:
        return MalformedDataError(
            f"twelve data payload did not match the expected schema: {exc}",
            provider=_PROVIDER,
            cause=exc,
        )
