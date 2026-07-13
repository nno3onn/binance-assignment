"""create market data tables

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14 00:00:00 UTC
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("quote_volume", sa.Numeric(precision=28, scale=12), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("source in ('websocket', 'rest_backfill')", name="ck_candles_source"),
        sa.UniqueConstraint(
            "symbol", "interval", "open_time", name="uq_candles_symbol_interval_open_time"
        ),
    )
    op.create_index(
        "ix_candles_symbol_interval_open_time", "candles", ["symbol", "interval", "open_time"]
    )
    op.create_index(
        "ix_candles_symbol_interval_close_time", "candles", ["symbol", "interval", "close_time"]
    )
    op.create_index("ix_candles_source", "candles", ["source"])

    op.create_table(
        "symbol_runtime_status",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_candle_open_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lag_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status in ('INITIALIZING', 'LIVE', 'DEGRADED', 'BACKFILLING', 'STALE', 'ERROR')",
            name="ck_symbol_runtime_status_status",
        ),
        sa.UniqueConstraint("symbol", "interval", name="uq_symbol_runtime_status_symbol_interval"),
    )
    op.create_index("ix_symbol_runtime_status_status", "symbol_runtime_status", ["status"])
    op.create_index(
        "ix_symbol_runtime_status_symbol_interval",
        "symbol_runtime_status",
        ["symbol", "interval"],
    )

    op.create_table(
        "backfill_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_type", sa.String(length=30), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_candle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_candle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_candle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "job_type in ('initial', 'restart_recovery')", name="ck_backfill_jobs_job_type"
        ),
        sa.CheckConstraint(
            "status in ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_backfill_jobs_status",
        ),
    )
    op.create_index(
        "ix_backfill_jobs_symbol_interval_status", "backfill_jobs", ["symbol", "interval", "status"]
    )
    op.create_index("ix_backfill_jobs_job_type", "backfill_jobs", ["job_type"])
    op.create_index(
        "ix_backfill_jobs_range",
        "backfill_jobs",
        ["symbol", "interval", "range_start", "range_end"],
    )

    op.create_table(
        "application_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("interval", sa.String(length=10), nullable=True),
        sa.Column("backfill_job_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "severity in ('INFO', 'WARN', 'ERROR')", name="ck_application_events_severity"
        ),
        sa.ForeignKeyConstraint(
            ["backfill_job_id"],
            ["backfill_jobs.id"],
            name="fk_application_events_backfill_job_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_application_events_event_time", "application_events", ["event_time"])
    op.create_index("ix_application_events_event_type", "application_events", ["event_type"])
    op.create_index(
        "ix_application_events_symbol_interval", "application_events", ["symbol", "interval"]
    )
    op.create_index(
        "ix_application_events_backfill_job_id", "application_events", ["backfill_job_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_application_events_backfill_job_id", table_name="application_events")
    op.drop_index("ix_application_events_symbol_interval", table_name="application_events")
    op.drop_index("ix_application_events_event_type", table_name="application_events")
    op.drop_index("ix_application_events_event_time", table_name="application_events")
    op.drop_table("application_events")

    op.drop_index("ix_backfill_jobs_range", table_name="backfill_jobs")
    op.drop_index("ix_backfill_jobs_job_type", table_name="backfill_jobs")
    op.drop_index("ix_backfill_jobs_symbol_interval_status", table_name="backfill_jobs")
    op.drop_table("backfill_jobs")

    op.drop_index("ix_symbol_runtime_status_symbol_interval", table_name="symbol_runtime_status")
    op.drop_index("ix_symbol_runtime_status_status", table_name="symbol_runtime_status")
    op.drop_table("symbol_runtime_status")

    op.drop_index("ix_candles_source", table_name="candles")
    op.drop_index("ix_candles_symbol_interval_close_time", table_name="candles")
    op.drop_index("ix_candles_symbol_interval_open_time", table_name="candles")
    op.drop_table("candles")
