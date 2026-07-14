from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Event

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.binance.dto import BinanceKline, BinanceServerTime
from app.binance.websocket import (
    BinanceWebSocketKline,
    CollectorEventHistory,
    CollectorRuntimeTracker,
)
from app.domain.market_data import CandleInput, CandleSource, RuntimeStatus
from app.main import create_app
from app.models import Base
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.runtime import MarketDataRuntime


class FakeRestClient:
    def __init__(self) -> None:
        self.kline_calls: list[str] = []
        self.closed = False

    def ping(self) -> None:
        return None

    def get_server_time(self) -> BinanceServerTime:
        return BinanceServerTime(server_time_ms=1_783_968_000_000)

    def get_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[BinanceKline]:
        self.kline_calls.append(symbol)
        start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
        return [
            rest_kline(start, "100"),
            rest_kline(start + timedelta(minutes=1), "101"),
        ]

    def close(self) -> None:
        self.closed = True


class FakeCollector:
    def __init__(
        self,
        on_kline: Callable[[BinanceWebSocketKline], None],
        runtime_tracker: CollectorRuntimeTracker,
        event_history: CollectorEventHistory,
        kline: BinanceWebSocketKline,
    ) -> None:
        self._on_kline = on_kline
        self._runtime_tracker = runtime_tracker
        self._event_history = event_history
        self._kline = kline
        self.started = Event()
        self.emitted = Event()
        self.stopped = Event()

    async def run(self) -> None:
        self.started.set()
        self._runtime_tracker.mark_connection_opened(["BTCUSDT", "ETHUSDT"], "1m")
        self._event_history.websocket_connected(["BTCUSDT", "ETHUSDT"], "1m")
        self._on_kline(self._kline)
        self.emitted.set()
        try:
            while not self.stopped.is_set():
                await asyncio.sleep(0.01)
        finally:
            self._runtime_tracker.mark_connection_closed(["BTCUSDT", "ETHUSDT"], "1m")
            self._event_history.websocket_disconnected(["BTCUSDT", "ETHUSDT"], "1m")

    async def stop(self) -> None:
        self.stopped.set()


def rest_kline(open_time: datetime, close_price: str) -> BinanceKline:
    return BinanceKline(
        open_time_ms=int(open_time.timestamp() * 1000),
        open_time=open_time,
        open_price=Decimal("100"),
        high_price=Decimal("110"),
        low_price=Decimal("90"),
        close_price=Decimal(close_price),
        volume=Decimal("12"),
        close_time_ms=int((open_time + timedelta(minutes=1)).timestamp() * 1000) - 1,
        close_time=open_time + timedelta(minutes=1) - timedelta(milliseconds=1),
        quote_volume=Decimal("1200"),
        trade_count=42,
        taker_buy_base_volume=Decimal("6"),
        taker_buy_quote_volume=Decimal("600"),
    )


def ws_kline(symbol: str = "BTCUSDT") -> BinanceWebSocketKline:
    open_time = datetime.now(tz=UTC).replace(second=0, microsecond=0)
    return BinanceWebSocketKline(
        event_time=open_time + timedelta(seconds=1),
        symbol=symbol,
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1) - timedelta(milliseconds=1),
        open_price=Decimal("101"),
        high_price=Decimal("112"),
        low_price=Decimal("99"),
        close_price=Decimal("111"),
        volume=Decimal("15"),
        quote_volume=Decimal("1500"),
        trade_count=50,
        is_closed=True,
    )


def candle(symbol: str, open_time: datetime) -> CandleInput:
    return CandleInput(
        symbol=symbol,
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1) - timedelta(milliseconds=1),
        open_price=Decimal("100"),
        high_price=Decimal("110"),
        low_price=Decimal("90"),
        close_price=Decimal("100"),
        volume=Decimal("12"),
        quote_volume=Decimal("1200"),
        trade_count=42,
        source=CandleSource.REST_BACKFILL,
    )


