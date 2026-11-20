import json
from pathlib import Path
import subprocess

import pytest

from flipper_diag import linux_ip


FIXTURE = Path(__file__).parent / "fixtures" / "ip-address.json"


def test_parse_iproute2_interface_fixture():
    interfaces = linux_ip.parse_ip_address_json(FIXTURE.read_text(encoding="utf-8"))

    assert len(interfaces) == 2
    assert interfaces[1]["name"] == "eth0"
    assert interfaces[1]["operstate"] == "UP"
    assert interfaces[1]["mtu"] == 1500
    assert interfaces[1]["addresses"][0]["local"] == "192.0.2.10"
    assert interfaces[1]["addresses"][0]["prefixlen"] == 24


def test_parser_rejects_invalid_json():
    with pytest.raises(ValueError, match="invalid JSON"):
        linux_ip.parse_ip_address_json("{broken")


def test_parser_rejects_wrong_root_type():
    with pytest.raises(ValueError, match="root must be an array"):
        linux_ip.parse_ip_address_json(json.dumps({"ifname": "eth0"}))


def test_parser_rejects_interface_without_name():
    with pytest.raises(ValueError, match="ifname"):
        linux_ip.parse_ip_address_json(json.dumps([{"ifindex": 2}]))


def test_collector_runs_only_fixed_read_only_command(monkeypatch):
    calls = []
    monkeypatch.setattr(linux_ip.shutil, "which", lambda name: "/usr/sbin/ip")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=FIXTURE.read_text(encoding="utf-8"),
            stderr="",
        )

    monkeypatch.setattr(linux_ip.subprocess, "run", fake_run)
    result = linux_ip.collect_ip_interfaces()

    assert result.status == "ok"
    assert result.data["count"] == 2
    assert calls[0][0] == ["/usr/sbin/ip", "-j", "address", "show"]
    assert calls[0][1]["timeout"] == linux_ip.COMMAND_TIMEOUT_SECONDS
    assert calls[0][1]["capture_output"] is True
    assert "shell" not in calls[0][1]


def test_collector_reports_missing_iproute2(monkeypatch):
    monkeypatch.setattr(linux_ip.shutil, "which", lambda name: None)

    result = linux_ip.collect_ip_interfaces()

    assert result.status == "error"
    assert result.findings[0].code == "COLLECTOR-TOOL-MISSING"
