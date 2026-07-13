from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.binance.errors import BinanceInvalidResponseError


@dataclass(frozen=True)
class BinanceServerTime:
    server_time_ms: int

    @property
    def server_time(self) -> datetime:
        return datetime.fromtimestamp(self.server_time_ms / 1000, tz=UTC)


@dataclass(frozen=True)
class BinanceKline:
    open_time_ms: int
    open_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    close_time_ms: int
    close_time: datetime
    quote_volume: Decimal
    trade_count: int
    taker_buy_base_volume: Decimal
    taker_buy_quote_volume: Decimal

    @classmethod
    def from_api_row(cls, row: Any) -> BinanceKline:
        if not isinstance(row, list) or len(row) < 11:
            raise BinanceInvalidResponseError("Kline row must be a list with at least 11 fields")

        try:
            open_time_ms = int(row[0])
            close_time_ms = int(row[6])
            return cls(
                open_time_ms=open_time_ms,
                open_time=datetime.fromtimestamp(open_time_ms / 1000, tz=UTC),
                open_price=Decimal(str(row[1])),
                high_price=Decimal(str(row[2])),
                low_price=Decimal(str(row[3])),
                close_price=Decimal(str(row[4])),
                volume=Decimal(str(row[5])),
                close_time_ms=close_time_ms,
                close_time=datetime.fromtimestamp(close_time_ms / 1000, tz=UTC),
                quote_volume=Decimal(str(row[7])),
                trade_count=int(row[8]),
                taker_buy_base_volume=Decimal(str(row[9])),
                taker_buy_quote_volume=Decimal(str(row[10])),
            )
        except (ArithmeticError, TypeError, ValueError) as exc:
            raise BinanceInvalidResponseError("Kline row contains invalid values") from exc