def build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_app_startup_runs_initial_backfill_starts_collector_and_shutdowns() -> None:
    factory = build_session_factory()
    rest_client = FakeRestClient()
    fake_collector: FakeCollector | None = None

    def runtime_factory() -> MarketDataRuntime:
        def collector_factory(
            on_kline: Callable[[BinanceWebSocketKline], None],
            runtime_tracker: CollectorRuntimeTracker,
            event_history: CollectorEventHistory,
        ) -> FakeCollector:
            nonlocal fake_collector
            fake_collector = FakeCollector(
                on_kline,
                runtime_tracker,
                event_history,
                ws_kline("BTCUSDT"),
            )
            return fake_collector

        from app.config import Settings

        return MarketDataRuntime(
            settings=Settings(database_url="sqlite://"),
            session_factory=factory,
            rest_client_factory=lambda: rest_client,
            collector_factory=collector_factory,
        )

    app = create_app(enable_runtime=True, runtime_factory=runtime_factory)
    with TestClient(app):
        assert fake_collector is not None
        assert fake_collector.emitted.wait(timeout=1)

        with factory() as session:
            repository = SqlAlchemyMarketDataRepository(session)
            btc_candles = repository.list_candles_by_symbol("BTCUSDT", "1m", limit=10)
            eth_candles = repository.list_candles_by_symbol("ETHUSDT", "1m", limit=10)
            btc_status = repository.get_runtime_status("BTCUSDT", "1m")
            events = repository.list_recent_application_events(limit=10)
            jobs = repository.list_recent_backfill_jobs(limit=10)

        assert rest_client.kline_calls == ["BTCUSDT", "ETHUSDT"]
        assert len(btc_candles) == 3
        assert len(eth_candles) == 2
        assert any(candle.source == CandleSource.WEBSOCKET.value for candle in btc_candles)
        assert btc_status is not None
        assert btc_status.status == RuntimeStatus.LIVE.value
        assert len(jobs) == 2
        assert events

    assert fake_collector is not None
    assert fake_collector.stopped.is_set()


def test_startup_skips_initial_backfill_when_candles_exist() -> None:
    factory = build_session_factory()
    with factory() as session:
        repository = SqlAlchemyMarketDataRepository(session)
        repository.upsert_candle(candle("BTCUSDT", datetime(2026, 7, 14, 0, 0, tzinfo=UTC)))
        repository.upsert_candle(candle("ETHUSDT", datetime(2026, 7, 14, 0, 0, tzinfo=UTC)))
        session.commit()

    rest_client = FakeRestClient()

    def runtime_factory() -> MarketDataRuntime:
        def collector_factory(
            on_kline: Callable[[BinanceWebSocketKline], None],
            runtime_tracker: CollectorRuntimeTracker,
            event_history: CollectorEventHistory,
        ) -> FakeCollector:
            return FakeCollector(on_kline, runtime_tracker, event_history, ws_kline("BTCUSDT"))

        from app.config import Settings

        return MarketDataRuntime(
            settings=Settings(database_url="sqlite://"),
            session_factory=factory,
            rest_client_factory=lambda: rest_client,
            collector_factory=collector_factory,
        )

    app = create_app(enable_runtime=True, runtime_factory=runtime_factory)
    with TestClient(app):
        pass

    assert rest_client.kline_calls == []


def test_startup_runs_restart_recovery_for_existing_gap() -> None:
    factory = build_session_factory()
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    with factory() as session:
        repository = SqlAlchemyMarketDataRepository(session)
        repository.upsert_candle(candle("BTCUSDT", start))
        repository.upsert_candle(candle("BTCUSDT", start + timedelta(minutes=2)))
        repository.upsert_candle(candle("ETHUSDT", start))
        session.commit()

    rest_client = FakeRestClient()

    def runtime_factory() -> MarketDataRuntime:
        def collector_factory(
            on_kline: Callable[[BinanceWebSocketKline], None],
            runtime_tracker: CollectorRuntimeTracker,
            event_history: CollectorEventHistory,
        ) -> FakeCollector:
            return FakeCollector(on_kline, runtime_tracker, event_history, ws_kline("BTCUSDT"))

        from app.config import Settings

        return MarketDataRuntime(
            settings=Settings(database_url="sqlite://"),
            session_factory=factory,
            rest_client_factory=lambda: rest_client,
            collector_factory=collector_factory,
        )

    app = create_app(enable_runtime=True, runtime_factory=runtime_factory)
    with TestClient(app):
        with factory() as session:
            repository = SqlAlchemyMarketDataRepository(session)
            btc_candles = repository.list_candles_by_symbol("BTCUSDT", "1m", limit=10)
            eth_candles = repository.list_candles_by_symbol("ETHUSDT", "1m", limit=10)
            btc_status = repository.get_runtime_status("BTCUSDT", "1m")
            events = repository.list_recent_application_events(limit=20)

    assert rest_client.kline_calls == ["BTCUSDT"]
    assert {item.open_time for item in btc_candles}.issuperset(
        {start, start + timedelta(minutes=1), start + timedelta(minutes=2)}
    )
    recovered_open_time = start + timedelta(minutes=1)
    assert len([item for item in btc_candles if item.open_time == recovered_open_time]) == 1
    assert len(eth_candles) == 1
    assert btc_status is not None
    assert btc_status.status == RuntimeStatus.LIVE.value
    assert any(event.event_type == "recovery_completed" for event in events)
