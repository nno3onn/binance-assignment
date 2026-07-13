from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.binance.errors import (
    BinanceInvalidResponseError,
    BinanceRateLimitError,
    BinanceTimeoutError,
)
from app.binance.rest import HttpxBinanceRestClient
from app.config import Settings


def client_for(
    handler: httpx.MockTransport,
    retry_count: int = 0,
    sleeps: list[float] | None = None,
) -> HttpxBinanceRestClient:
    http_client = httpx.Client(base_url="https://example.test", transport=handler, timeout=1)
    return HttpxBinanceRestClient(
        settings=Settings(
            binance_rest_base_url="https://example.test",
            binance_rest_timeout_seconds=1,
            binance_rest_retry_count=retry_count,
        ),
        http_client=http_client,
        sleep=lambda seconds: sleeps.append(seconds) if sleeps is not None else None,
    )


def json_response(payload: Any, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=payload)


def sample_kline_row() -> list[Any]:
    return [
        1_720_000_000_000,
        "100.00",
        "110.00",
        "90.00",
        "105.00",
        "12.345",
        1_720_000_059_999,
        "1234.567",
        42,
        "6.000",
        "600.000",
        "0",
    ]


def test_ping_success() -> None:
    transport = httpx.MockTransport(lambda _request: json_response({}))
    client = client_for(transport)

    client.ping()


def test_get_server_time() -> None:
    transport = httpx.MockTransport(
        lambda _request: json_response({"serverTime": 1_720_000_000_000})
    )
    client = client_for(transport)

    server_time = client.get_server_time()

    assert server_time.server_time_ms == 1_720_000_000_000
    assert server_time.server_time.year == 2024


def test_get_klines_maps_response_to_dto() -> None:
    seen_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.update(dict(request.url.params))
        return json_response([sample_kline_row()])

    client = client_for(httpx.MockTransport(handler))

    klines = client.get_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_time=1,
        end_time=2,
        limit=500,
    )

    assert seen_params == {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "startTime": "1",
        "endTime": "2",
        "limit": "500",
    }
    assert len(klines) == 1
    assert klines[0].open_price == Decimal("100.00")
    assert klines[0].trade_count == 42


def test_timeout_raises_after_retries() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.TimeoutException("timed out")

    sleeps: list[float] = []
    client = client_for(httpx.MockTransport(handler), retry_count=2, sleeps=sleeps)

    with pytest.raises(BinanceTimeoutError):
        client.ping()

    assert calls == 3
    assert sleeps == [0.25, 0.5]


def test_rate_limit_429_retries_then_raises() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return json_response({"code": -1003}, status_code=429)

    sleeps: list[float] = []
    client = client_for(httpx.MockTransport(handler), retry_count=1, sleeps=sleeps)

    with pytest.raises(BinanceRateLimitError):
        client.get_server_time()

    assert calls == 2
    assert sleeps == [0.25]


def test_invalid_response_raises() -> None:
    transport = httpx.MockTransport(lambda _request: json_response({"unexpected": "shape"}))
    client = client_for(transport)

    with pytest.raises(BinanceInvalidResponseError):
        client.get_klines(symbol="BTCUSDT", interval="1m")


def test_retry_succeeds_after_server_error() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return json_response({"error": "temporary"}, status_code=500)
        return json_response({})

    sleeps: list[float] = []
    client = client_for(httpx.MockTransport(handler), retry_count=2, sleeps=sleeps)

    client.ping()

    assert calls == 2
    assert sleeps == [0.25]
