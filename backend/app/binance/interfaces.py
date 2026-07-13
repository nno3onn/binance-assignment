from __future__ import annotations

from typing import Protocol

from app.binance.dto import BinanceKline, BinanceServerTime


class BinanceRestClient(Protocol):
    def ping(self) -> None:
        pass

    def get_server_time(self) -> BinanceServerTime:
        pass

    def get_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[BinanceKline]:
        pass
