from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class CandleSource(StrEnum):
    WEBSOCKET = "websocket"
    REST_BACKFILL = "rest_backfill"


class RuntimeStatus(StrEnum):
    INITIALIZING = "INITIALIZING"
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    BACKFILLING = "BACKFILLING"
    STALE = "STALE"
    ERROR = "ERROR"


class ConnectionState(StrEnum):
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    DISCONNECTED = "DISCONNECTED"
    STOPPED = "STOPPED"


class BackfillJobType(StrEnum):
    INITIAL = "initial"
    RESTART_RECOVERY = "restart_recovery"


class BackfillJobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EventSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CandleInput:
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
    source: CandleSource


@dataclass(frozen=True)
class RuntimeStatusInput:
    symbol: str
    interval: str
    status: RuntimeStatus
    lag_seconds: int
    last_event_at: datetime | None = None
    last_candle_open_time: datetime | None = None
    consecutive_error_count: int = 0
    error_message: str | None = None


@dataclass(frozen=True)
class BackfillJobInput:
    job_type: BackfillJobType
    symbol: str
    interval: str
    status: BackfillJobStatus
    range_start: datetime
    range_end: datetime
    requested_candle_count: int = 0
    inserted_candle_count: int = 0
    updated_candle_count: int = 0
    attempt_count: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True)
class ApplicationEventInput:
    severity: EventSeverity
    event_type: str
    message: str
    event_time: datetime
    symbol: str | None = None
    interval: str | None = None
    backfill_job_id: int | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
