from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.market_data import (
    CandleInput,
    CandleSource,
    RuntimeStatus,
    RuntimeStatusInput,
)
from app.models import Base
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.gaps import GapDetectionService


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


def seed_candles(
    repository: SqlAlchemyMarketDataRepository,
    symbol: str,
    open_times: list[datetime],
) -> None:
    repository.bulk_upsert_candles([candle(symbol, open_time) for open_time in open_times])


def test_detects_no_gap(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    seed_candles(repository, "BTCUSDT", [start, start + timedelta(minutes=1)])
    session.commit()

    result = GapDetectionService(repository).detect_for_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=1),
    )

    assert result.expected_candle_count == 2
    assert result.observed_candle_count == 2
    assert result.missing_candle_count == 0
    assert result.gaps == []


def test_detects_single_gap(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    seed_candles(repository, "BTCUSDT", [start, start + timedelta(minutes=3)])
    session.commit()

    result = GapDetectionService(repository).detect_for_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=3),
    )

    assert result.missing_candle_count == 2
    assert len(result.gaps) == 1
    assert result.gaps[0].start_time == start + timedelta(minutes=1)
    assert result.gaps[0].end_time == start + timedelta(minutes=2)
    assert result.gaps[0].missing_candle_count == 2


def test_detects_multiple_gaps(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    seed_candles(
        repository,
        "BTCUSDT",
        [
            start,
            start + timedelta(minutes=2),
            start + timedelta(minutes=5),
        ],
    )
    session.commit()

    result = GapDetectionService(repository).detect_for_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=5),
    )

    assert result.missing_candle_count == 3
    assert [(gap.start_time, gap.end_time, gap.missing_candle_count) for gap in result.gaps] == [
        (start + timedelta(minutes=1), start + timedelta(minutes=1), 1),
        (start + timedelta(minutes=3), start + timedelta(minutes=4), 2),
    ]


def test_detects_empty_database_as_full_range_gap(
    repository: SqlAlchemyMarketDataRepository,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)

    result = GapDetectionService(repository).detect_for_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=2),
    )

    assert result.expected_candle_count == 3
    assert result.observed_candle_count == 0
    assert result.missing_candle_count == 3
    assert len(result.gaps) == 1
    assert result.gaps[0].start_time == start
    assert result.gaps[0].end_time == start + timedelta(minutes=2)


def test_detects_two_symbols_independently(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    seed_candles(repository, "BTCUSDT", [start, start + timedelta(minutes=1)])
    seed_candles(repository, "ETHUSDT", [start])
    session.commit()

    results = GapDetectionService(repository).detect_for_symbols(
        ["BTCUSDT", "ETHUSDT"],
        "1m",
        start=start,
        end=start + timedelta(minutes=1),
    )

    missing_by_symbol = {result.symbol: result.missing_candle_count for result in results}
    assert missing_by_symbol == {"BTCUSDT": 0, "ETHUSDT": 1}
    eth_gap = next(result.gaps[0] for result in results if result.symbol == "ETHUSDT")
    assert eth_gap.start_time == start + timedelta(minutes=1)


def test_uses_runtime_status_as_default_scan_end(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    seed_candles(repository, "BTCUSDT", [start])
    repository.save_runtime_status(
        RuntimeStatusInput(
            symbol="BTCUSDT",
            interval="1m",
            status=RuntimeStatus.LIVE,
            last_candle_open_time=start + timedelta(minutes=2),
            lag_seconds=0,
        )
    )
    session.commit()

    result = GapDetectionService(repository).detect_for_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
    )

    assert result.scan_end == start + timedelta(minutes=2)
    assert result.missing_candle_count == 2
