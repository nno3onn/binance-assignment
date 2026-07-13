from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Coroutine
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.binance.websocket import (
    BinanceWebSocketCollector,
    BinanceWebSocketKline,
    parse_kline_message,
)


def run_async(coroutine: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coroutine)


def kline_message(symbol: str = "BTCUSDT", close_price: str = "105.00") -> str:
    return json.dumps(
        {
            "stream": f"{symbol.lower()}@kline_1m",
            "data": {
                "e": "kline",
                "E": 1_720_000_060_000,
                "s": symbol,
                "k": {
                    "t": 1_720_000_000_000,
                    "T": 1_720_000_059_999,
                    "s": symbol,
                    "i": "1m",
                    "o": "100.00",
                    "c": close_price,
                    "h": "110.00",
                    "l": "90.00",
                    "v": "12.345",
                    "q": "1234.567",
                    "n": 42,
                    "x": True,
                },
            },
        }
    )


@dataclass
class FakeWebSocket:
    messages: list[str]
    close_after_messages: bool = False
    ping_count: int = 0
    closed: bool = False

    async def recv(self) -> str:
        if self.messages:
            return self.messages.pop(0)
        raise ConnectionError("closed")

    def ping(self) -> Awaitable[None]:
        self.ping_count += 1
        return _noop()

    async def close(self) -> None:
        self.closed = True


class FakeWebSocketContext:
    def __init__(self, websocket: FakeWebSocket) -> None:
        self.websocket = websocket

    async def __aenter__(self) -> FakeWebSocket:
        return self.websocket

    async def __aexit__(self, *_args: object) -> None:
        await self.websocket.close()


class FakeConnector:
    def __init__(self, connections: list[FakeWebSocket]) -> None:
        self.connections = connections
        self.urls: list[str] = []

    def __call__(self, url: str) -> FakeWebSocketContext:
        self.urls.append(url)
        return FakeWebSocketContext(self.connections.pop(0))


async def _noop() -> None:
    return None


async def _sleep(_seconds: float) -> None:
    return None


def build_collector(
    connector: FakeConnector,
    events: list[BinanceWebSocketKline],
    symbols: list[str] | None = None,
    retry_count: int = 3,
) -> BinanceWebSocketCollector:
    return BinanceWebSocketCollector(
        base_url="wss://example.test",
        symbols=symbols or ["BTCUSDT"],
        interval="1m",
        on_kline=events.append,
        connector=connector,
        sleep=_sleep,
        keepalive_seconds=30,
        retry_count=retry_count,
    )


def test_parse_kline_message_maps_dto() -> None:
    event = parse_kline_message(
        kline_message(close_price="106.00"),
        allowed_symbols={"BTCUSDT"},
        expected_interval="1m",
    )

    assert event is not None
    assert event.symbol == "BTCUSDT"
    assert event.interval == "1m"
    assert event.close_price == Decimal("106.00")
    assert event.trade_count == 42
    assert event.is_closed is True


def test_collector_receives_normal_message() -> None:
    events: list[BinanceWebSocketKline] = []
    connector = FakeConnector([FakeWebSocket([kline_message()])])
    collector = build_collector(connector, events)

    run_async(collector.run(max_events=1))

    assert len(events) == 1
    assert events[0].symbol == "BTCUSDT"
    assert connector.urls == ["wss://example.test/stream?streams=btcusdt@kline_1m"]


def test_collector_ignores_invalid_messages() -> None:
    events: list[BinanceWebSocketKline] = []
    connector = FakeConnector(
        [FakeWebSocket(["not-json", json.dumps({"e": "trade"}), kline_message()])]
    )
    collector = build_collector(connector, events)

    run_async(collector.run(max_events=1))

    assert len(events) == 1


def test_collector_reconnects_after_connection_close() -> None:
    events: list[BinanceWebSocketKline] = []
    connector = FakeConnector(
        [
            FakeWebSocket([kline_message(close_price="101.00")]),
            FakeWebSocket([kline_message(close_price="102.00")]),
        ]
    )
    collector = build_collector(connector, events)

    run_async(collector.run(max_events=2))

    assert [event.close_price for event in events] == [Decimal("101.00"), Decimal("102.00")]
    assert len(connector.urls) == 2


def test_collector_receives_two_symbols() -> None:
    events: list[BinanceWebSocketKline] = []
    connector = FakeConnector(
        [
            FakeWebSocket(
                [
                    kline_message(symbol="BTCUSDT", close_price="101.00"),
                    kline_message(symbol="ETHUSDT", close_price="202.00"),
                ]
            )
        ]
    )
    collector = build_collector(connector, events, symbols=["BTCUSDT", "ETHUSDT"])

    run_async(collector.run(max_events=2))

    assert [event.symbol for event in events] == ["BTCUSDT", "ETHUSDT"]
    assert connector.urls == ["wss://example.test/stream?streams=btcusdt@kline_1m/ethusdt@kline_1m"]
