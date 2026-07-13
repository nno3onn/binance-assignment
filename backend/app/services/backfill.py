from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.binance.dto import BinanceKline
from app.binance.interfaces import BinanceRestClient
from app.domain.market_data import (
    BackfillJobInput,
    BackfillJobStatus,
    BackfillJobType,
    CandleInput,
    CandleSource,
)
from app.models.market_data import BackfillJob
from app.repositories.interfaces import MarketDataRepository
from app.services.events import EventHistoryService

BINANCE_KLINES_MAX_LIMIT = 1000


def kline_to_rest_backfill_candle(symbol: str, interval: str, kline: BinanceKline) -> CandleInput:
    return CandleInput(
        symbol=symbol,
        interval=interval,
        open_time=kline.open_time,
        close_time=kline.close_time,
        open_price=kline.open_price,
        high_price=kline.high_price,
        low_price=kline.low_price,
        close_price=kline.close_price,
        volume=kline.volume,
        quote_volume=kline.quote_volume,
        trade_count=kline.trade_count,
        source=CandleSource.REST_BACKFILL,
    )


@dataclass(frozen=True)
class InitialBackfillResult:
    symbol: str
    interval: str
    skipped: bool
    stored_candle_count: int
    backfill_job: BackfillJob | None


class InitialBackfillService:
    def __init__(
        self,
        repository: MarketDataRepository,
        binance_rest_client: BinanceRestClient,
        symbols: list[str],
        interval: str,
        initial_backfill_hours: int,
        now: datetime | None = None,
        event_history: EventHistoryService | None = None,
    ) -> None:
        self._repository = repository
        self._binance_rest_client = binance_rest_client
        self._symbols = symbols
        self._interval = interval
        self._initial_backfill_hours = initial_backfill_hours
        self._now = now
        self._event_history = event_history

    def run(self) -> list[InitialBackfillResult]:
        return [self._run_for_symbol(symbol) for symbol in self._symbols]

    def _run_for_symbol(self, symbol: str) -> InitialBackfillResult:
        if self._repository.get_latest_candle(symbol, self._interval) is not None:
            return InitialBackfillResult(
                symbol=symbol,
                interval=self._interval,
                skipped=True,
                stored_candle_count=0,
                backfill_job=None,
            )

        if self._event_history is not None:
            self._event_history.initial_backfill_started(symbol, self._interval)

        range_end = self._current_time()
        range_start = range_end - timedelta(hours=self._initial_backfill_hours)
        klines = self._binance_rest_client.get_klines(
            symbol=symbol,
            interval=self._interval,
            start_time=self._to_milliseconds(range_start),
            end_time=self._to_milliseconds(range_end),
            limit=BINANCE_KLINES_MAX_LIMIT,
        )

        job = self._repository.create_backfill_job(
            BackfillJobInput(
                job_type=BackfillJobType.INITIAL,
                symbol=symbol,
                interval=self._interval,
                status=BackfillJobStatus.SUCCEEDED,
                range_start=range_start,
                range_end=range_end,
                requested_candle_count=len(klines),
                inserted_candle_count=len(klines),
                updated_candle_count=0,
                attempt_count=1,
                started_at=range_start,
                finished_at=range_end,
            )
        )
        candles = [kline_to_rest_backfill_candle(symbol, self._interval, kline) for kline in klines]
        self._repository.bulk_upsert_candles(candles)
        if self._event_history is not None:
            self._event_history.initial_backfill_completed(
                symbol=symbol,
                interval=self._interval,
                stored_candle_count=len(candles),
                backfill_job_id=job.id,
            )

        return InitialBackfillResult(
            symbol=symbol,
            interval=self._interval,
            skipped=False,
            stored_candle_count=len(candles),
            backfill_job=job,
        )

    def _current_time(self) -> datetime:
        current = self._now or datetime.now(tz=UTC)
        if current.tzinfo is None:
            return current.replace(tzinfo=UTC)
        return current.astimezone(UTC)

    @staticmethod
    def _to_milliseconds(value: datetime) -> int:
        return int(value.timestamp() * 1000)
