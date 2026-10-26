from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from settings import get_database_url


class Base(DeclarativeBase):
    pass


def create_database_engine(database_url: str | None = None) -> Engine:
    if database_url is None:
        database_url = get_database_url()

    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(database_url, connect_args=connect_args)


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
