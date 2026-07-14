from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.api.schemas import (
    ApplicationEventResponse,
    BackfillJobResponse,
    CandleResponse,
    DashboardSummaryResponse,
    GapResponse,
    GapsResponse,
    SymbolStatusResponse,
)
from app.repositories.interfaces import MarketDataRepository
from app.services.gaps import GapDetectionService


@dataclass(frozen=True)
class DashboardQueryConfig:
    symbols: list[str]
    interval: str


class DashboardQueryService:
    def __init__(
        self,
        repository: MarketDataRepository,
        config: DashboardQueryConfig,
        *,
        now: datetime | None = None,
    ) -> None:
        self._repository = repository
        self._config = config
        self._now = now or datetime.now(tz=UTC)

    def summary(self) -> DashboardSummaryResponse:
        symbol_statuses = self.symbols()
        gaps = self.gaps(symbol=None, start=None, end=None).gaps
        recent_jobs = self.backfill_jobs(limit=10)
        recent_events = self.events(limit=10)
        total_missing = sum(gap.missing_candle_count for gap in gaps)
        return DashboardSummaryResponse(
            system_status=self._system_status(symbol_statuses, total_missing),
            symbols=symbol_statuses,
            total_missing_candle_count=total_missing,
            active_gap_count=len(gaps),
            recent_backfill_job_count=len(recent_jobs),
            recent_event_count=len(recent_events),
        )

    def symbols(self) -> list[SymbolStatusResponse]:
        return [self._symbol_status(symbol) for symbol in self._config.symbols]

    def candles(
        self,
        *,
        symbol: str,
        limit: int,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[CandleResponse]:
        if start is not None and end is not None:
            candles = self._repository.list_candles_in_range(
                symbol,
                self._config.interval,
                start,
                end,
            )
        else:
            candles = self._repository.list_candles_by_symbol(
                symbol,
                self._config.interval,
                limit=limit,
            )
        return [CandleResponse.model_validate(candle) for candle in self._items(candles)[:limit]]

    def gaps(
        self,
        *,
        symbol: str | None,
        start: datetime | None,
        end: datetime | None,
    ) -> GapsResponse:
        service = GapDetectionService(self._repository)
        symbols = [symbol] if symbol is not None else self._config.symbols
        results = service.detect_for_symbols(symbols, self._config.interval, start=start, end=end)
        gaps = [
            GapResponse(
                symbol=gap.symbol,
                interval=gap.interval,
                start_time=gap.start_time,
                end_time=gap.end_time,
                missing_candle_count=gap.missing_candle_count,
            )
            for result in results
            for gap in result.gaps
        ]
        return GapsResponse(
            gaps=gaps,
            total_missing_candle_count=sum(gap.missing_candle_count for gap in gaps),
        )

    def backfill_jobs(self, limit: int) -> list[BackfillJobResponse]:
        return [
            BackfillJobResponse.model_validate(job)
            for job in self._items(self._repository.list_recent_backfill_jobs(limit))
        ]

    def events(self, limit: int) -> list[ApplicationEventResponse]:
        return [
            ApplicationEventResponse.model_validate(event)
            for event in self._items(self._repository.list_recent_application_events(limit))
        ]

    def _symbol_status(self, symbol: str) -> SymbolStatusResponse:
        status = self._repository.get_runtime_status(symbol, self._config.interval)
        latest_candle = self._repository.get_latest_candle(symbol, self._config.interval)
        last_event_at = status.last_event_at if status is not None else None
        freshness = (
            max(0, int((self._now - last_event_at).total_seconds()))
            if last_event_at is not None
            else None
        )
        return SymbolStatusResponse(
            symbol=symbol,
            interval=self._config.interval,
            status=status.status if status is not None else "INITIALIZING",
            last_event_at=last_event_at,
            last_candle_open_time=(
                status.last_candle_open_time
                if status is not None
                else latest_candle.open_time
                if latest_candle is not None
                else None
            ),
            freshness_seconds=freshness,
            lag_seconds=status.lag_seconds if status is not None else None,
            latest_price=latest_candle.close_price if latest_candle is not None else None,
        )

    @staticmethod
    def _system_status(symbols: list[SymbolStatusResponse], missing_count: int) -> str:
        if any(symbol.status == "ERROR" for symbol in symbols):
            return "ERROR"
        if missing_count > 0 or any(symbol.status in {"DEGRADED", "STALE"} for symbol in symbols):
            return "DEGRADED"
        if all(symbol.status == "LIVE" for symbol in symbols):
            return "LIVE"
        return "INITIALIZING"

    @staticmethod
    def _items(values: Iterable[object] | None) -> list[object]:
        if values is None:
            return []
        return list(values)
