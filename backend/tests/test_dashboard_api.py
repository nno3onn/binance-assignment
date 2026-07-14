from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_repository
from app.domain.market_data import (
    ApplicationEventInput,
    ApplicationEventType,
    BackfillJobInput,
    BackfillJobStatus,
    BackfillJobType,
    CandleInput,
    CandleSource,
    EventSeverity,
    RuntimeStatus,
    RuntimeStatusInput,
)
from app.main import create_app
from app.models import Base
from app.repositories.sqlalchemy_market_data import SqlAlchemyMarketDataRepository
from app.services.dashboard import DashboardQueryConfig, DashboardQueryService


class EmptyBoundaryRepository:
    def get_runtime_status(self, _symbol: str, _interval: str) -> None:
        return None

    def get_latest_candle(self, _symbol: str, _interval: str) -> None:
        return None

    def get_first_open_time(self, _symbol: str, _interval: str) -> None:
        return None

    def list_candles_by_symbol(
        self, _symbol: str, _interval: str, _limit: int = 100
    ) -> None:
        return None

    def list_candles_in_range(
        self,
        _symbol: str,
        _interval: str,
        _start: datetime,
        _end: datetime,
    ) -> None:
        return None

    def list_recent_backfill_jobs(self, _limit: int = 100) -> None:
        return None

    def list_recent_application_events(self, _limit: int = 100) -> None:
        return None

    def __getattr__(self, _name: str) -> Any:
        raise AssertionError("Unexpected repository call in empty dashboard summary")


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


@pytest.fixture()
def client(repository: SqlAlchemyMarketDataRepository) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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


def seed_dashboard_data(repository: SqlAlchemyMarketDataRepository, session: Session) -> None:
    start = datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    repository.bulk_upsert_candles(
        [
            candle("BTCUSDT", start, "101"),
            candle("BTCUSDT", start + timedelta(minutes=2), "103"),
            candle("ETHUSDT", start, "201"),
        ]
    )
    repository.save_runtime_status(
        RuntimeStatusInput(
            symbol="BTCUSDT",
            interval="1m",
            status=RuntimeStatus.LIVE,
            last_event_at=start + timedelta(minutes=2),
            last_candle_open_time=start + timedelta(minutes=2),
            lag_seconds=5,
        )
    )
    repository.save_runtime_status(
        RuntimeStatusInput(
            symbol="ETHUSDT",
            interval="1m",
            status=RuntimeStatus.DEGRADED,
            last_event_at=start,
            last_candle_open_time=start + timedelta(minutes=1),
            lag_seconds=60,
        )
    )
    job = repository.create_backfill_job(
        BackfillJobInput(
            job_type=BackfillJobType.INITIAL,
            symbol="BTCUSDT",
            interval="1m",
            status=BackfillJobStatus.SUCCEEDED,
            range_start=start,
            range_end=start + timedelta(minutes=2),
            requested_candle_count=3,
            inserted_candle_count=3,
        )
    )
    repository.append_application_event(
        ApplicationEventInput(
            severity=EventSeverity.INFO,
            event_type=ApplicationEventType.INITIAL_BACKFILL_COMPLETED.value,
            message="done",
            event_time=start + timedelta(minutes=3),
            symbol="BTCUSDT",
            interval="1m",
            backfill_job_id=job.id,
            metadata_json={"stored_candle_count": 3},
        )
    )
    session.commit()


def test_api_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["symbols"] == ["BTCUSDT", "ETHUSDT"]


def test_dashboard_summary_response(
    client: TestClient,
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    seed_dashboard_data(repository, session)

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["system_status"] == "DEGRADED"
    assert payload["active_gap_count"] >= 1
    assert {symbol["symbol"] for symbol in payload["symbols"]} == {"BTCUSDT", "ETHUSDT"}


def test_symbol_status_response(
    client: TestClient,
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    seed_dashboard_data(repository, session)

    response = client.get("/api/dashboard/symbols")

    assert response.status_code == 200
    btc = next(item for item in response.json() if item["symbol"] == "BTCUSDT")
    assert btc["status"] == "LIVE"
    assert btc["latest_price"] == "103.00000000"
    assert btc["last_event_at"].endswith("Z") or "+00:00" in btc["last_event_at"]


def test_candles_query_and_validation(
    client: TestClient,
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    seed_dashboard_data(repository, session)

    response = client.get("/api/dashboard/candles?symbol=BTCUSDT&interval=1m&limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTCUSDT"
    assert len(payload["candles"]) == 2
    assert client.get("/api/dashboard/candles?symbol=BNBUSDT").status_code == 422
    assert client.get("/api/dashboard/candles?symbol=BTCUSDT&interval=5m").status_code == 422
    assert client.get("/api/dashboard/candles?symbol=BTCUSDT&limit=0").status_code == 422


def test_gap_list(
    client: TestClient,
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    seed_dashboard_data(repository, session)

    response = client.get("/api/dashboard/gaps?symbol=BTCUSDT")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_missing_candle_count"] == 1
    assert payload["gaps"][0]["start_time"].startswith("2026-07-14T00:01:00")


def test_backfill_job_list(
    client: TestClient,
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    seed_dashboard_data(repository, session)

    response = client.get("/api/dashboard/backfill-jobs")

    assert response.status_code == 200
    assert response.json()["jobs"][0]["job_type"] == "initial"


def test_event_list(
    client: TestClient,
    repository: SqlAlchemyMarketDataRepository,
    session: Session,
) -> None:
    seed_dashboard_data(repository, session)

    response = client.get("/api/dashboard/events")

    assert response.status_code == 200
    assert response.json()["events"][0]["event_type"] == "initial_backfill_completed"


def test_empty_database_returns_meaningful_empty_responses(client: TestClient) -> None:
    summary_response = client.get("/api/dashboard/summary")

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary == {
        "system_status": "INITIALIZING",
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "interval": "1m",
                "status": "INITIALIZING",
                "last_event_at": None,
                "last_candle_open_time": None,
                "freshness_seconds": None,
                "lag_seconds": None,
                "latest_price": None,
            },
            {
                "symbol": "ETHUSDT",
                "interval": "1m",
                "status": "INITIALIZING",
                "last_event_at": None,
                "last_candle_open_time": None,
                "freshness_seconds": None,
                "lag_seconds": None,
                "latest_price": None,
            },
        ],
        "total_missing_candle_count": 0,
        "active_gap_count": 0,
        "recent_backfill_job_count": 0,
        "recent_event_count": 0,
    }
    assert client.get("/api/dashboard/candles?symbol=BTCUSDT").json()["candles"] == []
    assert client.get("/api/dashboard/gaps").json()["gaps"] == []
    assert client.get("/api/dashboard/backfill-jobs").json()["jobs"] == []
    assert client.get("/api/dashboard/events").json()["events"] == []


def test_dashboard_summary_treats_none_repository_results_as_empty() -> None:
    service = DashboardQueryService(
        cast(Any, EmptyBoundaryRepository()),
        DashboardQueryConfig(symbols=["BTCUSDT", "ETHUSDT"], interval="1m"),
    )

    summary = service.summary()

    assert summary.system_status == "INITIALIZING"
    assert [symbol.status for symbol in summary.symbols] == ["INITIALIZING", "INITIALIZING"]
    assert summary.total_missing_candle_count == 0
    assert summary.active_gap_count == 0
    assert summary.recent_backfill_job_count == 0
    assert summary.recent_event_count == 0
