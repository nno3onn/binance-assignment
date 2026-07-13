from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from app.api.schemas import DashboardStreamPayload
from app.services.dashboard import DashboardQueryService

Sleep = Callable[[float], Awaitable[None]]
DisconnectCheck = Callable[[], Awaitable[bool]]
Clock = Callable[[], datetime]


class DashboardSseService:
    def __init__(
        self,
        dashboard: DashboardQueryService,
        *,
        interval_seconds: float,
        heartbeat_seconds: float,
        sleep: Sleep = asyncio.sleep,
        now: Clock | None = None,
    ) -> None:
        self._dashboard = dashboard
        self._interval_seconds = interval_seconds
        self._heartbeat_seconds = heartbeat_seconds
        self._sleep = sleep
        self._now = now or (lambda: datetime.now(tz=UTC))

    async def stream(
        self,
        *,
        is_disconnected: DisconnectCheck,
    ) -> AsyncIterator[str]:
        last_heartbeat = self._now()
        while not await is_disconnected():
            try:
                yield self._snapshot_event()
            except Exception as exc:
                yield format_sse(
                    event="error",
                    data={
                        "event_type": "error",
                        "emitted_at": self._utc_now().isoformat(),
                        "message": "dashboard snapshot failed",
                        "error": str(exc),
                    },
                )

            current = self._now()
            if (current - last_heartbeat).total_seconds() >= self._heartbeat_seconds:
                yield self.heartbeat_event()
                last_heartbeat = current

            await self._sleep(self._interval_seconds)

    def heartbeat_event(self) -> str:
        return format_sse(
            event="heartbeat",
            data={
                "event_type": "heartbeat",
                "emitted_at": self._utc_now().isoformat(),
            },
        )

    def _snapshot_event(self) -> str:
        summary = self._dashboard.summary()
        latest_job = next(iter(self._dashboard.backfill_jobs(limit=1)), None)
        payload = DashboardStreamPayload(
            event_type="dashboard_snapshot",
            emitted_at=self._utc_now(),
            system_health=summary.system_status,
            symbols=summary.symbols,
            active_gap_count=summary.active_gap_count,
            latest_backfill_status=latest_job.status if latest_job is not None else None,
        )
        return format_sse(
            event="dashboard_snapshot",
            data=payload.model_dump(mode="json"),
        )

    def _utc_now(self) -> datetime:
        current = self._now()
        if current.tzinfo is None:
            return current.replace(tzinfo=UTC)
        return current.astimezone(UTC)


def format_sse(*, event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
