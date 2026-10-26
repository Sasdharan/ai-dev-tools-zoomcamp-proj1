from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import text

from database import create_database_engine
from settings import get_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_get_database_url_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    assert get_database_url() == "sqlite:///:memory:"


@pytest.mark.unit
def test_get_database_url_requires_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "")

    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        get_database_url()


@pytest.mark.integration
@pytest.mark.smoke
def test_sqlite_engine_can_connect() -> None:
    database_engine = create_database_engine("sqlite:///:memory:")
    try:
        with database_engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        database_engine.dispose()


@pytest.mark.unit
def test_postgresql_url_selects_psycopg_driver() -> None:
    database_engine = create_database_engine(
        "postgresql+psycopg2://user:password@localhost:5432/expense_tracker"
    )
    try:
        assert database_engine.url.drivername == "postgresql+psycopg2"
    finally:
        database_engine.dispose()


@pytest.mark.unit
def test_alembic_config_points_to_root_migrations() -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))

    assert Path(config.get_main_option("script_location")).resolve() == (
        PROJECT_ROOT / "migrations"
    )
