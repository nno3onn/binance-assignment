from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.binance.dto import BinanceKline, BinanceServerTime
from app.models import Base
from app.models.market_data import BackfillJob, Candle
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.backfill import InitialBackfillService


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


def make_kline(open_time: datetime, close_price: str = "100.00") -> BinanceKline:
    close_time = open_time + timedelta(minutes=1) - timedelta(milliseconds=1)
    return BinanceKline(
        open_time_ms=int(open_time.timestamp() * 1000),
        open_time=open_time,
        open_price=Decimal("95.00"),
        high_price=Decimal("110.00"),
        low_price=Decimal("90.00"),
        close_price=Decimal(close_price),
        volume=Decimal("12.345"),
        close_time_ms=int(close_time.timestamp() * 1000),
        close_time=close_time,
        quote_volume=Decimal("1234.567"),
        trade_count=42,
        taker_buy_base_volume=Decimal("6.000"),
        taker_buy_quote_volume=Decimal("600.000"),
    )


def build_service(
    session: Session,
    client: FakeBinanceRestClient,
    symbols: list[str] | None = None,
) -> InitialBackfillService:
    return InitialBackfillService(
        repository=SqlAlchemyMarketDataRepository(session),
        binance_rest_client=client,
        symbols=symbols or ["BTCUSDT"],
        interval="1m",
        initial_backfill_hours=24,
        now=datetime(2026, 7, 14, 0, 0, tzinfo=UTC),
    )


def test_initial_backfill_on_empty_database(session: Session) -> None:
    open_time = datetime(2026, 7, 13, 23, 58, tzinfo=UTC)
    client = FakeBinanceRestClient({"BTCUSDT": [make_kline(open_time, close_price="101.00")]})

    result = build_service(session, client).run()
    session.commit()

    candles = session.scalars(select(Candle)).all()
    assert len(result) == 1
    assert result[0].skipped is False
    assert result[0].stored_candle_count == 1
    assert len(candles) == 1
    assert candles[0].source == "rest_backfill"
    assert candles[0].close_price == Decimal("101.00000000")
    assert client.kline_calls[0]["start_time"] == 1_783_900_800_000
    assert client.kline_calls[0]["end_time"] == 1_783_987_200_000


def test_initial_backfill_skips_when_data_already_exists(session: Session) -> None:
    open_time = datetime(2026, 7, 13, 23, 58, tzinfo=UTC)
    client = FakeBinanceRestClient({"BTCUSDT": [make_kline(open_time, close_price="101.00")]})
    service = build_service(session, client)

    service.run()
    session.commit()
    second_result = service.run()
    session.commit()

    assert second_result[0].skipped is True
    assert len(client.kline_calls) == 1
    assert session.scalar(select(func.count()).select_from(Candle)) == 1
    assert session.scalar(select(func.count()).select_from(BackfillJob)) == 1


def test_initial_backfill_does_not_create_duplicates_on_duplicate_rest_data(
    session: Session,
) -> None:
    open_time = datetime(2026, 7, 13, 23, 58, tzinfo=UTC)
    client = FakeBinanceRestClient(
        {
            "BTCUSDT": [
                make_kline(open_time, close_price="101.00"),
                make_kline(open_time, close_price="102.00"),
            ]
        }
    )

    build_service(session, client).run()
    session.commit()

    candles = session.scalars(select(Candle)).all()
    assert len(candles) == 1
    assert candles[0].close_price == Decimal("102.00000000")


def test_initial_backfill_stores_both_symbols(session: Session) -> None:
    btc_open = datetime(2026, 7, 13, 23, 58, tzinfo=UTC)
    eth_open = datetime(2026, 7, 13, 23, 59, tzinfo=UTC)
    client = FakeBinanceRestClient(
        {
            "BTCUSDT": [make_kline(btc_open, close_price="101.00")],
            "ETHUSDT": [make_kline(eth_open, close_price="202.00")],
        }
    )

    result = build_service(session, client, symbols=["BTCUSDT", "ETHUSDT"]).run()
    session.commit()

    symbols = set(session.scalars(select(Candle.symbol)).all())
    assert symbols == {"BTCUSDT", "ETHUSDT"}
    assert [item.symbol for item in result] == ["BTCUSDT", "ETHUSDT"]
    assert all(item.stored_candle_count == 1 for item in result)
    assert session.scalar(select(func.count()).select_from(BackfillJob)) == 2
