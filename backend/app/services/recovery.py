from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.binance.interfaces import BinanceRestClient
from app.repositories.interfaces import MarketDataRepository
from app.services.backfill import BINANCE_KLINES_MAX_LIMIT, kline_to_rest_backfill_candle
from app.services.events import EventHistoryService
from app.services.gaps import CandleGap, GapDetectionService


@dataclass(frozen=True)
class GapRecoveryResult:
    symbol: str
    interval: str
    gap_start: datetime
    gap_end: datetime
    missing_candle_count: int
    fetched_candle_count: int
    stored_candle_count: int


@dataclass(frozen=True)
class RestartRecoveryResult:
    symbol: str
    interval: str
    recovered_gap_count: int
    fetched_candle_count: int
    stored_candle_count: int
    gap_results: list[GapRecoveryResult]


class RestartRecoveryService:
    def __init__(
        self,
        repository: MarketDataRepository,
        binance_rest_client: BinanceRestClient,
        gap_detection_service: GapDetectionService,
        event_history: EventHistoryService | None = None,
    ) -> None:
        self._repository = repository
        self._binance_rest_client = binance_rest_client
        self._gap_detection_service = gap_detection_service
        self._event_history = event_history

    def recover_symbols(
        self,
        symbols: list[str],
        interval: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[RestartRecoveryResult]:
        return [
            self.recover_symbol(symbol=symbol, interval=interval, start=start, end=end)
            for symbol in symbols
        ]

    def recover_symbol(
        self,
        *,
        symbol: str,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> RestartRecoveryResult:
        if self._event_history is not None:
            self._event_history.recovery_started(symbol, interval)
        try:
            gap_detection = self._gap_detection_service.detect_for_symbol(
                symbol=symbol,
                interval=interval,
                start=start,
                end=end,
            )
            gap_results = [self._recover_gap(gap) for gap in gap_detection.gaps]

            result = RestartRecoveryResult(
                symbol=symbol,
                interval=interval,
                recovered_gap_count=len(gap_results),
                fetched_candle_count=sum(result.fetched_candle_count for result in gap_results),
                stored_candle_count=sum(result.stored_candle_count for result in gap_results),
                gap_results=gap_results,
            )
            if self._event_history is not None:
                self._event_history.recovery_completed(
                    symbol=symbol,
                    interval=interval,
                    recovered_gap_count=result.recovered_gap_count,
                    stored_candle_count=result.stored_candle_count,
                )
            return result
        except Exception as exc:
            if self._event_history is not None:
                self._event_history.recovery_failed(symbol, interval, exc)
            raise

    def _recover_gap(self, gap: CandleGap) -> GapRecoveryResult:
        klines = self._binance_rest_client.get_klines(
            symbol=gap.symbol,
            interval=gap.interval,
            start_time=self._to_milliseconds(gap.start_time),
            end_time=self._to_milliseconds(gap.end_time),
            limit=BINANCE_KLINES_MAX_LIMIT,
        )
        missing_open_times = self._missing_open_times(gap)
        candles = [
            kline_to_rest_backfill_candle(gap.symbol, gap.interval, kline)
            for kline in klines
            if kline.open_time in missing_open_times
        ]
        if candles:
            self._repository.bulk_upsert_candles(candles)

        return GapRecoveryResult(
            symbol=gap.symbol,
            interval=gap.interval,
            gap_start=gap.start_time,
            gap_end=gap.end_time,
            missing_candle_count=gap.missing_candle_count,
            fetched_candle_count=len(klines),
            stored_candle_count=len(candles),
        )

    @staticmethod
    def _missing_open_times(gap: CandleGap) -> set[datetime]:
        current = gap.start_time
        values: set[datetime] = set()
        while current <= gap.end_time:
            values.add(current)
            current += timedelta(minutes=1)
        return values

    @staticmethod
    def _to_milliseconds(value: datetime) -> int:
        return int(value.timestamp() * 1000)
