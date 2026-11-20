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


def test_baseline_cli_save_and_compare(tmp_path, monkeypatch, capsys):
    database = tmp_path / "baseline.sqlite3"
    original = tmp_path / "original.json"
    current = tmp_path / "current.json"
    original.write_text(
        json.dumps([{"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.10"]}]),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            [
                {"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.11"]},
                {"mac_address": "02:00:00:00:00:02", "addresses": ["192.0.2.20"]},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "flipper-diag", "baseline", "save", "--name", "office",
            "--input", str(original), "--db", str(database), "--json",
        ],
    )
    cli.main()
    saved = json.loads(capsys.readouterr().out)
    assert saved["device_count"] == 1

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "flipper-diag", "baseline", "compare", "--name", "office",
            "--input", str(current), "--db", str(database), "--json",
        ],
    )
    cli.main()
    findings = json.loads(capsys.readouterr().out)
    assert [item["code"] for item in findings] == [
        "INVENTORY-NEW-DEVICE",
        "INVENTORY-ADDRESS-CHANGED",
    ]
