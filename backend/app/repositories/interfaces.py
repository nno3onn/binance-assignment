from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.market_data import (
    ApplicationEventInput,
    BackfillJobInput,
    CandleInput,
    RuntimeStatusInput,
)
from app.models.market_data import ApplicationEvent, BackfillJob, Candle, SymbolRuntimeStatus


class MarketDataRepository(Protocol):
    def upsert_candle(self, candle: CandleInput) -> Candle:
        pass

    def bulk_upsert_candles(self, candles: list[CandleInput]) -> list[Candle]:
        pass

    def get_latest_candle(self, symbol: str, interval: str) -> Candle | None:
        pass

    def get_last_open_time(self, symbol: str, interval: str) -> datetime | None:
        pass

    def list_candles_by_symbol(self, symbol: str, interval: str, limit: int = 100) -> list[Candle]:
        pass

    def list_candles_in_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        pass

    def save_runtime_status(self, status: RuntimeStatusInput) -> SymbolRuntimeStatus:
        pass

    def get_runtime_status(self, symbol: str, interval: str) -> SymbolRuntimeStatus | None:
        pass

    def create_backfill_job(self, job: BackfillJobInput) -> BackfillJob:
        pass

    def get_backfill_job(self, job_id: int) -> BackfillJob | None:
        pass

    def append_application_event(self, event: ApplicationEventInput) -> ApplicationEvent:
        pass

    def list_recent_application_events(self, limit: int = 100) -> list[ApplicationEvent]:
        pass
