from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard import router as dashboard_router
from app.api.stream import router as stream_router
from app.config import get_settings
from app.database import SessionLocal
from app.services.runtime import MarketDataRuntime

RuntimeFactory = Callable[[], MarketDataRuntime]


def build_runtime() -> MarketDataRuntime:
    return MarketDataRuntime(settings=get_settings(), session_factory=SessionLocal)


def create_app(
    *,
    enable_runtime: bool = True,
    runtime_factory: RuntimeFactory = build_runtime,
) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runtime: MarketDataRuntime | None = None
        if enable_runtime:
            runtime = runtime_factory()
            app.state.market_data_runtime = runtime
            await runtime.start()
        try:
            yield
        finally:
            if runtime is not None:
                await runtime.stop()

    app = FastAPI(
        title="Binance Market Data Operations API",
        version="0.1.0",
        lifespan=lifespan,
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
