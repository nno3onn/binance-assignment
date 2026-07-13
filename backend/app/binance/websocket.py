from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from websockets.asyncio.client import connect


@dataclass(frozen=True)
class BinanceWebSocketKline:
    event_time: datetime
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    trade_count: int
    is_closed: bool


class WebSocketConnection(Protocol):
    async def recv(self) -> str | bytes:
        pass

    def ping(self) -> Awaitable[Any] | Any:
        pass

    async def close(self) -> None:
        pass


class WebSocketConnector(Protocol):
    def __call__(self, url: str) -> Any:
        pass


class CollectorRuntimeTracker(Protocol):
    def mark_connection_opened(self, symbols: list[str], interval: str) -> Awaitable[None] | None:
        pass

    def mark_connection_closed(self, symbols: list[str], interval: str) -> Awaitable[None] | None:
        pass

    def record_kline(self, kline: BinanceWebSocketKline) -> Awaitable[None] | None:
        pass

    def record_invalid_message(self) -> Awaitable[None] | None:
        pass


class CollectorEventHistory(Protocol):
    def websocket_connected(self, symbols: list[str], interval: str) -> None:
        pass

    def websocket_disconnected(self, symbols: list[str], interval: str) -> None:
        pass

    def websocket_reconnecting(self, symbols: list[str], interval: str, attempt: int) -> None:
        pass

    def invalid_message_received(
        self, symbol: str | None = None, interval: str | None = None
    ) -> None:
        pass


KlineHandler = Callable[[BinanceWebSocketKline], Awaitable[None] | None]
Sleep = Callable[[float], Awaitable[None]]


class BinanceWebSocketCollector:
    def __init__(
        self,
        *,
        base_url: str,
        symbols: list[str],
        interval: str,
        on_kline: KlineHandler,
        connector: WebSocketConnector | None = None,
        runtime_tracker: CollectorRuntimeTracker | None = None,
        event_history: CollectorEventHistory | None = None,
        sleep: Sleep = asyncio.sleep,
        keepalive_seconds: float = 30.0,
        retry_count: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._symbols = [symbol.upper() for symbol in symbols]
        self._interval = interval
        self._on_kline = on_kline
        self._connector = connector or self._connect
        self._runtime_tracker = runtime_tracker
        self._event_history = event_history
        self._sleep = sleep
        self._keepalive_seconds = keepalive_seconds
        self._retry_count = retry_count
        self._stopped = asyncio.Event()
        self._active_connection: WebSocketConnection | None = None

    async def run(self, max_events: int | None = None) -> None:
        emitted_events = 0
        reconnect_attempt = 0

        while not self._stopped.is_set():
            try:
                emitted_events += await self._consume_once(max_events, emitted_events)
                reconnect_attempt = 0
                if max_events is not None and emitted_events >= max_events:
                    return
            except (ConnectionError, TimeoutError, OSError):
                if self._stopped.is_set():
                    return
                if reconnect_attempt >= self._retry_count:
                    raise
                if self._event_history is not None:
                    self._event_history.websocket_reconnecting(
                        self._symbols,
                        self._interval,
                        reconnect_attempt + 1,
                    )
                await self._sleep(self._backoff_seconds(reconnect_attempt))
                reconnect_attempt += 1

    async def stop(self) -> None:
        self._stopped.set()
        if self._active_connection is not None:
            await self._active_connection.close()

    def stream_url(self) -> str:
        streams = "/".join(f"{symbol.lower()}@kline_{self._interval}" for symbol in self._symbols)
        return f"{self._base_url}/stream?streams={streams}"

    async def _consume_once(self, max_events: int | None, emitted_events: int) -> int:
        emitted_this_connection = 0
        async with self._connector(self.stream_url()) as websocket:
            self._active_connection = websocket
            await self._call_runtime_tracker(
                "mark_connection_opened", self._symbols, self._interval
            )
            if self._event_history is not None:
                self._event_history.websocket_connected(self._symbols, self._interval)
            keepalive_task = asyncio.create_task(self._keepalive(websocket))
            try:
                while not self._stopped.is_set():
                    try:
                        raw_message = await websocket.recv()
                    except (ConnectionError, TimeoutError, OSError):
                        if emitted_this_connection > 0:
                            return emitted_this_connection
                        raise
                    kline = parse_kline_message(
                        raw_message,
                        allowed_symbols=set(self._symbols),
                        expected_interval=self._interval,
                    )
                    if kline is None:
                        await self._call_runtime_tracker("record_invalid_message")
                        if self._event_history is not None:
                            self._event_history.invalid_message_received(interval=self._interval)
                        continue

                    await self._call_runtime_tracker("record_kline", kline)
                    result = self._on_kline(kline)
                    if inspect.isawaitable(result):
                        await result
                    emitted_this_connection += 1

                    if (
                        max_events is not None
                        and emitted_events + emitted_this_connection >= max_events
                    ):
                        return emitted_this_connection
            finally:
                keepalive_task.cancel()
                await self._call_runtime_tracker(
                    "mark_connection_closed", self._symbols, self._interval
                )
                if self._event_history is not None:
                    self._event_history.websocket_disconnected(self._symbols, self._interval)
                self._active_connection = None
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    pass

        return emitted_this_connection

    async def _keepalive(self, websocket: WebSocketConnection) -> None:
        while not self._stopped.is_set():
            await self._sleep(self._keepalive_seconds)
            pong = websocket.ping()
            if inspect.isawaitable(pong):
                await pong

    @staticmethod
    def _connect(url: str) -> Any:
        return connect(url, ping_interval=None)

    async def _call_runtime_tracker(self, method_name: str, *args: object) -> None:
        if self._runtime_tracker is None:
            return
        method = getattr(self._runtime_tracker, method_name)
        result = method(*args)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        return float(min(0.25 * (2**attempt), 2.0))


def parse_kline_message(
    raw_message: str | bytes,
    *,
    allowed_symbols: set[str],
    expected_interval: str,
) -> BinanceWebSocketKline | None:
    try:
        payload = json.loads(
            raw_message.decode("utf-8") if isinstance(raw_message, bytes) else raw_message
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    data = payload.get("data", payload)
    if not isinstance(data, dict) or data.get("e") != "kline":
        return None

    kline = data.get("k")
    if not isinstance(kline, dict):
        return None

    symbol = str(data.get("s") or kline.get("s") or "").upper()
    interval = str(kline.get("i") or "")
    if symbol not in allowed_symbols or interval != expected_interval:
        return None

    try:
        event_time_ms = int(data["E"])
        open_time_ms = int(kline["t"])
        close_time_ms = int(kline["T"])
        return BinanceWebSocketKline(
            event_time=_from_milliseconds(event_time_ms),
            symbol=symbol,
            interval=interval,
            open_time=_from_milliseconds(open_time_ms),
            close_time=_from_milliseconds(close_time_ms),
            open_price=Decimal(str(kline["o"])),
            high_price=Decimal(str(kline["h"])),
            low_price=Decimal(str(kline["l"])),
            close_price=Decimal(str(kline["c"])),
            volume=Decimal(str(kline["v"])),
            quote_volume=Decimal(str(kline["q"])),
            trade_count=int(kline["n"]),
            is_closed=bool(kline["x"]),
        )
    except (ArithmeticError, KeyError, TypeError, ValueError):
        return None


def _from_milliseconds(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)
