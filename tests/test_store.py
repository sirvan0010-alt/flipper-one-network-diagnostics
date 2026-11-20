import sqlite3

import pytest

from flipper_diag.models import DiagnosticResult, Finding
from flipper_diag.store import (
    DatabaseVersionError,
    initialize_database,
    list_baselines,
    list_results,
    load_baseline,
    save_baseline,
    save_result,
)


def test_initialize_and_save_result_round_trip(tmp_path):
    database = tmp_path / "data" / "results.sqlite3"
    result = DiagnosticResult(
        collector="fixture",
        status="warning",
        interface="eth0",
        data={"link": "up", "speed_mbps": 1000},
        findings=[
            Finding(
                code="DNS-001",
                severity="warning",
                title="DNS server not configured",
                recommendation="Check DHCP option 6.",
            )
        ],
    )

    run_id = save_result(database, result)
    stored = list_results(database)

    assert len(run_id) == 36
    assert len(stored) == 1
    assert stored[0]["run_id"] == run_id
    assert stored[0]["collector"] == "fixture"
    assert stored[0]["data"]["speed_mbps"] == 1000
    assert stored[0]["findings"][0]["code"] == "DNS-001"


def test_list_results_limit_is_bounded(tmp_path):
    database = tmp_path / "results.sqlite3"
    initialize_database(database)

    with pytest.raises(ValueError, match="between 1 and 500"):
        list_results(database, limit=0)


def test_newer_database_schema_is_rejected(tmp_path):
    database = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 99")
    connection.close()

    with pytest.raises(DatabaseVersionError):
        initialize_database(database)


def test_v1_database_migrates_to_v2_without_losing_runs(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(database)
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
        CREATE TABLE findings (
            finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL REFERENCES diagnostic_runs(run_id),
            code TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            recommendation TEXT NOT NULL
        );
        PRAGMA user_version = 1;
        """
    )
    connection.close()

    initialize_database(database)

    connection = sqlite3.connect(database)
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    connection.close()
    assert version == 2
    assert "diagnostic_runs" in tables
    assert "inventory_baselines" in tables


def test_save_and_load_named_baseline(tmp_path):
    database = tmp_path / "results.sqlite3"
    devices = [
        {
            "mac_address": "02:00:00:00:00:01",
            "addresses": ["192.0.2.10", "2001:db8::10"],
        }
    ]

    baseline_id = save_baseline(database, "office", devices)
    loaded = load_baseline(database, "office")

    assert loaded is not None
    assert loaded["baseline_id"] == baseline_id
    assert loaded["name"] == "office"
    assert loaded["devices"] == devices
    assert list_baselines(database)[0]["name"] == "office"


def test_baseline_rejects_empty_name_and_invalid_inventory(tmp_path):
    database = tmp_path / "results.sqlite3"

    with pytest.raises(ValueError, match="name"):
        save_baseline(database, "  ", [])
    with pytest.raises(ValueError, match="MAC address"):
        save_baseline(database, "bad", [{"addresses": []}])


def test_missing_baseline_returns_none(tmp_path):
    assert load_baseline(tmp_path / "results.sqlite3", "unknown") is None


def test_database_file_is_owner_only_on_posix(tmp_path):
    import os
    import stat

    if os.name != "posix":
        pytest.skip("POSIX file mode semantics are required")
    database = tmp_path / "private.sqlite3"
    initialize_database(database)

    mode = stat.S_IMODE(database.stat().st_mode)
    assert mode == 0o600
