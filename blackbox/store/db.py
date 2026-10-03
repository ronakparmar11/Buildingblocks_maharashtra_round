import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from blackbox.config import get_settings


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _create_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    selected_url = database_url or settings.DATABASE_URL
    if selected_url:
        return create_engine(
            _normalize_database_url(selected_url),
            pool_pre_ping=True,
        )

    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )


engine = _create_engine()
_runtime_engine = engine


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: SQLite3Connection, _: object) -> None:
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_db() -> None:
    from blackbox.store import models  # noqa: F401

    settings = get_settings()
    if engine is _runtime_engine and settings.DATABASE_URL_UNPOOLED:
        schema_engine = _create_engine(settings.DATABASE_URL_UNPOOLED)
        try:
            SQLModel.metadata.create_all(schema_engine)
        finally:
            schema_engine.dispose()
        return

    SQLModel.metadata.create_all(engine)


def migrate_database(db_path: Path) -> tuple[list[str], Path | None]:
    """Upgrade a v1 SQLite database to schema v2 without removing data."""
    from blackbox.store import models  # noqa: F401

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        migration_engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(migration_engine)
        return ["created schema v2"], None

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        task_columns = (
            {row[1] for row in connection.execute("PRAGMA table_info(task)")}
            if "task" in tables
            else set()
        )
        run_columns = (
            {row[1] for row in connection.execute('PRAGMA table_info("run")')}
            if "run" in tables
            else set()
        )

    expected_tables = {
        "incident",
        "incident_event",
        "recipient",
        "notification_rule",
        "notification_log",
    }
    needs_migration = bool(
        expected_tables - tables
        or ({"workspace", "category"} - task_columns)
        or ({"workspace", "incident_id"} - run_columns)
    )
    if not needs_migration:
        return [], None

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = db_path.with_name(f"blackbox.backup-{timestamp}.db")
    shutil.copy2(db_path, backup_path)

    changes: list[str] = []
    with sqlite3.connect(db_path) as connection:
        if "task" in tables:
            if "workspace" not in task_columns:
                connection.execute(
                    "ALTER TABLE task ADD COLUMN workspace TEXT DEFAULT 'hotpot'"
                )
                changes.append("added task.workspace")
            if "category" not in task_columns:
                connection.execute("ALTER TABLE task ADD COLUMN category TEXT")
                changes.append("added task.category")
            connection.execute(
                "UPDATE task SET workspace = 'hotpot' WHERE workspace IS NULL"
            )
        if "run" in tables:
            if "workspace" not in run_columns:
                connection.execute(
                    'ALTER TABLE "run" ADD COLUMN workspace TEXT DEFAULT \'hotpot\''
                )
                changes.append("added run.workspace")
            if "incident_id" not in run_columns:
                connection.execute('ALTER TABLE "run" ADD COLUMN incident_id TEXT')
                changes.append("added run.incident_id")
            connection.execute(
                'UPDATE "run" SET workspace = \'hotpot\' WHERE workspace IS NULL'
            )
        connection.commit()

    migration_engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(migration_engine)
    created_tables = sorted(expected_tables - tables)
    changes.extend(f"created {table} table" for table in created_tables)
    return changes, backup_path


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
