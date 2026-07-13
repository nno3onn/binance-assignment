from fastapi import FastAPI

from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Binance Market Data Operations API",
        version="0.1.0",
    )

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
