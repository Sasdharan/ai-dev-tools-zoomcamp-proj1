from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from models import Transaction

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
@pytest.mark.smoke
def test_transaction_model_defines_csv_fields() -> None:
    transaction = Transaction(
        date=datetime(2025, 1, 1, 14, 22, 10),
        amount=Decimal("-45.50"),
        merchant="Supermarket",
        category="Groceries",
    )

    assert transaction.date == datetime(2025, 1, 1, 14, 22, 10)
    assert transaction.amount == Decimal("-45.50")
    assert transaction.merchant == "Supermarket"
    assert transaction.category == "Groceries"


@pytest.mark.integration
def test_migration_creates_transaction_table(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))

    command.upgrade(config, "head")

    database_engine = create_engine(database_url)
    try:
        columns = {
            column["name"]
            for column in inspect(database_engine).get_columns("transactions")
        }
    finally:
        database_engine.dispose()

    assert columns == {"id", "date", "amount", "merchant", "category"}
