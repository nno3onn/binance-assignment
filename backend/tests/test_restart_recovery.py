from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.binance.dto import BinanceKline, BinanceServerTime
from app.domain.market_data import CandleInput, CandleSource, RuntimeStatus, RuntimeStatusInput
from app.models import Base
from app.models.market_data import Candle
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.gaps import GapDetectionService
from app.services.recovery import RestartRecoveryService


class FakeBinanceRestClient:
    def __init__(self, klines_by_symbol: dict[str, list[BinanceKline]]) -> None:
        self.klines_by_symbol = klines_by_symbol
        self.kline_calls: list[dict[str, int | str | None]] = []

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
        self.kline_calls.append(
            {
                "symbol": symbol,
                "interval": interval,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            }
        )
        return self.klines_by_symbol[symbol]


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


def seed_candles(
    repository: SqlAlchemyMarketDataRepository,
    symbol: str,
    open_times: list[datetime],
) -> None:
    repository.bulk_upsert_candles([candle(symbol, open_time) for open_time in open_times])


def recovery_service(
    repository: SqlAlchemyMarketDataRepository,
    client: FakeBinanceRestClient,
) -> RestartRecoveryService:
    return RestartRecoveryService(
        repository=repository,
        binance_rest_client=client,
        gap_detection_service=GapDetectionService(repository),
    )


def test_recovery_no_gap_does_not_call_rest(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    seed_candles(repository, "BTCUSDT", [start, start + timedelta(minutes=1)])
    session.commit()
    client = FakeBinanceRestClient({"BTCUSDT": []})

    result = recovery_service(repository, client).recover_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=1),
    )

    assert result.recovered_gap_count == 0
    assert result.stored_candle_count == 0
    assert client.kline_calls == []


def test_recovery_repairs_single_gap(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    missing = start + timedelta(minutes=1)
    seed_candles(repository, "BTCUSDT", [start, start + timedelta(minutes=2)])
    session.commit()
    client = FakeBinanceRestClient({"BTCUSDT": [kline(missing, close_price="106")]})

    result = recovery_service(repository, client).recover_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=2),
    )
    session.commit()

    candles = repository.list_candles_in_range("BTCUSDT", "1m", start, start + timedelta(minutes=2))
    assert result.recovered_gap_count == 1
    assert result.stored_candle_count == 1
    assert [candle_row.open_time for candle_row in candles] == [
        start,
        missing,
        start + timedelta(minutes=2),
    ]
    recovered = next(candle_row for candle_row in candles if candle_row.open_time == missing)
    assert recovered.source == "rest_backfill"


def test_recovery_repairs_multiple_gaps(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    missing_one = start + timedelta(minutes=1)
    missing_two = start + timedelta(minutes=3)
    seed_candles(
        repository, "BTCUSDT", [start, start + timedelta(minutes=2), start + timedelta(minutes=4)]
    )
    session.commit()
    client = FakeBinanceRestClient({"BTCUSDT": [kline(missing_one), kline(missing_two)]})

    result = recovery_service(repository, client).recover_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=4),
    )
    session.commit()

    assert result.recovered_gap_count == 2
    assert result.stored_candle_count == 2
    assert session.scalar(select(func.count()).select_from(Candle)) == 5
    assert len(client.kline_calls) == 2


def test_recovery_is_idempotent_when_reexecuted(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    missing = start + timedelta(minutes=1)
    seed_candles(repository, "BTCUSDT", [start, start + timedelta(minutes=2)])
    session.commit()
    client = FakeBinanceRestClient({"BTCUSDT": [kline(missing)]})
    service = recovery_service(repository, client)

    first = service.recover_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=2),
    )
    session.commit()
    second = service.recover_symbol(
        symbol="BTCUSDT",
        interval="1m",
        start=start,
        end=start + timedelta(minutes=2),
    )
    session.commit()

    assert first.stored_candle_count == 1
    assert second.stored_candle_count == 0
    assert len(client.kline_calls) == 1
    assert session.scalar(select(func.count()).select_from(Candle)) == 3


def test_recovery_repairs_two_symbols_independently(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    seed_candles(repository, "BTCUSDT", [start, start + timedelta(minutes=2)])
    seed_candles(repository, "ETHUSDT", [start])
    repository.save_runtime_status(
        RuntimeStatusInput(
            symbol="ETHUSDT",
            interval="1m",
            status=RuntimeStatus.LIVE,
            last_candle_open_time=start + timedelta(minutes=1),
            lag_seconds=0,
        )
    )
    session.commit()
    client = FakeBinanceRestClient(
        {
            "BTCUSDT": [kline(start + timedelta(minutes=1))],
            "ETHUSDT": [kline(start + timedelta(minutes=1))],
        }
    )

    results = recovery_service(repository, client).recover_symbols(
        ["BTCUSDT", "ETHUSDT"],
        "1m",
        start=start,
        end=start + timedelta(minutes=2),
    )
    session.commit()

    stored_by_symbol = {result.symbol: result.stored_candle_count for result in results}
    assert stored_by_symbol == {"BTCUSDT": 1, "ETHUSDT": 1}
    assert session.scalar(select(func.count()).select_from(Candle)) == 5
