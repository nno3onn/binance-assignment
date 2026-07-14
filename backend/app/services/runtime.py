from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.binance.interfaces import BinanceRestClient
from app.binance.rest import HttpxBinanceRestClient
from app.binance.websocket import (
    BinanceWebSocketCollector,
    BinanceWebSocketKline,
    CollectorEventHistory,
    CollectorRuntimeTracker,
)
from app.config import Settings
from app.domain.market_data import CandleInput, CandleSource, RuntimeStatus, RuntimeStatusInput
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.backfill import InitialBackfillService
from app.services.events import EventHistoryService
from app.services.gaps import GapDetectionService
from app.services.recovery import RestartRecoveryService
from app.services.status import RuntimeStatusService

SessionFactory = Callable[[], Session]
RestClientFactory = Callable[[], BinanceRestClient]


class RuntimeCollector(Protocol):
    def run(self) -> Coroutine[Any, Any, None]:
        pass

    def stop(self) -> Coroutine[Any, Any, None]:
        pass


CollectorFactory = Callable[
    [Callable[[BinanceWebSocketKline], None], CollectorRuntimeTracker, CollectorEventHistory],
    RuntimeCollector,
]


def websocket_kline_to_candle(kline: BinanceWebSocketKline) -> CandleInput:
    return CandleInput(
        symbol=kline.symbol,
        interval=kline.interval,
        open_time=kline.open_time,
        close_time=kline.close_time,
        open_price=kline.open_price,
        high_price=kline.high_price,
        low_price=kline.low_price,
        close_price=kline.close_price,
        volume=kline.volume,
        quote_volume=kline.quote_volume,
        trade_count=kline.trade_count,
        source=CandleSource.WEBSOCKET,
    )


@dataclass
class MarketDataRuntime:
    settings: Settings
    session_factory: SessionFactory
    rest_client_factory: RestClientFactory | None = None
    collector_factory: CollectorFactory | None = None

    def __post_init__(self) -> None:
        self._collector: RuntimeCollector | None = None
        self._collector_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await asyncio.to_thread(self._run_startup_backfill_and_recovery)
        self._collector = self._build_collector()
        self._collector_task = asyncio.create_task(self._collector.run())

    async def stop(self) -> None:
        if self._collector is not None:
            await self._collector.stop()
        if self._collector_task is not None:
            self._collector_task.cancel()
            try:
                await self._collector_task
            except asyncio.CancelledError:
                pass
        self._collector = None
        self._collector_task = None

    @property
    def collector_task(self) -> asyncio.Task[None] | None:
        return self._collector_task

    def handle_kline(self, kline: BinanceWebSocketKline) -> None:
        with self.session_factory() as session:
            repository = SqlAlchemyMarketDataRepository(session)
            repository.upsert_candle(websocket_kline_to_candle(kline))
            RuntimeStatusService(repository).record_kline(kline)
            session.commit()

    def _run_startup_backfill_and_recovery(self) -> None:
        rest_client = self._build_rest_client()
        try:
            with self.session_factory() as session:
                repository = SqlAlchemyMarketDataRepository(session)
                event_history = EventHistoryService(repository)
                runtime_status = RuntimeStatusService(repository)
                for symbol in self.settings.symbol_list:
                    runtime_status.initialize_symbol(symbol, self.settings.candle_interval)
                    if repository.get_latest_candle(symbol, self.settings.candle_interval) is None:
                        repository.save_runtime_status(
                            RuntimeStatusInput(
                                symbol=symbol,
                                interval=self.settings.candle_interval,
                                status=RuntimeStatus.BACKFILLING,
                                lag_seconds=0,
                            )
                        )
                session.commit()

                InitialBackfillService(
                    repository=repository,
                    binance_rest_client=rest_client,
                    symbols=self.settings.symbol_list,
                    interval=self.settings.candle_interval,
                    initial_backfill_hours=self.settings.initial_backfill_hours,
                    event_history=event_history,
                ).run()

                recovery_started_at = datetime.now(tz=UTC)
                for symbol in self.settings.symbol_list:
                    latest = repository.get_latest_candle(symbol, self.settings.candle_interval)
                    if latest is not None:
                        repository.save_runtime_status(
                            RuntimeStatusInput(
                                symbol=symbol,
                                interval=self.settings.candle_interval,
                                status=RuntimeStatus.BACKFILLING,
                                last_event_at=recovery_started_at,
                                last_candle_open_time=latest.open_time,
                                lag_seconds=0,
                            )
                        )

                RestartRecoveryService(
                    repository=repository,
                    binance_rest_client=rest_client,
                    gap_detection_service=GapDetectionService(repository),
                    event_history=event_history,
                ).recover_symbols(
                    self.settings.symbol_list,
                    self.settings.candle_interval,
                )

                now = datetime.now(tz=UTC)
                for symbol in self.settings.symbol_list:
                    latest = repository.get_latest_candle(symbol, self.settings.candle_interval)
                    if latest is not None:
                        repository.save_runtime_status(
                            RuntimeStatusInput(
                                symbol=symbol,
                                interval=self.settings.candle_interval,
                                status=RuntimeStatus.LIVE,
                                last_event_at=now,
                                last_candle_open_time=latest.open_time,
                                lag_seconds=0,
                            )
                        )
                session.commit()
        finally:
            close = getattr(rest_client, "close", None)
            if callable(close):
                close()

    def _build_rest_client(self) -> BinanceRestClient:
        if self.rest_client_factory is not None:
            return self.rest_client_factory()
        return HttpxBinanceRestClient(self.settings)

    def _build_collector(self) -> RuntimeCollector:
        runtime_tracker = RuntimeTrackerSessionAdapter(self.session_factory)
        event_history = EventHistorySessionAdapter(self.session_factory)
        if self.collector_factory is not None:
            return self.collector_factory(self.handle_kline, runtime_tracker, event_history)
        return BinanceWebSocketCollector(
            base_url=self.settings.binance_ws_base_url,
            symbols=self.settings.symbol_list,
            interval=self.settings.candle_interval,
            on_kline=self.handle_kline,
            runtime_tracker=runtime_tracker,
            event_history=event_history,
            keepalive_seconds=self.settings.binance_ws_keepalive_seconds,
            retry_count=self.settings.binance_ws_retry_count,
        )


