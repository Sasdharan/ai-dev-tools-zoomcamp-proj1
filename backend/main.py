import csv
import io
import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine, get_db
from models import Transaction
from telemetry import configure_telemetry


class TransactionInput(BaseModel):
    date: datetime
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    merchant: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)


class TransactionResponse(TransactionInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CategorySpending(BaseModel):
    category: str
    spending: Decimal
    count: int


class MonthlyTotals(BaseModel):
    month: str
    income: Decimal
    spending: Decimal


class TransactionSummaryResponse(BaseModel):
    transaction_count: int
    total_income: Decimal
    total_spending: Decimal
    net: Decimal
    by_category: list[CategorySpending]
    by_month: list[MonthlyTotals]


class ImportRowError(BaseModel):
    row_number: int
    errors: list[str]


class ImportTransactionsResponse(BaseModel):
    imported: int
    rejected: list[ImportRowError]


CSV_FIELD_ALIASES = {
    "date": {"date", "transactiondate", "posteddate"},
    "amount": {"amount", "transactionamount"},
    "merchant": {"merchant", "description", "payee"},
    "category": {"category", "expensecategory"},
}


def _normalize_csv_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.casefold())


def _map_csv_headers(headers: list[str]) -> dict[str, str]:
    mapped_headers: dict[str, str] = {}
    for header in headers:
        normalized_header = _normalize_csv_header(header)
        for field, aliases in CSV_FIELD_ALIASES.items():
            if normalized_header not in aliases:
                continue
            if field in mapped_headers:
                raise HTTPException(
                    status_code=422,
                    detail=f"Multiple CSV columns map to {field}",
                )
            mapped_headers[field] = header

    missing_fields = set(CSV_FIELD_ALIASES) - mapped_headers.keys()
    if missing_fields:
        missing_headers = ", ".join(sorted(missing_fields))
        raise HTTPException(
            status_code=422,
            detail=f"CSV is missing required columns: {missing_headers}",
        )
    return mapped_headers


app = FastAPI(title="Personal Expense Tracker API")
configure_telemetry(app, engine)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/v1/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    transaction_input: TransactionInput,
    database_session: Annotated[Session, Depends(get_db)],
) -> Transaction:
    transaction = Transaction(**transaction_input.model_dump())
    database_session.add(transaction)
    database_session.commit()
    database_session.refresh(transaction)
    return transaction


@app.get("/api/v1/transactions", response_model=list[TransactionResponse])
def list_transactions(
    database_session: Annotated[Session, Depends(get_db)],
) -> list[Transaction]:
    statement = select(Transaction).order_by(Transaction.id)
    return list(database_session.scalars(statement).all())


@app.get(
    "/api/v1/transactions/summary",
    response_model=TransactionSummaryResponse,
)
def summarize_transactions(
    database_session: Annotated[Session, Depends(get_db)],
) -> TransactionSummaryResponse:
    # A category whose amounts net to a positive value is treated as income
    # (e.g. Salary). Every other category is spending, so positive amounts in
    # it (refunds, cashback) reduce that category's spending instead of
    # counting as income.
    zero = Decimal("0.00")
    statement = select(
        Transaction.date, Transaction.amount, Transaction.category
    ).order_by(Transaction.date)
    rows = database_session.execute(statement).all()

    category_net: dict[str, Decimal] = {}
    category_count: dict[str, int] = {}
    for _, amount, category in rows:
        category_net[category] = category_net.get(category, zero) + amount
        category_count[category] = category_count.get(category, 0) + 1
    income_categories = {category for category, net in category_net.items() if net > 0}

    month_income: dict[str, Decimal] = {}
    month_spending: dict[str, Decimal] = {}
    for transaction_date, amount, category in rows:
        month_key = transaction_date.strftime("%Y-%m")
        month_income.setdefault(month_key, zero)
        month_spending.setdefault(month_key, zero)
        if category in income_categories:
            month_income[month_key] += amount
        else:
            month_spending[month_key] -= amount

    total_income = zero
    total_spending = zero
    by_category: list[CategorySpending] = []
    for category, net in category_net.items():
        if category in income_categories:
            total_income += net
        elif net < 0:
            spending = zero - net
            total_spending += spending
            by_category.append(
                CategorySpending(
                    category=category,
                    spending=spending,
                    count=category_count[category],
                )
            )

    return TransactionSummaryResponse(
        transaction_count=len(rows),
        total_income=total_income,
        total_spending=total_spending,
        net=total_income - total_spending,
        by_category=sorted(
            by_category,
            key=lambda item: (-item.spending, item.category.casefold()),
        ),
        by_month=[
            MonthlyTotals(
                month=month_key,
                income=max(zero, month_income[month_key]),
                spending=max(zero, month_spending[month_key]),
            )
            for month_key in sorted(month_income)
        ],
    )


