from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    environment: str
    symbols: list[str]
    interval: str
    initial_backfill_hours: int


class SymbolStatusResponse(BaseModel):
    symbol: str
    interval: str
    status: str
    last_event_at: datetime | None
    last_candle_open_time: datetime | None
    freshness_seconds: int | None
    lag_seconds: int | None
    latest_price: Decimal | None


class DashboardSummaryResponse(BaseModel):
    system_status: str
    symbols: list[SymbolStatusResponse]
    total_missing_candle_count: int
    active_gap_count: int
    recent_backfill_job_count: int
    recent_event_count: int


class CandleResponse(BaseModel):
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    trade_count: int
    source: str

    model_config = ConfigDict(from_attributes=True)


class CandlesResponse(BaseModel):
    symbol: str
    interval: str
    candles: list[CandleResponse]


class GapResponse(BaseModel):
    symbol: str
    interval: str
    start_time: datetime
    end_time: datetime
    missing_candle_count: int


class GapsResponse(BaseModel):
    gaps: list[GapResponse]
    total_missing_candle_count: int


class BackfillJobResponse(BaseModel):
    id: int
    job_type: str
    symbol: str
    interval: str
    status: str
    range_start: datetime
    range_end: datetime
    requested_candle_count: int
    inserted_candle_count: int
    updated_candle_count: int
    attempt_count: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BackfillJobsResponse(BaseModel):
    jobs: list[BackfillJobResponse]


class ApplicationEventResponse(BaseModel):
    id: int
    event_time: datetime
    severity: str
    event_type: str
    symbol: str | None
    interval: str | None
    backfill_job_id: int | None
    message: str
    metadata_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventsResponse(BaseModel):
    events: list[ApplicationEventResponse]


class DashboardStreamPayload(BaseModel):
    event_type: str
    emitted_at: datetime
    system_health: str
    symbols: list[SymbolStatusResponse]
    active_gap_count: int
    latest_backfill_status: str | None
