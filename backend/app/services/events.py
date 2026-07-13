from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.domain.market_data import ApplicationEventInput, ApplicationEventType, EventSeverity
from app.models.market_data import ApplicationEvent
from app.repositories.interfaces import MarketDataRepository

Clock = Callable[[], datetime]


class EventHistoryService:
    def __init__(
        self,
        repository: MarketDataRepository,
        *,
        now: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(tz=UTC))

    def record(
        self,
        *,
        event_type: ApplicationEventType,
        severity: EventSeverity,
        message: str,
        occurred_at: datetime | None = None,
        symbol: str | None = None,
        interval: str | None = None,
        metadata: dict[str, Any] | None = None,
        backfill_job_id: int | None = None,
    ) -> ApplicationEvent | None:
        try:
            return self._repository.append_application_event(
                ApplicationEventInput(
                    severity=severity,
                    event_type=event_type.value,
                    message=message,
                    event_time=self._normalize(occurred_at or self._now()),
                    symbol=symbol,
                    interval=interval,
                    backfill_job_id=backfill_job_id,
                    metadata_json=metadata or {},
                )
            )
        except Exception:
            return None

    def recent(self, limit: int = 100) -> list[ApplicationEvent]:
        return self._repository.list_recent_application_events(limit)

    def websocket_connected(self, symbols: list[str], interval: str) -> None:
        self.record(
            event_type=ApplicationEventType.WEBSOCKET_CONNECTED,
            severity=EventSeverity.INFO,
            message="Binance WebSocket connected",
            interval=interval,
            metadata={"symbols": symbols},
        )

    def websocket_disconnected(self, symbols: list[str], interval: str) -> None:
        self.record(
            event_type=ApplicationEventType.WEBSOCKET_DISCONNECTED,
            severity=EventSeverity.WARNING,
            message="Binance WebSocket disconnected",
            interval=interval,
            metadata={"symbols": symbols},
        )

    def websocket_reconnecting(self, symbols: list[str], interval: str, attempt: int) -> None:
        self.record(
            event_type=ApplicationEventType.WEBSOCKET_RECONNECTING,
            severity=EventSeverity.WARNING,
            message="Binance WebSocket reconnecting",
            interval=interval,
            metadata={"symbols": symbols, "attempt": attempt},
        )

    def invalid_message_received(
        self, symbol: str | None = None, interval: str | None = None
    ) -> None:
        self.record(
            event_type=ApplicationEventType.INVALID_MESSAGE_RECEIVED,
            severity=EventSeverity.WARNING,
            message="Invalid Binance WebSocket message ignored",
            symbol=symbol,
            interval=interval,
        )

    def initial_backfill_started(self, symbol: str, interval: str) -> None:
        self.record(
            event_type=ApplicationEventType.INITIAL_BACKFILL_STARTED,
            severity=EventSeverity.INFO,
            message="Initial backfill started",
            symbol=symbol,
            interval=interval,
        )

    def initial_backfill_completed(
        self,
        *,
        symbol: str,
        interval: str,
        stored_candle_count: int,
        backfill_job_id: int | None,
    ) -> None:
        self.record(
            event_type=ApplicationEventType.INITIAL_BACKFILL_COMPLETED,
            severity=EventSeverity.INFO,
            message="Initial backfill completed",
            symbol=symbol,
            interval=interval,
            backfill_job_id=backfill_job_id,
            metadata={"stored_candle_count": stored_candle_count},
        )

    def recovery_started(self, symbol: str, interval: str) -> None:
        self.record(
            event_type=ApplicationEventType.RECOVERY_STARTED,
            severity=EventSeverity.INFO,
            message="Restart recovery started",
            symbol=symbol,
            interval=interval,
        )

    def recovery_completed(
        self,
        *,
        symbol: str,
        interval: str,
        recovered_gap_count: int,
        stored_candle_count: int,
    ) -> None:
        self.record(
            event_type=ApplicationEventType.RECOVERY_COMPLETED,
            severity=EventSeverity.INFO,
            message="Restart recovery completed",
            symbol=symbol,
            interval=interval,
            metadata={
                "recovered_gap_count": recovered_gap_count,
                "stored_candle_count": stored_candle_count,
            },
        )

    def recovery_failed(self, symbol: str, interval: str, error: Exception) -> None:
        self.record(
            event_type=ApplicationEventType.RECOVERY_FAILED,
            severity=EventSeverity.ERROR,
            message="Restart recovery failed",
            symbol=symbol,
            interval=interval,
            metadata={"error": str(error)},
        )

    @staticmethod
    def _normalize(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
