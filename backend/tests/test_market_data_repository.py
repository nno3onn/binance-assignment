from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.market_data import (
    ApplicationEventInput,
    BackfillJobInput,
    BackfillJobStatus,
    BackfillJobType,
    CandleInput,
    CandleSource,
    EventSeverity,
    RuntimeStatus,
    RuntimeStatusInput,
)
from app.models import Base
from app.models.market_data import ApplicationEvent, BackfillJob, Candle
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository


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


def candle_input(open_time: datetime, close_price: str = "100.00") -> CandleInput:
    return CandleInput(
        symbol="BTCUSDT",
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1) - timedelta(milliseconds=1),
        open_price=Decimal("95.00"),
        high_price=Decimal("110.00"),
        low_price=Decimal("90.00"),
        close_price=Decimal(close_price),
        volume=Decimal("12.345"),
        quote_volume=Decimal("1234.567"),
        trade_count=42,
        source=CandleSource.WEBSOCKET,
    )


def test_upsert_candle_is_idempotent(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    open_time = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)

    first = repository.upsert_candle(candle_input(open_time, close_price="100.00"))
    second = repository.upsert_candle(candle_input(open_time, close_price="101.00"))
    session.commit()

    candle_count = session.scalar(select(func.count()).select_from(Candle))
    assert candle_count == 1
    assert first.id == second.id
    assert second.close_price == Decimal("101.00000000")


def test_bulk_upsert_candles(repository: SqlAlchemyMarketDataRepository, session: Session) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    candles = [
        candle_input(start, close_price="100.00"),
        candle_input(start + timedelta(minutes=1), close_price="101.00"),
        candle_input(start, close_price="102.00"),
    ]

    persisted = repository.bulk_upsert_candles(candles)
    session.commit()

    assert len(persisted) == 3
    assert session.scalar(select(func.count()).select_from(Candle)) == 2
    latest = repository.get_latest_candle("BTCUSDT", "1m")
    assert latest is not None
    assert latest.close_price == Decimal("101.00000000")


def test_get_latest_candle_and_last_open_time(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    repository.bulk_upsert_candles(
        [
            candle_input(start, close_price="100.00"),
            candle_input(start + timedelta(minutes=2), close_price="102.00"),
            candle_input(start + timedelta(minutes=1), close_price="101.00"),
        ]
    )
    session.commit()

    latest = repository.get_latest_candle("BTCUSDT", "1m")
    assert latest is not None
    assert latest.open_time == start + timedelta(minutes=2)
    assert repository.get_last_open_time("BTCUSDT", "1m") == latest.open_time


def test_list_candles_by_symbol_and_range(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    repository.bulk_upsert_candles(
        [
            candle_input(start, close_price="100.00"),
            candle_input(start + timedelta(minutes=1), close_price="101.00"),
            candle_input(start + timedelta(minutes=2), close_price="102.00"),
        ]
    )
    session.commit()

    by_symbol = repository.list_candles_by_symbol("BTCUSDT", "1m", limit=2)
    in_range = repository.list_candles_in_range(
        "BTCUSDT",
        "1m",
        start + timedelta(minutes=1),
        start + timedelta(minutes=2),
    )

    assert [candle.open_time for candle in by_symbol] == [
        start + timedelta(minutes=2),
        start + timedelta(minutes=1),
    ]
    assert [candle.close_price for candle in in_range] == [
        Decimal("101.00000000"),
        Decimal("102.00000000"),
    ]


def test_save_runtime_status_is_idempotent(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    event_time = datetime(2026, 7, 14, 0, 1, tzinfo=UTC)

    first = repository.save_runtime_status(
        RuntimeStatusInput(
            symbol="BTCUSDT",
            interval="1m",
            status=RuntimeStatus.INITIALIZING,
            last_event_at=event_time,
            lag_seconds=10,
        )
    )
    second = repository.save_runtime_status(
        RuntimeStatusInput(
            symbol="BTCUSDT",
            interval="1m",
            status=RuntimeStatus.LIVE,
            last_event_at=event_time,
            last_candle_open_time=event_time - timedelta(minutes=1),
            lag_seconds=1,
        )
    )
    session.commit()

    stored = repository.get_runtime_status("BTCUSDT", "1m")
    assert stored is not None
    assert first.id == second.id
    assert stored.status == RuntimeStatus.LIVE.value
    assert stored.lag_seconds == 1


def test_create_and_get_backfill_job(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)

    job = repository.create_backfill_job(
        BackfillJobInput(
            job_type=BackfillJobType.INITIAL,
            symbol="BTCUSDT",
            interval="1m",
            status=BackfillJobStatus.PENDING,
            range_start=start,
            range_end=start + timedelta(hours=24),
            requested_candle_count=1440,
        )
    )
    session.commit()

    stored = repository.get_backfill_job(job.id)
    assert stored is not None
    assert stored.job_type == BackfillJobType.INITIAL.value
    assert session.scalar(select(func.count()).select_from(BackfillJob)) == 1


def test_append_application_event(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    event_time = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)

    event = repository.append_application_event(
        ApplicationEventInput(
            event_time=event_time,
            severity=EventSeverity.INFO,
            event_type="repository_test",
            symbol="BTCUSDT",
            interval="1m",
            message="repository event appended",
            metadata_json={"source": "test"},
        )
    )
    session.commit()

    assert event.id is not None
    assert session.scalar(select(func.count()).select_from(ApplicationEvent)) == 1
    assert event.metadata_json == {"source": "test"}
