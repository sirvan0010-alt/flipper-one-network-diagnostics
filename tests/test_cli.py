import json
import sys

import pytest

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


def test_routes_command_saves_result_by_default(tmp_path, monkeypatch, capsys):
    database = tmp_path / "routes.sqlite3"
    monkeypatch.setattr(
        sys, "argv", ["flipper-diag", "routes", "--db", str(database), "--json"]
    )
    monkeypatch.setattr(
        cli,
        "collect_default_routes",
        lambda: DiagnosticResult(
            collector="linux.default_routes",
            status="ok",
            data={"routes": [{"family": "inet", "gateway": "192.0.2.1"}], "count": 1},
        ),
    )

    cli.main()

    output = json.loads(capsys.readouterr().out)
    assert output["data"]["routes"][0]["gateway"] == "192.0.2.1"
    assert output["run_id"]
    assert database.exists()


def test_dns_command_saves_result_by_default(tmp_path, monkeypatch, capsys):
    database = tmp_path / "dns.sqlite3"
    monkeypatch.setattr(
        sys, "argv", ["flipper-diag", "dns", "--db", str(database), "--json"]
    )
    monkeypatch.setattr(
        cli,
        "collect_dns_config",
        lambda: DiagnosticResult(
            collector="linux.resolver_config",
            status="ok",
            data={"nameservers": ["192.0.2.53"]},
        ),
    )

    cli.main()

    output = json.loads(capsys.readouterr().out)
    assert output["data"]["nameservers"] == ["192.0.2.53"]
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


def test_local_check_command_saves_read_only_aggregate(tmp_path, monkeypatch, capsys):
    database = tmp_path / "local-check.sqlite3"
    monkeypatch.setattr(
        sys,
        "argv",
        ["flipper-diag", "local-check", "--db", str(database), "--json"],
    )
    monkeypatch.setattr(
        cli,
        "collect_local_check",
        lambda interface=None: DiagnosticResult(
            collector="network.local_check",
            status="ok",
            interface=interface,
            data={"active_probes": False, "component_status": {"routes": "ok"}},
        ),
    )

    cli.main()

    output = json.loads(capsys.readouterr().out)
    assert output["collector"] == "network.local_check"
    assert output["data"]["active_probes"] is False
    assert output["run_id"]
    assert database.exists()


def test_ping_cli_requires_explicit_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "flipper-diag", "ping", "--target", "192.0.2.1",
            "--scope", "192.0.2.1/32", "--db", str(tmp_path / "ping.sqlite3"),
        ],
    )
    with pytest.raises(SystemExit):
        cli.main()


def test_ping_cli_passes_single_target_authorization(tmp_path, monkeypatch, capsys):
    database = tmp_path / "ping.sqlite3"
    calls = []

    def fake_ping(target, **kwargs):
        calls.append((target, kwargs))
        return DiagnosticResult(
            collector="linux.ping",
            status="ok",
            data={"target": target, "packets_received": 3},
        )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "flipper-diag", "ping", "--target", "192.0.2.1",
            "--scope", "192.0.2.0/24", "--confirm-active",
            "--count", "2", "--timeout", "1", "--db", str(database), "--json",
        ],
    )
    monkeypatch.setattr(cli, "run_ping", fake_ping)
    monkeypatch.setattr(cli, "save_result", lambda *args: "ping-run-id")

    cli.main()

    output = json.loads(capsys.readouterr().out)
    target, kwargs = calls[0]
    assert target == "192.0.2.1"
    assert kwargs["safe_mode"] is False
    assert kwargs["authorization"].targets == ("192.0.2.1",)
    assert kwargs["authorization"].scope == "192.0.2.0/24"
    assert kwargs["count"] == 2
    assert output["run_id"] == "ping-run-id"
