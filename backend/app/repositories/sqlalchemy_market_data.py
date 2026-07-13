from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.market_data import (
    ApplicationEventInput,
    BackfillJobInput,
    CandleInput,
    RuntimeStatusInput,
)
from app.models.market_data import ApplicationEvent, BackfillJob, Candle, SymbolRuntimeStatus


class SqlAlchemyMarketDataRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_candle(self, candle: CandleInput) -> Candle:
        existing = self._find_candle(candle.symbol, candle.interval, candle.open_time)
        if existing is None:
            existing = Candle(
                symbol=candle.symbol,
                interval=candle.interval,
                open_time=candle.open_time,
                close_time=candle.close_time,
                open_price=candle.open_price,
                high_price=candle.high_price,
                low_price=candle.low_price,
                close_price=candle.close_price,
                volume=candle.volume,
                quote_volume=candle.quote_volume,
                trade_count=candle.trade_count,
                source=candle.source.value,
            )
            self.session.add(existing)
        else:
            existing.close_time = candle.close_time
            existing.open_price = candle.open_price
            existing.high_price = candle.high_price
            existing.low_price = candle.low_price
            existing.close_price = candle.close_price
            existing.volume = candle.volume
            existing.quote_volume = candle.quote_volume
            existing.trade_count = candle.trade_count
            existing.source = candle.source.value

        self.session.flush()
        self._normalize_candle_datetimes(existing)
        return existing

    def bulk_upsert_candles(self, candles: list[CandleInput]) -> list[Candle]:
        return [self.upsert_candle(candle) for candle in candles]

    def get_latest_candle(self, symbol: str, interval: str) -> Candle | None:
        statement = (
            self._candles_for_symbol(symbol, interval).order_by(Candle.open_time.desc()).limit(1)
        )
        candle = self.session.execute(statement).scalar_one_or_none()
        if candle is not None:
            self._normalize_candle_datetimes(candle)
        return candle

    def get_last_open_time(self, symbol: str, interval: str) -> datetime | None:
        candle = self.get_latest_candle(symbol, interval)
        if candle is None:
            return None
        return candle.open_time

    def list_candles_by_symbol(self, symbol: str, interval: str, limit: int = 100) -> list[Candle]:
        statement = (
            self._candles_for_symbol(symbol, interval)
            .order_by(Candle.open_time.desc())
            .limit(limit)
        )
        candles = list(self.session.execute(statement).scalars().all())
        for candle in candles:
            self._normalize_candle_datetimes(candle)
        return candles

    def list_candles_in_range(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        statement = (
            self._candles_for_symbol(symbol, interval)
            .where(Candle.open_time >= start, Candle.open_time <= end)
            .order_by(Candle.open_time.asc())
        )
        candles = list(self.session.execute(statement).scalars().all())
        for candle in candles:
            self._normalize_candle_datetimes(candle)
        return candles

    def save_runtime_status(self, status: RuntimeStatusInput) -> SymbolRuntimeStatus:
        existing = self.get_runtime_status(status.symbol, status.interval)
        if existing is None:
            existing = SymbolRuntimeStatus(
                symbol=status.symbol,
                interval=status.interval,
                status=status.status.value,
                last_event_at=status.last_event_at,
                last_candle_open_time=status.last_candle_open_time,
                lag_seconds=status.lag_seconds,
                consecutive_error_count=status.consecutive_error_count,
                error_message=status.error_message,
            )
            self.session.add(existing)
        else:
            existing.status = status.status.value
            existing.last_event_at = status.last_event_at
            existing.last_candle_open_time = status.last_candle_open_time
            existing.lag_seconds = status.lag_seconds
            existing.consecutive_error_count = status.consecutive_error_count
            existing.error_message = status.error_message

        self.session.flush()
        self._normalize_runtime_status_datetimes(existing)
        return existing

    def get_runtime_status(self, symbol: str, interval: str) -> SymbolRuntimeStatus | None:
        statement = select(SymbolRuntimeStatus).where(
            SymbolRuntimeStatus.symbol == symbol,
            SymbolRuntimeStatus.interval == interval,
        )
        status = self.session.execute(statement).scalar_one_or_none()
        if status is not None:
            self._normalize_runtime_status_datetimes(status)
        return status

    def create_backfill_job(self, job: BackfillJobInput) -> BackfillJob:
        model = BackfillJob(
            job_type=job.job_type.value,
            symbol=job.symbol,
            interval=job.interval,
            status=job.status.value,
            range_start=job.range_start,
            range_end=job.range_end,
            requested_candle_count=job.requested_candle_count,
            inserted_candle_count=job.inserted_candle_count,
            updated_candle_count=job.updated_candle_count,
            attempt_count=job.attempt_count,
            error_message=job.error_message,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        self.session.add(model)
        self.session.flush()
        self._normalize_backfill_job_datetimes(model)
        return model

    def get_backfill_job(self, job_id: int) -> BackfillJob | None:
        job = self.session.get(BackfillJob, job_id)
        if job is not None:
            self._normalize_backfill_job_datetimes(job)
        return job

    def append_application_event(self, event: ApplicationEventInput) -> ApplicationEvent:
        model = ApplicationEvent(
            event_time=event.event_time,
            severity=event.severity.value,
            event_type=event.event_type,
            symbol=event.symbol,
            interval=event.interval,
            backfill_job_id=event.backfill_job_id,
            message=event.message,
            metadata_json=event.metadata_json,
        )
        self.session.add(model)
        self.session.flush()
        self._normalize_application_event_datetimes(model)
        return model

    def _find_candle(self, symbol: str, interval: str, open_time: datetime) -> Candle | None:
        statement = self._candles_for_symbol(symbol, interval).where(Candle.open_time == open_time)
        return self.session.execute(statement).scalar_one_or_none()

    @staticmethod
    def _candles_for_symbol(symbol: str, interval: str) -> Select[tuple[Candle]]:
        return select(Candle).where(Candle.symbol == symbol, Candle.interval == interval)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return SqlAlchemyMarketDataRepository._required_as_utc(value)

    @staticmethod
    def _required_as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _normalize_candle_datetimes(self, candle: Candle) -> None:
        candle.open_time = self._required_as_utc(candle.open_time)
        candle.close_time = self._required_as_utc(candle.close_time)
        candle.created_at = self._required_as_utc(candle.created_at)
        candle.updated_at = self._required_as_utc(candle.updated_at)

    def _normalize_runtime_status_datetimes(self, status: SymbolRuntimeStatus) -> None:
        status.last_event_at = self._as_utc(status.last_event_at)
        status.last_candle_open_time = self._as_utc(status.last_candle_open_time)
        status.created_at = self._required_as_utc(status.created_at)
        status.updated_at = self._required_as_utc(status.updated_at)

    def _normalize_backfill_job_datetimes(self, job: BackfillJob) -> None:
        job.range_start = self._required_as_utc(job.range_start)
        job.range_end = self._required_as_utc(job.range_end)
        job.started_at = self._as_utc(job.started_at)
        job.finished_at = self._as_utc(job.finished_at)
        job.created_at = self._required_as_utc(job.created_at)
        job.updated_at = self._required_as_utc(job.updated_at)

    def _normalize_application_event_datetimes(self, event: ApplicationEvent) -> None:
        event.event_time = self._required_as_utc(event.event_time)
        event.created_at = self._required_as_utc(event.created_at)
