import json
import subprocess

import pytest

from flipper_diag import linux_routes


V4 = json.dumps(
    [
        {"dst": "default", "gateway": "192.0.2.1", "dev": "eth0", "protocol": "dhcp", "metric": 100},
        {"dst": "192.0.2.0/24", "dev": "eth0"},
    ]
)
V6 = json.dumps(
    [{"dst": "default", "gateway": "2001:db8::1", "dev": "eth0", "metric": 50}]
)


def test_parse_default_routes_keeps_only_default_and_normalizes_fields():
    routes = linux_routes.parse_default_routes(V4, family="inet")
    assert routes == [
        {
            "family": "inet",
            "destination": "default",
            "gateway": "192.0.2.1",
            "device": "eth0",
            "metric": 100,
            "protocol": "dhcp",
            "table": None,
            "preferred_source": None,
        }
    ]


def test_parse_ipv6_default_route():
    routes = linux_routes.parse_default_routes(V6, family="inet6")
    assert routes[0]["gateway"] == "2001:db8::1"
    assert routes[0]["family"] == "inet6"


@pytest.mark.parametrize("payload", ["{bad", "{}", '[{"gateway":"not-ip"}]'])
def test_parser_rejects_malformed_route_payloads(payload):
    with pytest.raises(ValueError):
        linux_routes.parse_default_routes(payload, family="inet")


def test_parser_rejects_wrong_family_gateway():
    with pytest.raises(ValueError, match="does not match"):
        linux_routes.parse_default_routes(V6, family="inet")


def test_collector_runs_fixed_read_only_ipv4_and_ipv6_commands(monkeypatch):
    calls = []
    monkeypatch.setattr(linux_routes.shutil, "which", lambda name: "/usr/sbin/ip")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        output = V4 if "-6" not in command else V6
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    monkeypatch.setattr(linux_routes.subprocess, "run", fake_run)
    result = linux_routes.collect_default_routes()

    assert result.status == "ok"
    assert result.data["count"] == 2
    assert [call[0][1:] for call in calls] == [
        ["-j", "route", "show", "default"],
        ["-6", "-j", "route", "show", "default"],
    ]
    assert all(call[1]["timeout"] == 5 for call in calls)
    assert all("shell" not in call[1] for call in calls)


def test_collector_reports_missing_default_route(monkeypatch):
    monkeypatch.setattr(linux_routes.shutil, "which", lambda name: "/usr/sbin/ip")
    monkeypatch.setattr(
        linux_routes.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "[]", ""),
    )
    result = linux_routes.collect_default_routes()
    assert result.status == "warning"
    assert result.findings[0].code == "ROUTE-DEFAULT-MISSING"
