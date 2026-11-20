import json
import sys

from flipper_diag import cli
from flipper_diag.models import DiagnosticResult


def test_history_command_initializes_empty_local_database(tmp_path, monkeypatch, capsys):
    database = tmp_path / "history.sqlite3"
    monkeypatch.setattr(
        sys,
        "argv",
        ["flipper-diag", "history", "--db", str(database), "--json"],
    )

    cli.main()

    assert database.exists()
    assert json.loads(capsys.readouterr().out) == []


def test_interfaces_command_saves_result_by_default(tmp_path, monkeypatch, capsys):
    database = tmp_path / "results.sqlite3"
    monkeypatch.setattr(
        sys,
        "argv",
        ["flipper-diag", "interfaces", "--db", str(database), "--json"],
    )
    monkeypatch.setattr(
        cli,
        "collect_ip_interfaces",
        lambda: DiagnosticResult(
            collector="linux.ip_address",
            status="ok",
            data={"interfaces": [], "count": 0},
        ),
    )

    cli.main()

    output = json.loads(capsys.readouterr().out)
    assert output["collector"] == "linux.ip_address"
    assert output["run_id"]
    assert database.exists()


def test_link_command_saves_result_by_default(tmp_path, monkeypatch, capsys):
    database = tmp_path / "link-results.sqlite3"
    monkeypatch.setattr(
        sys,
        "argv",
        ["flipper-diag", "link", "eth0", "--db", str(database), "--json"],
    )
    monkeypatch.setattr(
        cli,
        "collect_link_status",
        lambda interface: DiagnosticResult(
            collector="linux.ethtool",
            status="ok",
            interface=interface,
            data={"speed_mbps": 1000, "duplex": "full", "link_detected": True},
        ),
    )

    cli.main()

    output = json.loads(capsys.readouterr().out)
    assert output["interface"] == "eth0"
    assert output["data"]["speed_mbps"] == 1000
    assert output["run_id"]
    assert database.exists()
