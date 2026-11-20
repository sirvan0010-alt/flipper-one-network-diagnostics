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
        "source": "ethtool",
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


def test_sysfs_fallback_reads_carrier_speed_and_duplex(tmp_path, monkeypatch):
    interface = tmp_path / "end0"
    interface.mkdir()
    (interface / "operstate").write_text("up\n", encoding="utf-8")
    (interface / "carrier").write_text("1\n", encoding="utf-8")
    (interface / "speed").write_text("1000\n", encoding="utf-8")
    (interface / "duplex").write_text("full\n", encoding="utf-8")
    monkeypatch.setattr(linux_ethtool, "SYS_CLASS_NET", tmp_path)
    monkeypatch.setattr(linux_ethtool.shutil, "which", lambda name: None)

    result = linux_ethtool.collect_link_status("end0")

    assert result.status == "ok"
    assert result.collector == "linux.sysfs_link"
    assert result.data == {
        "link_detected": True,
        "speed_mbps": 1000,
        "duplex": "full",
        "auto_negotiation": None,
        "operstate": "up",
        "source": "sysfs",
    }


def test_sysfs_fallback_reports_link_down(tmp_path, monkeypatch):
    interface = tmp_path / "end0"
    interface.mkdir()
    (interface / "operstate").write_text("down\n", encoding="utf-8")
    (interface / "carrier").write_text("0\n", encoding="utf-8")
    monkeypatch.setattr(linux_ethtool, "SYS_CLASS_NET", tmp_path)
    monkeypatch.setattr(linux_ethtool.shutil, "which", lambda name: None)

    result = linux_ethtool.collect_link_status("end0")

    assert result.status == "warning"
    assert result.findings[0].code == "ETH-LINK-DOWN"


def test_sysfs_fallback_reports_unavailable_carrier(tmp_path, monkeypatch):
    interface = tmp_path / "end0"
    interface.mkdir()
    (interface / "operstate").write_text("unknown\n", encoding="utf-8")
    monkeypatch.setattr(linux_ethtool, "SYS_CLASS_NET", tmp_path)
    monkeypatch.setattr(linux_ethtool.shutil, "which", lambda name: None)

    result = linux_ethtool.collect_link_status("end0")

    assert result.status == "warning"
    assert result.data["link_detected"] is None
    assert result.findings[0].code == "ETH-LINK-STATUS-UNAVAILABLE"


def test_ethtool_failure_falls_back_to_sysfs(tmp_path, monkeypatch):
    interface = tmp_path / "end0"
    interface.mkdir()
    (interface / "operstate").write_text("up\n", encoding="utf-8")
    (interface / "carrier").write_text("1\n", encoding="utf-8")
    monkeypatch.setattr(linux_ethtool, "SYS_CLASS_NET", tmp_path)
    monkeypatch.setattr(linux_ethtool.shutil, "which", lambda name: "/usr/sbin/ethtool")
    monkeypatch.setattr(
        linux_ethtool.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "unsupported"),
    )

    result = linux_ethtool.collect_link_status("end0")

    assert result.collector == "linux.sysfs_link"
    assert result.data["link_detected"] is True


@pytest.mark.parametrize("interface", [".", ".."])
def test_collector_rejects_path_components(interface):
    with pytest.raises(ValueError, match="invalid interface"):
        linux_ethtool.collect_link_status(interface)
