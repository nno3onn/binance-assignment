from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_repository
from app.api.schemas import (
    BackfillJobsResponse,
    CandlesResponse,
    DashboardSummaryResponse,
    EventsResponse,
    GapsResponse,
    HealthResponse,
    SymbolStatusResponse,
)
from app.config import Settings, get_settings
from app.repositories.interfaces import MarketDataRepository
from app.services.dashboard import DashboardQueryConfig, DashboardQueryService

router = APIRouter()


def validate_symbol(symbol: str | None, settings: Settings) -> str | None:
    if symbol is None:
        return None
    normalized = symbol.upper()
    if normalized not in settings.symbol_list:
        raise HTTPException(status_code=422, detail="Unsupported symbol")
    return normalized


def validate_interval(interval: str, settings: Settings) -> str:
    if interval != settings.candle_interval:
        raise HTTPException(status_code=422, detail="Unsupported interval")
    return interval


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def query_service(
    repository: MarketDataRepository,
    settings: Settings,
) -> DashboardQueryService:
    return DashboardQueryService(
        repository,
        DashboardQueryConfig(symbols=settings.symbol_list, interval=settings.candle_interval),
    )


@router.get(
    "/api/health",
    tags=["dashboard"],
    response_model=HealthResponse,
    summary="Read API health and configured market data scope",
)
def api_health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        symbols=settings.symbol_list,
        interval=settings.candle_interval,
        initial_backfill_hours=settings.initial_backfill_hours,
    )


@router.get(
    "/api/dashboard/summary",
    tags=["dashboard"],
    response_model=DashboardSummaryResponse,
    summary="Read operations dashboard summary",
)
def dashboard_summary(
    repository: Annotated[MarketDataRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DashboardSummaryResponse:
    return query_service(repository, settings).summary()


@router.get(
    "/api/dashboard/symbols",
    tags=["dashboard"],
    response_model=list[SymbolStatusResponse],
    summary="Read per-symbol pipeline status",
)
def dashboard_symbols(
    repository: Annotated[MarketDataRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[SymbolStatusResponse]:
    return query_service(repository, settings).symbols()


@router.get(
    "/api/dashboard/candles",
    tags=["dashboard"],
    response_model=CandlesResponse,
    summary="Read recent or ranged candles for one symbol",
)
def dashboard_candles(
    repository: Annotated[MarketDataRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    symbol: Annotated[str, Query(description="Configured symbol such as BTCUSDT")],
    interval: Annotated[str, Query(description="Candle interval")] = "1m",
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Maximum number of records to return"),
    ] = 100,
    start: Annotated[datetime | None, Query(description="UTC range start")] = None,
    end: Annotated[datetime | None, Query(description="UTC range end")] = None,
) -> CandlesResponse:
    normalized_symbol = validate_symbol(symbol, settings)
    validated_interval = validate_interval(interval, settings)
    start = normalize_datetime(start)
    end = normalize_datetime(end)
    if (start is None) != (end is None):
        raise HTTPException(status_code=422, detail="start and end must be provided together")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="start must be before or equal to end")
    candles = query_service(repository, settings).candles(
        symbol=normalized_symbol or symbol.upper(),
        limit=limit,
        start=start,
        end=end,
    )
    return CandlesResponse(
        symbol=normalized_symbol or symbol.upper(), interval=validated_interval, candles=candles
    )


@router.get(
    "/api/dashboard/gaps",
    tags=["dashboard"],
    response_model=GapsResponse,
    summary="Read currently detected missing candle gaps",
)
def dashboard_gaps(
    repository: Annotated[MarketDataRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    symbol: Annotated[str | None, Query(description="Optional configured symbol")] = None,
    interval: Annotated[str, Query(description="Candle interval")] = "1m",
    start: Annotated[datetime | None, Query(description="UTC scan start")] = None,
    end: Annotated[datetime | None, Query(description="UTC scan end")] = None,
) -> GapsResponse:
    normalized_symbol = validate_symbol(symbol, settings)
    validate_interval(interval, settings)
    start = normalize_datetime(start)
    end = normalize_datetime(end)
    if (start is None) != (end is None):
        raise HTTPException(status_code=422, detail="start and end must be provided together")
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="start must be before or equal to end")
    return query_service(repository, settings).gaps(symbol=normalized_symbol, start=start, end=end)


@router.get(
    "/api/dashboard/backfill-jobs",
    tags=["dashboard"],
    response_model=BackfillJobsResponse,
    summary="Read recent initial and recovery backfill jobs",
)
def dashboard_backfill_jobs(
    repository: Annotated[MarketDataRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Maximum number of records to return"),
    ] = 100,
) -> BackfillJobsResponse:
    return BackfillJobsResponse(jobs=query_service(repository, settings).backfill_jobs(limit))


@router.get(
    "/api/dashboard/events",
    tags=["dashboard"],
    response_model=EventsResponse,
    summary="Read recent operational application events",
)
def dashboard_events(
    repository: Annotated[MarketDataRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Maximum number of records to return"),
    ] = 100,
) -> EventsResponse:
    return EventsResponse(events=query_service(repository, settings).events(limit))
