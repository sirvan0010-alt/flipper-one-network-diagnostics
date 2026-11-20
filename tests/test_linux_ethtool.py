import subprocess
from pathlib import Path

import pytest

from flipper_diag import linux_ethtool


FIXTURE = Path(__file__).parent / "fixtures" / "ethtool-eth0.txt"


def test_parse_ethtool_output():
    result = linux_ethtool.parse_ethtool_output(FIXTURE.read_text(encoding="utf-8"))

    assert result == {
        "speed_mbps": 1000,
        "duplex": "full",
        "auto_negotiation": True,
        "link_detected": True,
    }


def test_parse_ethtool_rejects_missing_link_state():
    with pytest.raises(ValueError, match="Link detected"):
        linux_ethtool.parse_ethtool_output("Speed: 1000Mb/s\n")


def test_collector_uses_argument_list_and_fixed_timeout(monkeypatch):
    calls = []
    monkeypatch.setattr(linux_ethtool.shutil, "which", lambda name: "/usr/sbin/ethtool")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=FIXTURE.read_text(encoding="utf-8"),
            stderr="",
        )

    monkeypatch.setattr(linux_ethtool.subprocess, "run", fake_run)
    result = linux_ethtool.collect_link_status("eth0")

    assert result.status == "ok"
    assert result.data["speed_mbps"] == 1000
    assert calls[0][0] == ["/usr/sbin/ethtool", "eth0"]
    assert calls[0][1]["timeout"] == linux_ethtool.COMMAND_TIMEOUT_SECONDS
    assert "shell" not in calls[0][1]


def test_collector_rejects_unsafe_interface_name():
    with pytest.raises(ValueError, match="invalid interface"):
        linux_ethtool.collect_link_status("eth0; reboot")


def test_collector_marks_link_down(monkeypatch):
    output = "Speed: Unknown!\nDuplex: Unknown!\nLink detected: no\n"
    monkeypatch.setattr(linux_ethtool.shutil, "which", lambda name: "/usr/sbin/ethtool")
    monkeypatch.setattr(
        linux_ethtool.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, stdout=output, stderr=""
        ),
    )

    result = linux_ethtool.collect_link_status("eth0")

    assert result.status == "warning"
    assert result.findings[0].code == "ETH-LINK-DOWN"
