"""Deterministic, evidence-bounded explanations for local readiness results."""

from __future__ import annotations

from typing import Any

from .models import DiagnosticResult


def analyze_local_check(result: DiagnosticResult) -> dict[str, Any]:
    """Explain observed local configuration without claiming reachability or root cause."""
    if result.collector != "network.local_check":
        raise ValueError("problem engine expects a network.local_check result")

    components = result.data.get("components", {})
    interface_data = components.get("interfaces", {}).get("data", {})
    routes_data = components.get("routes", {}).get("data", {})
    dns_data = components.get("dns", {}).get("data", {})
    link_data = components.get("link", {}).get("data", {})
    findings = result.findings
    finding_codes = {item.code for item in findings}

    likely_causes: list[dict[str, str]] = []
    if "ETH-INTERFACE-NOT-FOUND" in finding_codes:
        likely_causes.append(
            {
                "code": "NO_WIRED_INTERFACE",
                "title": "No wired Ethernet interface was confirmed",
                "confidence": "high",
                "detail": "The local interface inventory and sysfs did not identify a wired port.",
                "recommendation": "Check the adapter, port mapping and kernel driver.",
            }
        )
    elif "ETH-INTERFACE-MEDIUM-UNKNOWN" in finding_codes:
        likely_causes.append(
            {
                "code": "WIRED_INTERFACE_UNCLASSIFIED",
                "title": "The interface medium could not be classified",
                "confidence": "low",
                "detail": "An Ethernet-like interface exists, but sysfs did not confirm whether it is wired or Wi-Fi.",
                "recommendation": "Inspect /sys/class/net and the driver before running wired tests.",
            }
        )

    if link_data.get("link_detected") is False:
        likely_causes.append(
            {
                "code": "PHYSICAL_LINK_PATH",
                "title": "The Ethernet physical link is down",
                "confidence": "medium",
                "detail": "The driver/kernel reports no carrier; the cable, remote switch port or PHY path may be responsible.",
                "recommendation": "Check both cable ends, the remote switch port and link negotiation.",
            }
        )

    selected = next(
        (
            item
            for item in interface_data.get("interfaces", [])
            if item.get("name") == result.interface
        ),
        {},
    )
    if result.interface and not selected.get("addresses"):
        likely_causes.append(
            {
                "code": "ADDRESS_CONFIGURATION",
                "title": "The selected Ethernet interface has no IP address",
                "confidence": "high",
                "detail": "No IPv4 or IPv6 address was listed for the selected wired interface. DHCP failure is possible but has not been tested.",
                "recommendation": "Check DHCP client state and the intended static address configuration.",
            }
        )

    routes = routes_data.get("routes", [])
    route_devices = {
        route.get("device")
        for route in routes
        if isinstance(route.get("device"), str) and route.get("device")
    }
    if not routes:
        likely_causes.append(
            {
                "code": "DEFAULT_ROUTE_CONFIGURATION",
                "title": "No default route is configured",
                "confidence": "high",
                "detail": "The local IPv4 and IPv6 routing-table queries returned no default route.",
                "recommendation": "Check the gateway settings and DHCP route options. Gateway reachability has not been tested.",
            }
        )
    elif result.interface and route_devices and result.interface not in route_devices:
        likely_causes.append(
            {
                "code": "ROUTE_INTERFACE_SELECTION",
                "title": "The default route uses a different interface",
                "confidence": "high",
                "detail": f"The selected wired interface is {result.interface}; default routes use {', '.join(sorted(route_devices))}.",
                "recommendation": "Check route metrics and whether the wired interface is intended to be the active uplink.",
            }
        )

    nameservers = dns_data.get("nameservers", [])
    if not nameservers:
        likely_causes.append(
            {
                "code": "DNS_RESOLVER_CONFIGURATION",
                "title": "No valid DNS resolver is configured",
                "confidence": "high",
                "detail": "The local resolver file contains no valid nameserver address.",
                "recommendation": "Check DHCP-provided DNS options or the intended static resolver settings.",
            }
        )
    elif dns_data.get("invalid_nameservers"):
        likely_causes.append(
            {
                "code": "DNS_RESOLVER_ENTRY_INVALID",
                "title": "The resolver configuration contains invalid nameserver entries",
                "confidence": "high",
                "detail": "At least one nameserver entry could not be parsed as an IP address.",
                "recommendation": "Correct the invalid resolver entries.",
            }
        )

    if likely_causes:
        summary = (
            f"{len(likely_causes)} local configuration issue(s) need attention; "
            "the end-to-end root cause is not confirmed."
        )
    else:
        summary = (
            "Local interface, route and DNS settings appear present; "
            "network reachability has not been verified."
        )

    return {
        "summary": summary,
        "likely_causes": likely_causes,
        "observations": [
            {
                "code": item.code,
                "severity": item.severity,
                "title": item.title,
            }
            for item in findings
        ],
        "reachability_tested": False,
        "root_cause_confirmed": False,
        "confidence_note": (
            "Confidence describes the observed local state. Suggested causes remain hypotheses "
            "until active tests or physical inspection confirm them."
        ),
    }
