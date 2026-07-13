from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="info", validation_alias="LOG_LEVEL")
    symbols: str = Field(default="BTCUSDT,ETHUSDT", validation_alias="SYMBOLS")
    candle_interval: Literal["1m"] = Field(default="1m", validation_alias="CANDLE_INTERVAL")
    initial_backfill_hours: int = Field(default=24, ge=1, validation_alias="INITIAL_BACKFILL_HOURS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def symbol_list(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.symbols.split(",") if symbol.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
