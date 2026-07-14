from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard import router as dashboard_router
from app.api.stream import router as stream_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Binance Market Data Operations API",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Cache-Control", "Last-Event-ID"],
    )
    app.include_router(dashboard_router)
    app.include_router(stream_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "environment": settings.app_env,
            "symbols": settings.symbol_list,
            "interval": settings.candle_interval,
            "initial_backfill_hours": settings.initial_backfill_hours,
        }

    return app


app = create_app()
