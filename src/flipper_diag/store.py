"""Local SQLite persistence for normalized diagnostic results and baselines."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .baseline import compare_device_inventory
from .models import DiagnosticResult

SCHEMA_VERSION = 2
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
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        pass
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: str | Path) -> None:
    """Create or migrate the local database in one atomic schema transaction."""
    connection = _connect(path)
    try:
        # Serialize concurrent first-run/migration attempts before reading user_version.
        connection.execute("BEGIN IMMEDIATE")
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise DatabaseVersionError(
                f"Database schema {version} is newer than supported {SCHEMA_VERSION}."
            )

        if version == 0:
            connection.execute(
                """
                CREATE TABLE diagnostic_runs (
                    run_id TEXT PRIMARY KEY,
                    collector TEXT NOT NULL,
                    status TEXT NOT NULL,
                    interface TEXT,
                    schema_version INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX idx_diagnostic_runs_started_at
                ON diagnostic_runs(started_at DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE findings (
                    finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES diagnostic_runs(run_id)
                        ON DELETE CASCADE,
                    code TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    recommendation TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX idx_findings_code ON findings(code)")
            connection.execute("PRAGMA user_version = 1")
            version = 1

        if version == 1:
            connection.execute(
                """
                CREATE TABLE inventory_baselines (
                    baseline_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    inventory_json TEXT NOT NULL
                )
                """
            )
            connection.execute("PRAGMA user_version = 2")

        connection.commit()
    except Exception:
        connection.rollback()
        raise
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


def save_baseline(
    path: str | Path, name: str, devices: list[dict[str, Any]]
) -> str:
    """Save a named device inventory snapshot after validating its structure."""
    if not name.strip():
        raise ValueError("baseline name must not be empty")
    snapshot = list(devices)
    compare_device_inventory(snapshot, snapshot)
    baseline_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    initialize_database(path)
    connection = _connect(path)
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO inventory_baselines
                    (baseline_id, name, created_at, inventory_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    baseline_id,
                    name.strip(),
                    created_at,
                    json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
                ),
            )
    finally:
        connection.close()
    return baseline_id


def load_baseline(path: str | Path, name: str) -> dict[str, Any] | None:
    """Load a named inventory baseline, or return None when it does not exist."""
    initialize_database(path)
    connection = _connect(path)
    try:
        row = connection.execute(
            """
            SELECT baseline_id, name, created_at, inventory_json
            FROM inventory_baselines
            WHERE name = ?
            """,
            (name,),
        ).fetchone()
        if row is None:
            return None
        return {
            "baseline_id": row["baseline_id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "devices": json.loads(row["inventory_json"]),
        }
    finally:
        connection.close()


def list_baselines(path: str | Path) -> list[dict[str, str]]:
    """List baseline names and creation times without loading their full inventories."""
    initialize_database(path)
    connection = _connect(path)
    try:
        rows = connection.execute(
            """
            SELECT baseline_id, name, created_at
            FROM inventory_baselines
            ORDER BY created_at DESC, rowid DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
