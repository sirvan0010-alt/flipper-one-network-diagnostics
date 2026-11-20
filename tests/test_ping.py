import subprocess

import pytest

from flipper_diag.ping import parse_ping_output, run_ping
from flipper_diag.safety import ActiveAuthorization, ActiveOperationBlocked


IPV4_OUTPUT = """
3 packets transmitted, 3 received, 0% packet loss, time 2002ms
rtt min/avg/max/mdev = 1.120/1.340/1.600/0.190 ms
"""
IPV6_OUTPUT = """
2 packets transmitted, 1 received, 50% packet loss, time 1000ms
round-trip min/avg/max/stddev = 1.200/1.200/1.200/0.000 ms
"""


def _authorization(target="192.0.2.1", scope="192.0.2.0/24"):
    return ActiveAuthorization(
        purpose="single-target ICMP diagnostic",
        scope=scope,
        targets=(target,),
        confirmed=True,
    )


def test_parse_iputils_ping_summary_and_rtt():
    parsed = parse_ping_output(IPV4_OUTPUT)
    assert parsed == {
        "packets_transmitted": 3,
        "packets_received": 3,
        "packet_loss_percent": 0.0,
        "rtt_min_ms": 1.12,
        "rtt_avg_ms": 1.34,
        "rtt_max_ms": 1.6,
        "rtt_mdev_ms": 0.19,
    }


def test_parse_busybox_style_packet_summary():
    parsed = parse_ping_output(IPV6_OUTPUT)
    assert parsed["packets_transmitted"] == 2
    assert parsed["packets_received"] == 1
    assert parsed["packet_loss_percent"] == 50.0


def test_ping_is_blocked_by_default_safe_mode():
    with pytest.raises(ActiveOperationBlocked, match="Safe Mode"):
        run_ping("192.0.2.1")


def test_ping_rejects_hostname_and_invalid_bounds_before_execution():
    with pytest.raises(ValueError, match="literal IPv4 or IPv6"):
        run_ping("example.com", authorization=_authorization(), safe_mode=False)
    with pytest.raises(ValueError, match="count must be"):
        run_ping("192.0.2.1", authorization=_authorization(), safe_mode=False, count=6)


def test_ping_rejects_target_outside_authorized_scope():
    authorization = _authorization(target="198.51.100.1", scope="192.0.2.0/24")
    with pytest.raises(ActiveOperationBlocked, match="outside"):
        run_ping(
            "198.51.100.1",
            authorization=authorization,
            safe_mode=False,
        )


def test_authorized_ping_uses_fixed_arguments_and_no_shell(monkeypatch):
    calls = []
    monkeypatch.setattr("flipper_diag.ping.shutil.which", lambda name: "/usr/bin/ping")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, IPV4_OUTPUT, "")

    monkeypatch.setattr("flipper_diag.ping.subprocess.run", fake_run)
    result = run_ping(
        "192.0.2.1",
        authorization=_authorization(),
        safe_mode=False,
        count=3,
        timeout_seconds=1,
    )

    assert result.status == "ok"
    assert result.data["packet_loss_percent"] == 0.0
    command, kwargs = calls[0]
    assert command == [
        "/usr/bin/ping", "-n", "-q", "-c", "3", "-W", "1", "192.0.2.1"
    ]
    assert kwargs["timeout"] == 6
    assert kwargs["check"] is False
    assert "shell" not in kwargs


def test_authorized_ipv6_ping_uses_ipv6_flag(monkeypatch):
    calls = []
    monkeypatch.setattr("flipper_diag.ping.shutil.which", lambda name: "/usr/bin/ping")

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, IPV6_OUTPUT, "")

    monkeypatch.setattr("flipper_diag.ping.subprocess.run", fake_run)
    result = run_ping(
        "2001:db8::1",
        authorization=ActiveAuthorization(
            purpose="single-target ICMP diagnostic",
            scope="2001:db8::/64",
            targets=("2001:db8::1",),
            confirmed=True,
        ),
        safe_mode=False,
    )

    assert result.status == "warning"
    assert result.data["packet_loss_percent"] == 50.0
    assert calls[0][:4] == ["/usr/bin/ping", "-n", "-q", "-6"]


def test_ping_timeout_is_reported_without_retry(monkeypatch):
    monkeypatch.setattr("flipper_diag.ping.shutil.which", lambda name: "/usr/bin/ping")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr("flipper_diag.ping.subprocess.run", timeout)
    result = run_ping(
        "192.0.2.1",
        authorization=_authorization(),
        safe_mode=False,
    )
    assert result.status == "warning"
    assert result.findings[0].code == "PING-COLLECTOR-TIMEOUT"


def test_ping_command_error_exit_status_is_not_reported_as_packet_loss(monkeypatch):
    monkeypatch.setattr("flipper_diag.ping.shutil.which", lambda name: "/usr/bin/ping")
    monkeypatch.setattr(
        "flipper_diag.ping.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 2, IPV4_OUTPUT, ""),
    )
    result = run_ping(
        "192.0.2.1",
        authorization=_authorization(),
        safe_mode=False,
    )
    assert result.status == "error"
    assert result.data["packets_received"] == 3
