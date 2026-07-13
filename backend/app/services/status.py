from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.binance.websocket import BinanceWebSocketKline
from app.domain.market_data import ConnectionState, RuntimeStatus, RuntimeStatusInput
from app.repositories.interfaces import MarketDataRepository

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class RuntimeSnapshot:
    symbol: str
    interval: str
    status: RuntimeStatus
    connection_state: ConnectionState
    last_event_at: datetime | None
    last_candle_open_time: datetime | None
    lag_seconds: int
    data_freshness_seconds: int | None


class RuntimeStatusService:
    def __init__(
        self,
        repository: MarketDataRepository,
        *,
        stale_after_seconds: int = 120,
        now: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._stale_after_seconds = stale_after_seconds
        self._now = now or (lambda: datetime.now(tz=UTC))
        self._connection_states: dict[tuple[str, str], ConnectionState] = {}
        self._invalid_message_count = 0

    @property
    def invalid_message_count(self) -> int:
        return self._invalid_message_count

    def initialize_symbol(self, symbol: str, interval: str) -> RuntimeSnapshot:
        return self._save(
            symbol=symbol,
            interval=interval,
            status=RuntimeStatus.INITIALIZING,
            connection_state=ConnectionState.DISCONNECTED,
            last_event_at=None,
            last_candle_open_time=None,
            lag_seconds=0,
        )

    def mark_connection_opened(self, symbols: list[str], interval: str) -> None:
        for symbol in symbols:
            current = self.snapshot(symbol, interval)
            status = RuntimeStatus.LIVE if current.last_event_at else RuntimeStatus.INITIALIZING
            self._save(
                symbol=symbol,
                interval=interval,
                status=status,
                connection_state=ConnectionState.CONNECTED,
                last_event_at=current.last_event_at,
                last_candle_open_time=current.last_candle_open_time,
                lag_seconds=current.lag_seconds,
            )

    def mark_connection_closed(self, symbols: list[str], interval: str) -> None:
        for symbol in symbols:
            current = self.snapshot(symbol, interval)
            status = RuntimeStatus.DEGRADED if current.last_event_at else RuntimeStatus.ERROR
            self._save(
                symbol=symbol,
                interval=interval,
                status=status,
                connection_state=ConnectionState.DISCONNECTED,
                last_event_at=current.last_event_at,
                last_candle_open_time=current.last_candle_open_time,
                lag_seconds=current.lag_seconds,
            )

    def record_kline(self, kline: BinanceWebSocketKline) -> RuntimeSnapshot:
        lag_seconds = self._seconds_between(self._current_time(), kline.event_time)
        status = (
            RuntimeStatus.STALE if lag_seconds > self._stale_after_seconds else RuntimeStatus.LIVE
        )
        return self._save(
            symbol=kline.symbol,
            interval=kline.interval,
            status=status,
            connection_state=ConnectionState.CONNECTED,
            last_event_at=kline.event_time,
            last_candle_open_time=kline.open_time,
            lag_seconds=lag_seconds,
        )

    def record_invalid_message(self) -> None:
        self._invalid_message_count += 1

    def snapshot(self, symbol: str, interval: str) -> RuntimeSnapshot:
        status = self._repository.get_runtime_status(symbol, interval)
        connection_state = self._connection_states.get(
            (symbol, interval),
            ConnectionState.DISCONNECTED,
        )
        if status is None:
            return RuntimeSnapshot(
                symbol=symbol,
                interval=interval,
                status=RuntimeStatus.INITIALIZING,
                connection_state=connection_state,
                last_event_at=None,
                last_candle_open_time=None,
                lag_seconds=0,
                data_freshness_seconds=None,
            )

        last_event_at = status.last_event_at
        freshness = (
            self._seconds_between(self._current_time(), last_event_at)
            if last_event_at is not None
            else None
        )
        return RuntimeSnapshot(
            symbol=symbol,
            interval=interval,
            status=RuntimeStatus(status.status),
            connection_state=connection_state,
            last_event_at=last_event_at,
            last_candle_open_time=status.last_candle_open_time,
            lag_seconds=status.lag_seconds,
            data_freshness_seconds=freshness,
        )

    def _save(
        self,
        *,
        symbol: str,
        interval: str,
        status: RuntimeStatus,
        connection_state: ConnectionState,
        last_event_at: datetime | None,
        last_candle_open_time: datetime | None,
        lag_seconds: int,
    ) -> RuntimeSnapshot:
        normalized_symbol = symbol.upper()
        self._connection_states[(normalized_symbol, interval)] = connection_state
        model = self._repository.save_runtime_status(
            RuntimeStatusInput(
                symbol=normalized_symbol,
                interval=interval,
                status=status,
                last_event_at=last_event_at,
                last_candle_open_time=last_candle_open_time,
                lag_seconds=lag_seconds,
            )
        )
        return RuntimeSnapshot(
            symbol=normalized_symbol,
            interval=interval,
            status=RuntimeStatus(model.status),
            connection_state=connection_state,
            last_event_at=model.last_event_at,
            last_candle_open_time=model.last_candle_open_time,
            lag_seconds=model.lag_seconds,
            data_freshness_seconds=(
                self._seconds_between(self._current_time(), model.last_event_at)
                if model.last_event_at is not None
                else None
            ),
        )

    def _current_time(self) -> datetime:
        current = self._now()
        if current.tzinfo is None:
            return current.replace(tzinfo=UTC)
        return current.astimezone(UTC)

    @staticmethod
    def _seconds_between(later: datetime, earlier: datetime) -> int:
        return max(0, int((later - earlier).total_seconds()))
