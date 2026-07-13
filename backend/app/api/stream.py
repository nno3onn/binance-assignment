from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.dashboard import query_service
from app.api.dependencies import get_repository
from app.config import Settings, get_settings
from app.repositories.interfaces import MarketDataRepository
from app.services.stream import DashboardSseService

router = APIRouter()


@router.get(
    "/api/dashboard/stream",
    tags=["dashboard"],
    summary="Stream realtime dashboard snapshots and heartbeats over SSE",
)
def dashboard_stream(
    request: Request,
    repository: Annotated[MarketDataRepository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    service = DashboardSseService(
        query_service(repository, settings),
        interval_seconds=settings.dashboard_sse_interval_seconds,
        heartbeat_seconds=settings.dashboard_sse_heartbeat_seconds,
    )
    return StreamingResponse(
        service.stream(is_disconnected=request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
