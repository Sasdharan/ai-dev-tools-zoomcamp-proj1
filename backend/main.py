from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Transaction


class TransactionInput(BaseModel):
    date: datetime
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    merchant: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)


class TransactionResponse(TransactionInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


app = FastAPI(title="Personal Expense Tracker API")


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
