import sqlite3
from pathlib import Path

from blackbox.store.db import migrate_database


def test_schema_v2_migration_is_backed_up_and_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "blackbox.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE task (task_id TEXT PRIMARY KEY, question TEXT NOT NULL)"
        )
        connection.execute(
            'CREATE TABLE "run" (run_id TEXT PRIMARY KEY, task_id TEXT NOT NULL)'
        )
        connection.execute("INSERT INTO task VALUES ('task-1', 'Question?')")
        connection.execute('INSERT INTO "run" VALUES (\'run-1\', \'task-1\')')
        connection.commit()

    changes, backup_path = migrate_database(db_path)

    assert backup_path is not None and backup_path.exists()
    assert "added task.workspace" in changes
    assert "added run.incident_id" in changes
    with sqlite3.connect(db_path) as connection:
        assert connection.execute(
            "SELECT workspace FROM task WHERE task_id = 'task-1'"
        ).fetchone() == ("hotpot",)
        assert connection.execute(
            'SELECT workspace FROM "run" WHERE run_id = \'run-1\''
        ).fetchone() == ("hotpot",)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "incident",
        "incident_event",
        "recipient",
        "notification_rule",
        "notification_log",
    } <= tables

    second_changes, second_backup = migrate_database(db_path)

    assert second_changes == []
    assert second_backup is None