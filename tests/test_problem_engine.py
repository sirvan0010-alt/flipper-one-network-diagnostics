import pytest

from flipper_diag.models import DiagnosticResult, Finding
from flipper_diag.problem_engine import analyze_local_check


def _local_result(*, interfaces=None, routes=None, dns=None, link=None, findings=None):
    components = {
        "interfaces": {"data": {"interfaces": interfaces or []}},
        "routes": {"data": {"routes": routes or []}},
        "dns": {"data": dns or {"nameservers": ["192.0.2.53"]}},
        "link": {"data": link or {"link_detected": True}},
    }
    return DiagnosticResult(
        collector="network.local_check",
        status="warning" if findings else "ok",
        interface="end0",
        data={"components": components},
        findings=findings or [],
    )


def test_problem_engine_does_not_claim_connectivity_when_local_config_looks_good():
    result = _local_result(
        interfaces=[
            {
                "name": "end0",
                "addresses": [{"family": "inet", "local": "192.0.2.10"}],
            }
        ],
        routes=[{"device": "end0", "gateway": "192.0.2.1"}],
    )

    assessment = analyze_local_check(result)

    assert assessment["likely_causes"] == []
    assert assessment["reachability_tested"] is False
    assert assessment["root_cause_confirmed"] is False
    assert "reachability has not been verified" in assessment["summary"]


def test_problem_engine_reports_possible_addressing_and_route_issues():
    result = _local_result(
        interfaces=[{"name": "end0", "addresses": []}],
        routes=[],
        dns={"nameservers": []},
        findings=[
            Finding("INTERFACE-NO-IP-ADDRESS", "warning", "No IP address"),
            Finding("ROUTE-DEFAULT-MISSING", "warning", "No default route"),
            Finding("DNS-CONFIG-MISSING", "warning", "No DNS server"),
        ],
    )

    assessment = analyze_local_check(result)
    codes = {item["code"] for item in assessment["likely_causes"]}

    assert {
        "ADDRESS_CONFIGURATION",
        "DEFAULT_ROUTE_CONFIGURATION",
        "DNS_RESOLVER_CONFIGURATION",
    } <= codes
    assert assessment["root_cause_confirmed"] is False
    assert "root cause is not confirmed" in assessment["summary"]


def test_problem_engine_explains_link_down_and_route_mismatch():
    result = _local_result(
        interfaces=[{"name": "end0", "addresses": [{"local": "192.0.2.10"}]}],
        routes=[{"device": "wlan0", "gateway": "198.51.100.1"}],
        link={"link_detected": False},
        findings=[
            Finding("ETH-LINK-DOWN", "warning", "Link down"),
            Finding("ROUTE-DEFAULT-OTHER-INTERFACE", "warning", "Route on another interface"),
        ],
    )

    assessment = analyze_local_check(result)
    codes = {item["code"] for item in assessment["likely_causes"]}

    assert {"PHYSICAL_LINK_PATH", "ROUTE_INTERFACE_SELECTION"} <= codes


def test_problem_engine_rejects_unrelated_collector_results():
    result = DiagnosticResult(collector="linux.ip_address", status="ok")
    with pytest.raises(ValueError, match="network.local_check"):
        analyze_local_check(result)
