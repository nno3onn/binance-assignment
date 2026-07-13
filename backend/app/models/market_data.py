from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.models.base import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        CheckConstraint("source in ('websocket', 'rest_backfill')", name="ck_candles_source"),
        UniqueConstraint(
            "symbol",
            "interval",
            "open_time",
            name="uq_candles_symbol_interval_open_time",
        ),
        Index("ix_candles_symbol_interval_open_time", "symbol", "interval", "open_time"),
        Index("ix_candles_symbol_interval_close_time", "symbol", "interval", "close_time"),
        Index("ix_candles_source", "source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    quote_volume: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    trade_count: Mapped[int] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SymbolRuntimeStatus(Base):
    __tablename__ = "symbol_runtime_status"
    __table_args__ = (
        CheckConstraint(
            "status in ('INITIALIZING', 'LIVE', 'DEGRADED', 'BACKFILLING', 'STALE', 'ERROR')",
            name="ck_symbol_runtime_status_status",
        ),
        UniqueConstraint("symbol", "interval", name="uq_symbol_runtime_status_symbol_interval"),
        Index("ix_symbol_runtime_status_status", "status"),
        Index("ix_symbol_runtime_status_symbol_interval", "symbol", "interval"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_candle_open_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    lag_seconds: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    consecutive_error_count: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BackfillJob(Base):
    __tablename__ = "backfill_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type in ('initial', 'restart_recovery')", name="ck_backfill_jobs_job_type"
        ),
        CheckConstraint(
            "status in ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_backfill_jobs_status",
        ),
        Index("ix_backfill_jobs_symbol_interval_status", "symbol", "interval", "status"),
        Index("ix_backfill_jobs_job_type", "job_type"),
        Index("ix_backfill_jobs_range", "symbol", "interval", "range_start", "range_end"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_candle_count: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    inserted_candle_count: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    updated_candle_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    events: Mapped[list[ApplicationEvent]] = relationship(back_populates="backfill_job")


class ApplicationEvent(Base):
    __tablename__ = "application_events"
    __table_args__ = (
        CheckConstraint(
            "severity in ('INFO', 'WARN', 'ERROR')", name="ck_application_events_severity"
        ),
        Index("ix_application_events_event_time", "event_time"),
        Index("ix_application_events_event_type", "event_type"),
        Index("ix_application_events_symbol_interval", "symbol", "interval"),
        Index("ix_application_events_backfill_job_id", "backfill_job_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    interval: Mapped[str | None] = mapped_column(String(10), nullable=True)
    backfill_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("backfill_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    backfill_job: Mapped[BackfillJob | None] = relationship(back_populates="events")
