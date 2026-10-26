import csv
import io
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


@pytest.mark.smoke
def test_app_generates_openapi_schema() -> None:
    schema = app.openapi()

    assert schema["info"]["title"] == "Personal Expense Tracker API"
    assert "/health" in schema["paths"]
    assert "/api/v1/transactions" in schema["paths"]
    assert "/api/v1/transactions/export" in schema["paths"]
    assert "/api/v1/transactions/import" in schema["paths"]
    assert "/api/v1/transactions/summary" in schema["paths"]


@pytest.mark.smoke
def test_health_check_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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


def test_export_transactions_returns_documented_csv_and_escapes_values(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/transactions",
        json={
            "date": "2025-01-01T14:22:10",
            "amount": "-45.50",
            "merchant": 'Market, "Main"\nLocation',
            "category": "Food",
        },
    )

    response = client.get("/api/v1/transactions/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="transactions.csv"'
    )
    rows = list(csv.reader(io.StringIO(response.text, newline="")))
    assert rows == [
        ["Date", "Amount", "Merchant", "Category"],
        ["2025-01-01 14:22:10", "-45.50", 'Market, "Main"\nLocation', "Food"],
    ]


def test_export_transactions_with_no_saved_transactions_returns_header_only_csv(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/transactions/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.text == "Date,Amount,Merchant,Category\r\n"


def test_summarize_transactions_with_no_saved_transactions(client: TestClient) -> None:
    response = client.get("/api/v1/transactions/summary")

    assert response.status_code == 200
    assert response.json() == {
        "transaction_count": 0,
        "total_income": "0.00",
        "total_spending": "0.00",
        "net": "0.00",
        "by_category": [],
        "by_month": [],
    }


def test_summarize_transactions_groups_spending_and_income(client: TestClient) -> None:
    for date, amount, merchant, category in (
        ("2025-01-03T09:00:00", "-45.50", "Supermarket", "Groceries"),
        ("2025-01-15T12:00:00", "-12.25", "Cafe", "Dining"),
        ("2025-01-31T18:00:00", "2500.00", "Employer", "Salary"),
        ("2025-02-02T10:00:00", "-30.00", "Market", "Groceries"),
    ):
        client.post(
            "/api/v1/transactions",
            json={
                "date": date,
                "amount": amount,
                "merchant": merchant,
                "category": category,
            },
        )

    response = client.get("/api/v1/transactions/summary")

    assert response.status_code == 200
    assert response.json() == {
        "transaction_count": 4,
        "total_income": "2500.00",
        "total_spending": "87.75",
        "net": "2412.25",
        "by_category": [
            {"category": "Groceries", "spending": "75.50", "count": 2},
            {"category": "Dining", "spending": "12.25", "count": 1},
        ],
        "by_month": [
            {"month": "2025-01", "income": "2500.00", "spending": "57.75"},
            {"month": "2025-02", "income": "0.00", "spending": "30.00"},
        ],
    }


def test_summarize_transactions_nets_refunds_against_spending_categories(
    client: TestClient,
) -> None:
    for date, amount, merchant, category in (
        ("2025-01-02T10:00:00", "-100.00", "Electronics Store", "Shopping"),
        ("2025-01-10T10:00:00", "-40.00", "Supermarket", "Groceries"),
        ("2025-01-31T09:00:00", "2000.00", "Employer", "Salary"),
        ("2025-02-05T10:00:00", "30.00", "Electronics Store", "Shopping"),
        ("2025-02-06T10:00:00", "40.00", "Supermarket", "Groceries"),
    ):
        client.post(
            "/api/v1/transactions",
            json={
                "date": date,
                "amount": amount,
                "merchant": merchant,
                "category": category,
            },
        )

    response = client.get("/api/v1/transactions/summary")

    assert response.status_code == 200
    assert response.json() == {
        "transaction_count": 5,
        "total_income": "2000.00",
        "total_spending": "70.00",
        "net": "1930.00",
        "by_category": [
            {"category": "Shopping", "spending": "70.00", "count": 2},
        ],
        "by_month": [
            {"month": "2025-01", "income": "2000.00", "spending": "140.00"},
            {"month": "2025-02", "income": "0.00", "spending": "0.00"},
        ],
    }


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


def test_import_transactions_maps_headers_and_ignores_extra_columns(
    client: TestClient,
) -> None:
    csv_content = (
        b"Transaction Date,Amount,Payee,Expense Category,Notes\n"
        b"2025-01-01 14:22:10,-45.50,Supermarket,Groceries,weekly shop\n"
        b"2025-01-03,1500.00,Employer,Salary,payday\n"
    )

    response = client.post(
        "/api/v1/transactions/import",
        files={"file": ("transactions.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {"imported": 2, "rejected": []}
    transactions = client.get("/api/v1/transactions").json()
    assert [transaction["merchant"] for transaction in transactions] == [
        "Supermarket",
        "Employer",
    ]


def test_import_transactions_keeps_valid_rows_and_reports_invalid_rows(
    client: TestClient,
) -> None:
    csv_content = (
        b"Date,Amount,Merchant,Category\n"
        b"2025-01-01,-45.50,Supermarket,Groceries\n"
        b"not-a-date,-12.00,City Transit,Transport\n"
        b"2025-01-05,1500.00,Employer,Salary\n"
    )

    response = client.post(
        "/api/v1/transactions/import",
        files={"file": ("transactions.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 2
    assert response.json()["rejected"][0]["row_number"] == 3
    assert response.json()["rejected"][0]["errors"]
    assert len(client.get("/api/v1/transactions").json()) == 2


def test_import_sample_history_csv_populates_summary(client: TestClient) -> None:
    sample_csv = PROJECT_ROOT / "sample-data" / "test_history.csv"

    response = client.post(
        "/api/v1/transactions/import",
        files={"file": (sample_csv.name, sample_csv.read_bytes(), "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {"imported": 4, "rejected": []}
    summary = client.get("/api/v1/transactions/summary").json()
    assert summary["transaction_count"] == 4
    assert summary["total_income"] == "1500.00"
    assert summary["total_spending"] == "64.30"
    assert [item["category"] for item in summary["by_category"]] == [
        "Groceries",
        "Transport",
        "Food & Drinks",
    ]


def test_import_detailed_bank_export_csv_maps_aliases_and_ignores_extra_columns(
    client: TestClient,
) -> None:
    sample_csv = PROJECT_ROOT / "sample-data" / "bank_export_detailed.csv"

    response = client.post(
        "/api/v1/transactions/import",
        files={"file": (sample_csv.name, sample_csv.read_bytes(), "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {"imported": 24, "rejected": []}
    transactions = client.get("/api/v1/transactions").json()
    assert len(transactions) == 24
    assert transactions[1] == {
        "id": 2,
        "date": "2025-03-02T18:20:45",
        "amount": "-82.35",
        "merchant": "Green Valley Market",
        "category": "Groceries",
    }
    assert set(transactions[0]) == {"id", "date", "amount", "merchant", "category"}

    summary = client.get("/api/v1/transactions/summary").json()
    assert summary["transaction_count"] == 24
    assert summary["total_income"] == "10050.00"
    assert summary["total_spending"] == "4225.76"
    assert summary["net"] == "5824.24"
    assert summary["by_category"][:2] == [
        {"category": "Rent", "spending": "3450.00", "count": 3},
        {"category": "Groceries", "spending": "237.65", "count": 4},
    ]
    assert len(summary["by_category"]) == 10
    assert summary["by_month"] == [
        {"month": "2025-03", "income": "3650.00", "spending": "1422.76"},
        {"month": "2025-04", "income": "3200.00", "spending": "1431.33"},
        {"month": "2025-05", "income": "3200.00", "spending": "1371.67"},
    ]


def test_import_header_only_csv_returns_empty_result(client: TestClient) -> None:
    response = client.post(
        "/api/v1/transactions/import",
        files={
            "file": (
                "transactions.csv",
                b"Date,Amount,Merchant,Category\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {"imported": 0, "rejected": []}
    assert client.get("/api/v1/transactions").json() == []


def test_import_rejects_empty_malformed_and_missing_header_files(
    client: TestClient,
) -> None:
    invalid_files = [
        b"",
        b'Date,Amount,Merchant,Category\n2025-01-01,1,Shop,Food\n"unterminated,1,Shop,Food\n',
        b"Date,Amount,Merchant\n2025-01-01,1,Shop\n",
    ]

    for file_content in invalid_files:
        response = client.post(
            "/api/v1/transactions/import",
            files={"file": ("transactions.csv", file_content, "text/csv")},
        )

        assert response.status_code == 422
        assert response.json()["detail"]
        assert client.get("/api/v1/transactions").json() == []
