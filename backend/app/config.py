from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="info", validation_alias="LOG_LEVEL")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias="CORS_ORIGINS",
    )
    symbols: str = Field(default="BTCUSDT,ETHUSDT", validation_alias="SYMBOLS")
    candle_interval: Literal["1m"] = Field(default="1m", validation_alias="CANDLE_INTERVAL")
    initial_backfill_hours: int = Field(default=24, ge=1, validation_alias="INITIAL_BACKFILL_HOURS")
    binance_rest_base_url: str = Field(
        default="https://api.binance.com",
        validation_alias="BINANCE_REST_BASE_URL",
    )
    binance_rest_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        validation_alias="BINANCE_REST_TIMEOUT_SECONDS",
    )
    binance_rest_retry_count: int = Field(
        default=3,
        ge=0,
        validation_alias="BINANCE_REST_RETRY_COUNT",
    )
    binance_ws_base_url: str = Field(
        default="wss://stream.binance.com:9443",
        validation_alias="BINANCE_WS_BASE_URL",
    )
    binance_ws_keepalive_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias="BINANCE_WS_KEEPALIVE_SECONDS",
    )
    binance_ws_retry_count: int = Field(
        default=3,
        ge=0,
        validation_alias="BINANCE_WS_RETRY_COUNT",
    )
    dashboard_sse_interval_seconds: float = Field(
        default=5.0,
        gt=0,
        validation_alias="DASHBOARD_SSE_INTERVAL_SECONDS",
    )
    dashboard_sse_heartbeat_seconds: float = Field(
        default=15.0,
        gt=0,
        validation_alias="DASHBOARD_SSE_HEARTBEAT_SECONDS",
    )
    database_url: str = Field(
        default="postgresql+psycopg://binance:binance@localhost:5432/binance_assignment",
        validation_alias="DATABASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def symbol_list(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.symbols.split(",") if symbol.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("database_url")
    @classmethod
    def normalize_postgres_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
