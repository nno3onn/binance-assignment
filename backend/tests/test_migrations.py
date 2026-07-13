from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def table_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migration_upgrade_creates_required_tables(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'upgrade.db'}"

    command.upgrade(alembic_config(database_url), "head")

    assert {
        "candles",
        "symbol_runtime_status",
        "backfill_jobs",
        "application_events",
    }.issubset(table_names(database_url))


def test_migration_downgrade_removes_required_tables(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'downgrade.db'}"
    config = alembic_config(database_url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    assert "candles" not in table_names(database_url)
    assert "symbol_runtime_status" not in table_names(database_url)
    assert "backfill_jobs" not in table_names(database_url)
    assert "application_events" not in table_names(database_url)


def test_migration_upgrade_can_be_reexecuted_at_head(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'reexecute.db'}"
    config = alembic_config(database_url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    assert "candles" in table_names(database_url)


def test_candles_schema_has_unique_key_indexes_and_source_constraint(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'schema.db'}"
    command.upgrade(alembic_config(database_url), "head")
    engine = create_engine(database_url)

    try:
        inspector = inspect(engine)
        unique_constraints = inspector.get_unique_constraints("candles")
        indexes = inspector.get_indexes("candles")
        checks = inspector.get_check_constraints("candles")
    finally:
        engine.dispose()

    assert any(
        constraint["name"] == "uq_candles_symbol_interval_open_time"
        and constraint["column_names"] == ["symbol", "interval", "open_time"]
        for constraint in unique_constraints
    )
    assert any(index["name"] == "ix_candles_symbol_interval_open_time" for index in indexes)
    assert any(
        check["name"] == "ck_candles_source"
        and "websocket" in check["sqltext"]
        and "rest_backfill" in check["sqltext"]
        for check in checks
    )
