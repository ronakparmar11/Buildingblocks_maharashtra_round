from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from blackbox.config import get_settings


def _create_engine() -> Engine:
    db_path = Path(get_settings().DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )


engine = _create_engine()


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: SQLite3Connection, _: object) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_db() -> None:
    from blackbox.store import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
