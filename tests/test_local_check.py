from flipper_diag import local_check
from flipper_diag.models import DiagnosticResult, Finding


def _result(collector, status="ok", data=None, findings=None, limitations=None):
    return DiagnosticResult(
        collector=collector,
        status=status,
        data=data or {},
        findings=findings or [],
        limitations=limitations or [],
    )


def test_local_check_combines_read_only_components(monkeypatch):
    monkeypatch.setattr(
        local_check,
        "collect_ip_interfaces",
        lambda: _result(
            "linux.ip_address",
            data={
                "interfaces": [
                    {
                        "name": "end0",
                        "link_type": "ether",
                        "wireless": False,
                        "operstate": "UP",
                        "addresses": [{"family": "inet", "local": "192.0.2.10"}],
                    }
                ]
            },
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_default_routes",
        lambda: _result(
            "linux.default_routes",
            data={"routes": [{"family": "inet", "device": "end0", "gateway": "192.0.2.1"}]},
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_dns_config",
        lambda: _result(
            "linux.resolver_config",
            data={"nameservers": ["192.0.2.53"]},
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_link_status",
        lambda interface: _result(
            "linux.ethtool",
            data={"link_detected": True, "speed_mbps": 1000},
        ),
    )

    result = local_check.collect_local_check()

    assert result.status == "ok"
    assert result.interface == "end0"
    assert result.data["active_probes"] is False
    assert result.data["assessment"]["likely_causes"] == []
    assert result.data["component_status"] == {
        "interfaces": "ok",
        "wired_interface": "available",
        "routes": "ok",
        "dns": "ok",
        "link": "ok",
    }
    assert result.data["components"]["link"]["data"]["speed_mbps"] == 1000
    assert any("no DHCP exchange" in item for item in result.limitations)


def test_local_check_reports_missing_route_and_dns(monkeypatch):
    monkeypatch.setattr(
        local_check,
        "collect_ip_interfaces",
        lambda: _result(
            "linux.ip_address",
            data={
                "interfaces": [
                    {
                        "name": "end0",
                        "link_type": "ether",
                        "wireless": False,
                        "operstate": "UP",
                        "addresses": [],
                    }
                ]
            },
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_default_routes",
        lambda: _result(
            "linux.default_routes",
            status="warning",
            findings=[
                Finding("ROUTE-DEFAULT-MISSING", "warning", "No default route found")
            ],
            data={"routes": []},
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_dns_config",
        lambda: _result(
            "linux.resolver_config",
            status="warning",
            findings=[Finding("DNS-CONFIG-MISSING", "warning", "No DNS server configured")],
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_link_status",
        lambda interface: _result(
            "linux.ethtool",
            status="warning",
            findings=[Finding("ETH-LINK-DOWN", "warning", "Ethernet link is down")],
        ),
    )

    result = local_check.collect_local_check()

    assert result.status == "warning"
    codes = {finding.code for finding in result.findings}
    assert {"ROUTE-DEFAULT-MISSING", "DNS-CONFIG-MISSING", "ETH-LINK-DOWN"} <= codes
    assert "INTERFACE-NO-IP-ADDRESS" in codes


def test_local_check_handles_no_ethernet_adapter(monkeypatch):
    monkeypatch.setattr(
        local_check,
        "collect_ip_interfaces",
        lambda: _result("linux.ip_address", data={"interfaces": []}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_default_routes",
        lambda: _result("linux.default_routes", data={"routes": []}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_dns_config",
        lambda: _result("linux.resolver_config", data={"nameservers": ["192.0.2.53"]}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_link_status",
        lambda interface: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    result = local_check.collect_local_check()

    assert result.status == "warning"
    assert result.interface is None
    assert result.data["component_status"]["link"] == "not_available"
    assert result.findings[0].code == "ETH-INTERFACE-NOT-FOUND"


def test_requested_interface_must_be_in_local_ethernet_inventory(monkeypatch):
    monkeypatch.setattr(
        local_check,
        "collect_ip_interfaces",
        lambda: _result("linux.ip_address", data={"interfaces": []}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_default_routes",
        lambda: _result("linux.default_routes", data={"routes": []}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_dns_config",
        lambda: _result("linux.resolver_config", data={"nameservers": []}),
    )

    try:
        local_check.collect_local_check("eth0")
    except ValueError as exc:
        assert "not present" in str(exc)
    else:
        raise AssertionError("invalid interface should be rejected")


def test_local_check_flags_default_route_on_another_interface(monkeypatch):
    monkeypatch.setattr(
        local_check,
        "collect_ip_interfaces",
        lambda: _result(
            "linux.ip_address",
            data={
                "interfaces": [
                    {
                        "name": "end0",
                        "link_type": "ether",
                        "wireless": False,
                        "operstate": "UP",
                        "addresses": [{"family": "inet", "local": "192.0.2.10"}],
                    },
                    {
                        "name": "wlan0",
                        "link_type": "ether",
                        "wireless": True,
                        "operstate": "UP",
                        "addresses": [{"family": "inet", "local": "198.51.100.10"}],
                    },
                ]
            },
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_default_routes",
        lambda: _result(
            "linux.default_routes",
            data={"routes": [{"family": "inet", "device": "wlan0", "gateway": "198.51.100.1"}]},
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_dns_config",
        lambda: _result("linux.resolver_config", data={"nameservers": ["192.0.2.53"]}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_link_status",
        lambda interface: _result(
            "linux.ethtool", data={"link_detected": True}
        ),
    )

    result = local_check.collect_local_check("end0")

    assert result.status == "warning"
    assert "ROUTE-DEFAULT-OTHER-INTERFACE" in {
        finding.code for finding in result.findings
    }


def test_local_check_does_not_treat_wifi_as_wired_ethernet(monkeypatch):
    monkeypatch.setattr(
        local_check,
        "collect_ip_interfaces",
        lambda: _result(
            "linux.ip_address",
            data={
                "interfaces": [
                    {
                        "name": "wlan0",
                        "link_type": "ether",
                        "wireless": True,
                        "operstate": "UP",
                        "addresses": [{"family": "inet", "local": "192.0.2.10"}],
                    }
                ]
            },
        ),
    )
    monkeypatch.setattr(
        local_check,
        "collect_default_routes",
        lambda: _result("linux.default_routes", data={"routes": []}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_dns_config",
        lambda: _result("linux.resolver_config", data={"nameservers": []}),
    )
    monkeypatch.setattr(
        local_check,
        "collect_link_status",
        lambda interface: (_ for _ in ()).throw(AssertionError("Wi-Fi must not use Ethernet test")),
    )

    result = local_check.collect_local_check()

    assert result.interface is None
    assert result.data["component_status"]["link"] == "not_available"
    assert "ETH-INTERFACE-NOT-FOUND" in {finding.code for finding in result.findings}
