from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.api.stream import dashboard_stream
from app.config import Settings
from app.domain.market_data import (
    BackfillJobInput,
    BackfillJobStatus,
    BackfillJobType,
    CandleInput,
    CandleSource,
    RuntimeStatus,
    RuntimeStatusInput,
)
from app.models import Base
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.dashboard import DashboardQueryConfig, DashboardQueryService
from app.services.stream import DashboardSseService


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


@pytest.fixture()
def repository(session: Session) -> SqlAlchemyMarketDataRepository:
    return SqlAlchemyMarketDataRepository(session)


def candle(symbol: str, open_time: datetime, close_price: str = "105") -> CandleInput:
    return CandleInput(
        symbol=symbol,
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1) - timedelta(milliseconds=1),
        open_price=Decimal("100"),
        high_price=Decimal("110"),
        low_price=Decimal("90"),
        close_price=Decimal(close_price),
        volume=Decimal("12"),
        quote_volume=Decimal("1200"),
        trade_count=42,
        source=CandleSource.WEBSOCKET,
    )


def seed_stream_data(repository: SqlAlchemyMarketDataRepository, session: Session) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    repository.bulk_upsert_candles([candle("BTCUSDT", start, "101")])
    repository.save_runtime_status(
        RuntimeStatusInput(
            symbol="BTCUSDT",
            interval="1m",
            status=RuntimeStatus.LIVE,
            last_event_at=start,
            last_candle_open_time=start,
            lag_seconds=2,
        )
    )
    repository.create_backfill_job(
        BackfillJobInput(
            job_type=BackfillJobType.INITIAL,
            symbol="BTCUSDT",
            interval="1m",
            status=BackfillJobStatus.SUCCEEDED,
            range_start=start,
            range_end=start,
        )
    )
    session.commit()


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.current += timedelta(seconds=10)
        return self.current


async def no_sleep(_seconds: float) -> None:
    return None


def parse_sse_data(frame: str) -> dict[str, object]:
    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    return cast(dict[str, object], json.loads(data_line.removeprefix("data: ")))


async def collect_events(stream: AsyncIterator[str], count: int) -> list[str]:
    events: list[str] = []
    async for event in stream:
        events.append(event)
        if len(events) >= count:
            break
    return events


def sse_service(
    repository: SqlAlchemyMarketDataRepository,
    clock: FakeClock,
    heartbeat_seconds: float = 5,
) -> DashboardSseService:
    dashboard = DashboardQueryService(
        repository,
        DashboardQueryConfig(symbols=["BTCUSDT", "ETHUSDT"], interval="1m"),
        now=datetime(2026, 7, 14, 0, 1, tzinfo=UTC),
    )
    return DashboardSseService(
        dashboard,
        interval_seconds=0.01,
        heartbeat_seconds=heartbeat_seconds,
        sleep=no_sleep,
        now=clock,
    )


def test_sse_content_type(repository: SqlAlchemyMarketDataRepository) -> None:
    class FakeRequest:
        async def is_disconnected(self) -> bool:
            return True

    response = dashboard_stream(
        request=cast(Request, FakeRequest()),
        repository=repository,
        settings=Settings(
            dashboard_sse_interval_seconds=0.01, dashboard_sse_heartbeat_seconds=0.01
        ),
    )

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"


def test_initial_snapshot_contains_required_payload(
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    seed_stream_data(repository, session)
    service = sse_service(repository, FakeClock())

    events = asyncio.run(collect_events(service.stream(is_disconnected=_never_disconnected), 1))

    assert events[0].startswith("event: dashboard_snapshot")
    payload = parse_sse_data(events[0])
    assert payload["event_type"] == "dashboard_snapshot"
    assert payload["system_health"] in {"LIVE", "DEGRADED", "INITIALIZING"}
    assert payload["active_gap_count"] == 0
    assert payload["latest_backfill_status"] == "SUCCEEDED"
    assert isinstance(payload["emitted_at"], str)
    assert payload["emitted_at"].endswith(("+00:00", "Z"))


def test_heartbeat_is_emitted(repository: SqlAlchemyMarketDataRepository) -> None:
    service = sse_service(repository, FakeClock())

    events = asyncio.run(collect_events(service.stream(is_disconnected=_never_disconnected), 2))

    assert events[1].startswith("event: heartbeat")
    assert parse_sse_data(events[1])["event_type"] == "heartbeat"


def test_client_disconnect_stops_generator(repository: SqlAlchemyMarketDataRepository) -> None:
    service = sse_service(repository, FakeClock(), heartbeat_seconds=100)
    checks = 0

    async def disconnected_after_first_check() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    events = asyncio.run(
        collect_events(service.stream(is_disconnected=disconnected_after_first_check), 5)
    )

    assert len(events) == 1


def test_dashboard_service_error_yields_error_event(
    repository: SqlAlchemyMarketDataRepository,
) -> None:
    class FailingDashboard:
        def summary(self) -> object:
            raise RuntimeError("snapshot unavailable")

        def backfill_jobs(self, limit: int) -> list[object]:
            return []

    service = DashboardSseService(
        FailingDashboard(),  # type: ignore[arg-type]
        interval_seconds=0.01,
        heartbeat_seconds=5,
        sleep=no_sleep,
        now=FakeClock(),
    )

    events = asyncio.run(collect_events(service.stream(is_disconnected=_never_disconnected), 1))

    assert events[0].startswith("event: error")
    payload = parse_sse_data(events[0])
    assert payload["event_type"] == "error"
    assert isinstance(payload["emitted_at"], str)
    assert payload["emitted_at"].endswith(("+00:00", "Z"))


def test_error_event_does_not_make_server_return_500(
    repository: SqlAlchemyMarketDataRepository,
) -> None:
    service = DashboardSseService(
        dashboard=DashboardQueryService(
            repository,
            DashboardQueryConfig(symbols=["BTCUSDT"], interval="1m"),
        ),
        interval_seconds=0.01,
        heartbeat_seconds=5,
        sleep=no_sleep,
        now=FakeClock(),
    )

    events = asyncio.run(collect_events(service.stream(is_disconnected=_never_disconnected), 1))

    assert events[0].startswith("event: dashboard_snapshot")


async def _never_disconnected() -> bool:
    return False
