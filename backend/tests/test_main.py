from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'api.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    database_engine = create_engine(database_url)
    test_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=database_engine,
    )

    def override_get_db():
        with test_session_factory() as database_session:
            yield database_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        database_engine.dispose()


def test_app_generates_openapi_schema() -> None:
    schema = app.openapi()

    assert schema["info"]["title"] == "Personal Expense Tracker API"
    assert "/api/v1/transactions" in schema["paths"]


def test_create_and_list_transactions(client: TestClient) -> None:
    response = client.get("/api/v1/transactions")
    assert response.status_code == 200
    assert response.json() == []

    response = client.post(
        "/api/v1/transactions",
        json={
            "date": "2025-01-01T14:22:10",
            "amount": "-45.50",
            "merchant": "Supermarket",
            "category": "Groceries",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "date": "2025-01-01T14:22:10",
        "amount": "-45.50",
        "merchant": "Supermarket",
        "category": "Groceries",
    }

    response = client.get("/api/v1/transactions")
    assert response.status_code == 200
    assert response.json()[0]["merchant"] == "Supermarket"


def test_create_transaction_rejects_invalid_input(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "date": "not-a-date",
            "amount": "1.234",
            "merchant": "",
            "category": "Groceries",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_update_and_delete_transaction(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/transactions",
        json={
            "date": "2025-01-01T14:22:10",
            "amount": "-45.50",
            "merchant": "Supermarket",
            "category": "Groceries",
        },
    )
    transaction_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/v1/transactions/{transaction_id}",
        json={
            "date": "2025-01-02T09:30:00",
            "amount": "-12.00",
            "merchant": "City Transit",
            "category": "Transport",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["merchant"] == "City Transit"
    assert update_response.json()["amount"] == "-12.00"

    delete_response = client.delete(f"/api/v1/transactions/{transaction_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert client.get("/api/v1/transactions").json() == []


def test_update_and_delete_missing_transaction_return_not_found(
    client: TestClient,
) -> None:
    transaction_input = {
        "date": "2025-01-02T09:30:00",
        "amount": "-12.00",
        "merchant": "City Transit",
        "category": "Transport",
    }

    update_response = client.put(
        "/api/v1/transactions/999",
        json=transaction_input,
    )
    delete_response = client.delete("/api/v1/transactions/999")

    assert update_response.status_code == 404
    assert update_response.json() == {"detail": "Transaction not found"}
    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "Transaction not found"}


def test_update_transaction_rejects_invalid_input(client: TestClient) -> None:
    response = client.put(
        "/api/v1/transactions/1",
        json={
            "date": "2025-01-02T09:30:00",
            "amount": "-12.345",
            "merchant": "City Transit",
            "category": "Transport",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]
