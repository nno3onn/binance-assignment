from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from app.binance.dto import BinanceKline, BinanceServerTime
from app.binance.errors import (
    BinanceHttpClientError,
    BinanceHttpServerError,
    BinanceInvalidResponseError,
    BinanceNetworkError,
    BinanceRateLimitError,
    BinanceTimeoutError,
)
from app.config import Settings


class HttpxBinanceRestClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._sleep = sleep
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=settings.binance_rest_base_url,
            timeout=settings.binance_rest_timeout_seconds,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def ping(self) -> None:
        payload = self._request_json("GET", "/api/v3/ping")
        if payload != {}:
            raise BinanceInvalidResponseError("Ping response must be an empty object")

    def get_server_time(self) -> BinanceServerTime:
        payload = self._request_json("GET", "/api/v3/time")
        if not isinstance(payload, dict) or "serverTime" not in payload:
            raise BinanceInvalidResponseError("Server time response missing serverTime")
        try:
            return BinanceServerTime(server_time_ms=int(payload["serverTime"]))
        except (TypeError, ValueError) as exc:
            raise BinanceInvalidResponseError("serverTime must be an integer timestamp") from exc

    def get_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[BinanceKline]:
        params: dict[str, int | str] = {
            "symbol": symbol,
            "interval": interval,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if limit is not None:
            params["limit"] = limit

        payload = self._request_json("GET", "/api/v3/klines", params=params)
        if not isinstance(payload, list):
            raise BinanceInvalidResponseError("Klines response must be a list")
        return [BinanceKline.from_api_row(row) for row in payload]

    def _request_json(
        self,
        method: str,
        path: str,
        params: dict[str, int | str] | None = None,
    ) -> Any:
        last_error: Exception | None = None
        max_attempts = self._settings.binance_rest_retry_count + 1

        for attempt in range(max_attempts):
            try:
                response = self._client.request(method, path, params=params)
                self._raise_for_status(response)
                return response.json()
            except httpx.TimeoutException:
                last_error = BinanceTimeoutError("Binance REST request timed out")
            except httpx.NetworkError:
                last_error = BinanceNetworkError("Binance REST network error")
            except httpx.DecodingError as exc:
                raise BinanceInvalidResponseError(
                    "Binance REST response is not valid JSON"
                ) from exc
            except BinanceRateLimitError as exc:
                last_error = exc
            except BinanceHttpServerError as exc:
                last_error = exc

            if attempt < max_attempts - 1:
                self._sleep(self._backoff_seconds(attempt))

        if last_error is None:
            raise BinanceNetworkError("Binance REST request failed")
        raise last_error

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status_code = response.status_code
        if status_code < 400:
            return
        if status_code == 429:
            raise BinanceRateLimitError("Binance REST rate limit exceeded")
        if 400 <= status_code < 500:
            raise BinanceHttpClientError(f"Binance REST client error: {status_code}")
        if 500 <= status_code:
            raise BinanceHttpServerError(f"Binance REST server error: {status_code}")

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        return float(min(0.25 * (2**attempt), 2.0))

    def __enter__(self) -> HttpxBinanceRestClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
