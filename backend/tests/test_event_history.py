from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.binance.dto import BinanceKline, BinanceServerTime
from app.domain.market_data import ApplicationEventType, CandleInput, CandleSource, EventSeverity
from app.models import Base
from app.models.market_data import ApplicationEvent, Candle
from app.repositories.interfaces import MarketDataRepository
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.backfill import InitialBackfillService
from app.services.events import EventHistoryService
from app.services.gaps import GapDetectionService
from app.services.recovery import RestartRecoveryService


class FakeBinanceRestClient:
    def __init__(
        self,
        klines_by_symbol: dict[str, list[BinanceKline]],
        error: Exception | None = None,
    ) -> None:
        self.klines_by_symbol = klines_by_symbol
        self.error = error

    def ping(self) -> None:
        return None

    def get_server_time(self) -> BinanceServerTime:
        return BinanceServerTime(server_time_ms=0)

    def get_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[BinanceKline]:
        if self.error is not None:
            raise self.error
        return self.klines_by_symbol[symbol]


class FailingEventRepository:
    def append_application_event(self, _event: object) -> ApplicationEvent:
        raise RuntimeError("event store unavailable")

    def list_recent_application_events(self, limit: int = 100) -> list[ApplicationEvent]:
        return []


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


@pytest.fixture()
def repository(session: Session) -> SqlAlchemyMarketDataRepository:
    return SqlAlchemyMarketDataRepository(session)


def kline(open_time: datetime, close_price: str = "105") -> BinanceKline:
    close_time = open_time + timedelta(minutes=1) - timedelta(milliseconds=1)
    return BinanceKline(
        open_time_ms=int(open_time.timestamp() * 1000),
        open_time=open_time,
        open_price=Decimal("100"),
        high_price=Decimal("110"),
        low_price=Decimal("90"),
        close_price=Decimal(close_price),
        volume=Decimal("12"),
        close_time_ms=int(close_time.timestamp() * 1000),
        close_time=close_time,
        quote_volume=Decimal("1200"),
        trade_count=42,
        taker_buy_base_volume=Decimal("6"),
        taker_buy_quote_volume=Decimal("600"),
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
        close_price=Decimal("105"),
        volume=Decimal("12"),
        quote_volume=Decimal("1200"),
        trade_count=42,
        source=CandleSource.WEBSOCKET,
    )


def test_event_append(repository: SqlAlchemyMarketDataRepository, session: Session) -> None:
    service = EventHistoryService(repository)

    event = service.record(
        event_type=ApplicationEventType.WEBSOCKET_CONNECTED,
        severity=EventSeverity.INFO,
        message="connected",
        occurred_at=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
        symbol="BTCUSDT",
        interval="1m",
        metadata={"stream": "btcusdt@kline_1m"},
    )
    session.commit()

    assert event is not None
    assert event.event_type == "websocket_connected"
    assert event.severity == "INFO"
    assert event.metadata_json == {"stream": "btcusdt@kline_1m"}


def test_recent_events_are_returned_newest_first(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    service = EventHistoryService(repository)
    base = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    service.record(
        event_type=ApplicationEventType.WEBSOCKET_CONNECTED,
        severity=EventSeverity.INFO,
        message="old",
        occurred_at=base,
    )
    service.record(
        event_type=ApplicationEventType.WEBSOCKET_DISCONNECTED,
        severity=EventSeverity.WARNING,
        message="new",
        occurred_at=base + timedelta(minutes=1),
    )
    session.commit()

    assert [event.message for event in service.recent(limit=2)] == ["new", "old"]


def test_records_all_supported_severities(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    service = EventHistoryService(repository)
    for severity in [EventSeverity.INFO, EventSeverity.WARNING, EventSeverity.ERROR]:
        service.record(
            event_type=ApplicationEventType.INVALID_MESSAGE_RECEIVED,
            severity=severity,
            message=f"{severity.value} event",
        )
    session.commit()

    severities = {event.severity for event in service.recent(limit=3)}
    assert severities == {"INFO", "WARNING", "ERROR"}


def test_websocket_event_hooks(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    service = EventHistoryService(repository)

    service.websocket_connected(["BTCUSDT", "ETHUSDT"], "1m")
    service.websocket_disconnected(["BTCUSDT"], "1m")
    service.websocket_reconnecting(["BTCUSDT"], "1m", attempt=2)
    service.invalid_message_received(interval="1m")
    session.commit()

    event_types = {event.event_type for event in service.recent(limit=4)}
    assert event_types == {
        "invalid_message_received",
        "websocket_reconnecting",
        "websocket_disconnected",
        "websocket_connected",
    }


def test_initial_backfill_completed_event(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    open_time = datetime(2026, 7, 13, 23, 58, tzinfo=UTC)
    event_history = EventHistoryService(repository)

    InitialBackfillService(
        repository=repository,
        binance_rest_client=FakeBinanceRestClient({"BTCUSDT": [kline(open_time)]}),
        symbols=["BTCUSDT"],
        interval="1m",
        initial_backfill_hours=24,
        now=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
        event_history=event_history,
    ).run()
    session.commit()

    event_types = [event.event_type for event in event_history.recent(limit=2)]
    assert event_types == ["initial_backfill_completed", "initial_backfill_started"]
    completed = event_history.recent(limit=1)[0]
    assert completed.backfill_job_id is not None
    assert completed.metadata_json == {"stored_candle_count": 1}


def test_recovery_completed_and_failed_events(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    repository.bulk_upsert_candles(
        [candle("BTCUSDT", start), candle("BTCUSDT", start + timedelta(minutes=2))]
    )
    session.commit()
    event_history = EventHistoryService(repository)

    RestartRecoveryService(
        repository=repository,
        binance_rest_client=FakeBinanceRestClient(
            {"BTCUSDT": [kline(start + timedelta(minutes=1))]}
        ),
        gap_detection_service=GapDetectionService(repository),
        event_history=event_history,
    ).recover_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=2),
    )

    with pytest.raises(RuntimeError):
        RestartRecoveryService(
            repository=repository,
            binance_rest_client=FakeBinanceRestClient({"ETHUSDT": []}, error=RuntimeError("boom")),
            gap_detection_service=GapDetectionService(repository),
            event_history=event_history,
        ).recover_symbol(
            symbol="ETHUSDT",
            interval="1m",
            start=start,
            end=start,
        )
    session.commit()

    event_types = [event.event_type for event in event_history.recent(limit=5)]
    assert "recovery_completed" in event_types
    assert "recovery_failed" in event_types


def test_event_record_failure_does_not_stop_initial_backfill(session: Session) -> None:
    repository = SqlAlchemyMarketDataRepository(session)
    event_history = EventHistoryService(cast(MarketDataRepository, FailingEventRepository()))
    open_time = datetime(2026, 7, 13, 23, 58, tzinfo=UTC)

    InitialBackfillService(
        repository=repository,
        binance_rest_client=FakeBinanceRestClient({"BTCUSDT": [kline(open_time)]}),
        symbols=["BTCUSDT"],
        interval="1m",
        initial_backfill_hours=24,
        now=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
        event_history=event_history,
    ).run()
    session.commit()

    assert session.scalar(select(func.count()).select_from(Candle)) == 1
