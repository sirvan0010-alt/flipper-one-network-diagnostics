import json
import subprocess

import pytest

from flipper_diag import linux_neighbors


V4 = json.dumps(
    [
        {"dst": "192.0.2.1", "lladdr": "02:00:00:00:00:01", "dev": "end0", "state": ["REACHABLE"], "router": True},
        {"dst": "192.0.2.20", "lladdr": "02:00:00:00:00:20", "dev": "end0", "state": ["STALE"]},
        {"dst": "192.0.2.30", "dev": "end0", "state": ["INCOMPLETE"]},
    ]
)
V6 = json.dumps(
    [
        {"dst": "2001:db8::20", "lladdr": "02:00:00:00:00:21", "dev": "end0", "state": "DELAY"}
    ]
)


def test_parse_neighbor_cache_normalizes_ipv4_and_states():
    neighbors = linux_neighbors.parse_neighbor_json(V4, family="inet")
    assert neighbors[0] == {
        "family": "inet",
        "ip": "192.0.2.1",
        "mac_address": "02:00:00:00:00:01",
        "interface": "end0",
        "state": ["REACHABLE"],
        "usable": True,
        "router": True,
    }
    assert neighbors[2]["usable"] is False


def test_parse_neighbor_cache_supports_ipv6():
    neighbors = linux_neighbors.parse_neighbor_json(V6, family="inet6")
    assert neighbors[0]["ip"] == "2001:db8::20"
    assert neighbors[0]["usable"] is True


@pytest.mark.parametrize("payload", ["{bad", "{}", '[{"dst":"not-an-ip"}]'])
def test_neighbor_parser_rejects_invalid_payload(payload):
    with pytest.raises(ValueError):
        linux_neighbors.parse_neighbor_json(payload, family="inet")


def test_collector_runs_fixed_read_only_commands(monkeypatch):
    calls = []
    monkeypatch.setattr(linux_neighbors.shutil, "which", lambda name: "/usr/sbin/ip")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        output = V6 if "-6" in command else V4
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(linux_neighbors.subprocess, "run", fake_run)
    result = linux_neighbors.collect_neighbor_cache()

    assert result.status == "ok"
    assert result.data["count"] == 4
    assert result.data["usable_count"] == 3
    assert [call[0][1:] for call in calls] == [
        ["-j", "neigh", "show"],
        ["-6", "-j", "neigh", "show"],
    ]
    assert all(call[1]["timeout"] == 5 for call in calls)
    assert all("shell" not in call[1] for call in calls)
    assert result.findings[0].code == "NEIGHBOR-UNRESOLVED"


def test_empty_neighbor_cache_is_not_a_failure(monkeypatch):
    monkeypatch.setattr(linux_neighbors.shutil, "which", lambda name: "/usr/sbin/ip")
    monkeypatch.setattr(
        linux_neighbors.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "[]", ""),
    )
    result = linux_neighbors.collect_neighbor_cache()
    assert result.status == "ok"
    assert result.data["count"] == 0


def test_partial_neighbor_cache_failure_is_warning(monkeypatch):
    monkeypatch.setattr(linux_neighbors.shutil, "which", lambda name: "/usr/sbin/ip")

    def fake_run(command, **kwargs):
        if "-6" in command:
            return subprocess.CompletedProcess(command, 1, "", "netlink error")
        return subprocess.CompletedProcess(command, 0, V4, "")

    monkeypatch.setattr(linux_neighbors.subprocess, "run", fake_run)
    result = linux_neighbors.collect_neighbor_cache()

    assert result.status == "warning"
    assert result.data["count"] == 3
    assert any("inet6" in note for note in result.limitations)
