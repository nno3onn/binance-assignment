from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import Settings
from app.main import create_app


def test_health_endpoint_returns_backend_boot_status() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": "local",
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "interval": "1m",
        "initial_backfill_hours": 24,
    }


def test_settings_parse_comma_separated_symbols(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SYMBOLS", "btcusdt, ethusdt")
    monkeypatch.setenv("INITIAL_BACKFILL_HOURS", "12")

    settings = Settings()

    assert settings.symbol_list == ["BTCUSDT", "ETHUSDT"]
    assert settings.initial_backfill_hours == 12
