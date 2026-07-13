from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.binance.websocket import BinanceWebSocketKline
from app.domain.market_data import ConnectionState, RuntimeStatus
from app.models import Base
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.status import RuntimeStatusService


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


def kline(event_time: datetime, symbol: str = "BTCUSDT") -> BinanceWebSocketKline:
    open_time = event_time - timedelta(seconds=30)
    return BinanceWebSocketKline(
        event_time=event_time,
        symbol=symbol,
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1) - timedelta(milliseconds=1),
        open_price=Decimal("100"),
        high_price=Decimal("110"),
        low_price=Decimal("90"),
        close_price=Decimal("105"),
        volume=Decimal("12"),
        quote_volume=Decimal("1200"),
        trade_count=42,
        is_closed=True,
    )


def service(session: Session, now: datetime) -> RuntimeStatusService:
    return RuntimeStatusService(
        SqlAlchemyMarketDataRepository(session),
        now=lambda: now,
        stale_after_seconds=120,
    )


def test_initialize_symbol_persists_initializing_status(session: Session) -> None:
    runtime = service(session, datetime(2026, 7, 14, 0, 0, tzinfo=UTC))

    snapshot = runtime.initialize_symbol("BTCUSDT", "1m")
    session.commit()

    assert snapshot.status == RuntimeStatus.INITIALIZING
    assert snapshot.connection_state == ConnectionState.DISCONNECTED
    assert runtime.snapshot("BTCUSDT", "1m").status == RuntimeStatus.INITIALIZING


def test_record_kline_updates_live_status_freshness_and_last_event(session: Session) -> None:
    now = datetime(2026, 7, 14, 0, 2, tzinfo=UTC)
    event_time = now - timedelta(seconds=30)
    runtime = service(session, now)

    snapshot = runtime.record_kline(kline(event_time))
    session.commit()

    assert snapshot.status == RuntimeStatus.LIVE
    assert snapshot.connection_state == ConnectionState.CONNECTED
    assert snapshot.last_event_at == event_time
    assert snapshot.lag_seconds == 30
    assert runtime.snapshot("BTCUSDT", "1m").data_freshness_seconds == 30


def test_record_kline_marks_stale_when_freshness_exceeds_threshold(session: Session) -> None:
    now = datetime(2026, 7, 14, 0, 5, tzinfo=UTC)
    runtime = service(session, now)

    snapshot = runtime.record_kline(kline(now - timedelta(seconds=180)))
    session.commit()

    assert snapshot.status == RuntimeStatus.STALE
    assert snapshot.lag_seconds == 180


def test_connection_state_transitions(session: Session) -> None:
    runtime = service(session, datetime(2026, 7, 14, 0, 0, tzinfo=UTC))

    runtime.initialize_symbol("BTCUSDT", "1m")
    runtime.mark_connection_opened(["BTCUSDT"], "1m")
    opened = runtime.snapshot("BTCUSDT", "1m")
    runtime.mark_connection_closed(["BTCUSDT"], "1m")
    closed = runtime.snapshot("BTCUSDT", "1m")
    session.commit()

    assert opened.connection_state == ConnectionState.CONNECTED
    assert opened.status == RuntimeStatus.INITIALIZING
    assert closed.connection_state == ConnectionState.DISCONNECTED
    assert closed.status == RuntimeStatus.ERROR


def test_invalid_message_count_is_tracked_without_repository_write(session: Session) -> None:
    runtime = service(session, datetime(2026, 7, 14, 0, 0, tzinfo=UTC))

    runtime.record_invalid_message()
    runtime.record_invalid_message()

    assert runtime.invalid_message_count == 2
