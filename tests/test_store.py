from flipper_diag.models import DiagnosticResult, Finding
from flipper_diag.store import (
    DatabaseVersionError,
    initialize_database,
    list_results,
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

    try:
        list_results(database, limit=0)
    except ValueError as exc:
        assert "between 1 and 500" in str(exc)
    else:
        raise AssertionError("invalid limit must fail")


def test_newer_database_schema_is_rejected(tmp_path):
    import sqlite3

    database = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 99")
    connection.close()

    try:
        initialize_database(database)
    except DatabaseVersionError:
        pass
    else:
        raise AssertionError("newer schema must not be silently modified")
