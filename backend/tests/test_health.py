from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import Settings, get_settings
from app.main import create_app


def test_health_endpoint_returns_backend_boot_status() -> None:
    client = TestClient(create_app(enable_runtime=False))

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


def test_settings_parse_comma_separated_cors_origins(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://binance-assignment.vercel.app, http://localhost:3000",
    )

    settings = Settings()

    assert settings.cors_origin_list == [
        "https://binance-assignment.vercel.app",
        "http://localhost:3000",
    ]


def test_settings_default_database_url_targets_localhost() -> None:
    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://binance:binance@localhost:5432/binance_assignment"
    )


def test_settings_normalize_railway_postgres_url(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@railway.internal:5432/railway",
    )

    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://user:password@railway.internal:5432/railway"
    )


def test_settings_ignore_cwd_root_env_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql://binance:binance@postgres:5432/binance_assignment\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://binance:binance@localhost:5432/binance_assignment"
    )


def test_settings_os_environment_overrides_env_file(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://binance:binance@postgres:5432/binance_assignment",
    )

    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://binance:binance@postgres:5432/binance_assignment"
    )


def test_cors_preflight_allows_configured_local_origin(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    get_settings.cache_clear()
    client = TestClient(create_app(enable_runtime=False))

    response = client.options(
        "/api/dashboard/stream",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Accept",
        },
    )

    get_settings.cache_clear()
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "OPTIONS" in response.headers["access-control-allow-methods"]


def test_cors_get_response_allows_configured_local_origin(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    get_settings.cache_clear()
    client = TestClient(create_app(enable_runtime=False))

    response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:3000"})

    get_settings.cache_clear()
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "access-control-allow-credentials" not in response.headers


def test_cors_get_response_does_not_allow_unconfigured_origin(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    get_settings.cache_clear()
    client = TestClient(create_app(enable_runtime=False))

    response = client.get("/api/health", headers={"Origin": "https://example.com"})

    get_settings.cache_clear()
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