@app.get("/api/v1/transactions/export")
def export_transactions(
    database_session: Annotated[Session, Depends(get_db)],
) -> Response:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("Date", "Amount", "Merchant", "Category"))

    statement = select(Transaction).order_by(Transaction.id)
    for transaction in database_session.scalars(statement):
        writer.writerow(
            (
                transaction.date.isoformat(sep=" "),
                str(transaction.amount),
                transaction.merchant,
                transaction.category,
            )
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@app.post(
    "/api/v1/transactions/import",
    response_model=ImportTransactionsResponse,
)
async def import_transactions(
    file: Annotated[UploadFile, File()],
    database_session: Annotated[Session, Depends(get_db)],
) -> ImportTransactionsResponse:
    file_content = await file.read()
    if not file_content.strip():
        raise HTTPException(status_code=422, detail="CSV file is empty")

    try:
        csv_content = file_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=422,
            detail="CSV file must use UTF-8 encoding",
        ) from error

    reader = csv.DictReader(io.StringIO(csv_content, newline=""), strict=True)
    try:
        headers = reader.fieldnames
        if not headers:
            raise HTTPException(status_code=422, detail="CSV file has no header row")
        mapped_headers = _map_csv_headers(headers)

        valid_transactions: list[TransactionInput] = []
        rejected_rows: list[ImportRowError] = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                rejected_rows.append(
                    ImportRowError(
                        row_number=row_number,
                        errors=["Row has more values than the header columns"],
                    )
                )
                continue

            transaction_data = {
                field: (row.get(header) or "").strip()
                for field, header in mapped_headers.items()
            }
            try:
                valid_transactions.append(
                    TransactionInput.model_validate(transaction_data)
                )
            except ValidationError as error:
                rejected_rows.append(
                    ImportRowError(
                        row_number=row_number,
                        errors=[
                            f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}"
                            for issue in error.errors()
                        ],
                    )
                )
    except csv.Error as error:
        raise HTTPException(
            status_code=422,
            detail=f"Malformed CSV file: {error}",
        ) from error

    if valid_transactions:
        database_session.add_all(
            Transaction(**transaction.model_dump())
            for transaction in valid_transactions
        )
        database_session.commit()

    return ImportTransactionsResponse(
        imported=len(valid_transactions),
        rejected=rejected_rows,
    )


@app.put(
    "/api/v1/transactions/{transaction_id}",
    response_model=TransactionResponse,
)
def update_transaction(
    transaction_id: int,
    transaction_input: TransactionInput,
    database_session: Annotated[Session, Depends(get_db)],
) -> Transaction:
    transaction = database_session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for field, value in transaction_input.model_dump().items():
        setattr(transaction, field, value)

    database_session.commit()
    database_session.refresh(transaction)
    return transaction


@app.delete(
    "/api/v1/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_transaction(
    transaction_id: int,
    database_session: Annotated[Session, Depends(get_db)],
) -> Response:
    transaction = database_session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    database_session.delete(transaction)
    database_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
