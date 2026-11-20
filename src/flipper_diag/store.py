"""Local SQLite persistence for normalized diagnostic results."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .models import DiagnosticResult

SCHEMA_VERSION = 1
DEFAULT_DB_NAME = "results.sqlite3"


class DatabaseVersionError(RuntimeError):
    """Raised when the database was created by a newer incompatible version."""


def default_database_path() -> Path:
    """Return the per-user local data path without creating it."""
    return Path.home() / ".local" / "share" / "flipper-one-network-diagnostics" / DEFAULT_DB_NAME


def _connect(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: str | Path) -> None:
    """Create or migrate the local database to the current schema."""
    connection = _connect(path)
    try:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise DatabaseVersionError(
                f"Database schema {version} is newer than supported {SCHEMA_VERSION}."
            )
        if version == 0:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE diagnostic_runs (
                        run_id TEXT PRIMARY KEY,
                        collector TEXT NOT NULL,
                        status TEXT NOT NULL,
                        interface TEXT,
                        schema_version INTEGER NOT NULL,
                        started_at TEXT NOT NULL,
                        result_json TEXT NOT NULL
                    );

                    CREATE INDEX idx_diagnostic_runs_started_at
                        ON diagnostic_runs(started_at DESC);

                    CREATE TABLE findings (
                        finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT NOT NULL REFERENCES diagnostic_runs(run_id)
                            ON DELETE CASCADE,
                        code TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        title TEXT NOT NULL,
                        detail TEXT NOT NULL,
                        recommendation TEXT NOT NULL
                    );

                    CREATE INDEX idx_findings_code ON findings(code);
                    PRAGMA user_version = 1;
                    """
                )
    finally:
        connection.close()


def save_result(path: str | Path, result: DiagnosticResult) -> str:
    """Persist one complete result atomically and return its generated run ID."""
    initialize_database(path)
    payload = result.to_dict()
    run_id = str(uuid.uuid4())
    connection = _connect(path)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO diagnostic_runs
                    (run_id, collector, status, interface, schema_version, started_at, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result.collector,
                    result.status,
                    result.interface,
                    result.schema_version,
                    result.started_at,
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            connection.executemany(
                """
                INSERT INTO findings
                    (run_id, code, severity, title, detail, recommendation)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        item.code,
                        item.severity,
                        item.title,
                        item.detail,
                        item.recommendation,
                    )
                    for item in result.findings
                ],
            )
    finally:
        connection.close()
    return run_id


def list_results(path: str | Path, *, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent result envelopes, newest first."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    initialize_database(path)
    connection = _connect(path)
    try:
        rows = connection.execute(
            """
            SELECT run_id, result_json
            FROM diagnostic_runs
            ORDER BY started_at DESC, rowid DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {"run_id": row["run_id"], **json.loads(row["result_json"])}
            for row in rows
        ]
    finally:
        connection.close()