class RuntimeTrackerSessionAdapter:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def mark_connection_opened(self, symbols: list[str], interval: str) -> None:
        with self._session_factory() as session:
            service = RuntimeStatusService(SqlAlchemyMarketDataRepository(session))
            service.mark_connection_opened(symbols, interval)
            session.commit()

    def mark_connection_closed(self, symbols: list[str], interval: str) -> None:
        with self._session_factory() as session:
            service = RuntimeStatusService(SqlAlchemyMarketDataRepository(session))
            service.mark_connection_closed(symbols, interval)
            session.commit()

    def record_kline(self, _kline: BinanceWebSocketKline) -> None:
        return None

    def record_invalid_message(self) -> None:
        return None


class EventHistorySessionAdapter:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def websocket_connected(self, symbols: list[str], interval: str) -> None:
        with self._session_factory() as session:
            EventHistoryService(SqlAlchemyMarketDataRepository(session)).websocket_connected(
                symbols, interval
            )
            session.commit()

    def websocket_disconnected(self, symbols: list[str], interval: str) -> None:
        with self._session_factory() as session:
            EventHistoryService(SqlAlchemyMarketDataRepository(session)).websocket_disconnected(
                symbols, interval
            )
            session.commit()

    def websocket_reconnecting(self, symbols: list[str], interval: str, attempt: int) -> None:
        with self._session_factory() as session:
            EventHistoryService(SqlAlchemyMarketDataRepository(session)).websocket_reconnecting(
                symbols, interval, attempt
            )
            session.commit()

    def invalid_message_received(
        self, symbol: str | None = None, interval: str | None = None
    ) -> None:
        with self._session_factory() as session:
            EventHistoryService(SqlAlchemyMarketDataRepository(session)).invalid_message_received(
                symbol=symbol,
                interval=interval,
            )
            session.commit()
