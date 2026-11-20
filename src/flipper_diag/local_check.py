"""Local-only readiness check combining passive configuration collectors."""

from __future__ import annotations

from .linux_dns import collect_dns_config
from .linux_ethtool import collect_link_status
from .linux_ip import collect_ip_interfaces
from .linux_routes import collect_default_routes
from .models import DiagnosticResult, Finding
from .problem_engine import analyze_local_check


def _select_ethernet_interface(
    interfaces: list[dict], routes: list[dict], requested: str | None
) -> str | None:
    names = [
        item["name"]
        for item in interfaces
        if item.get("link_type") == "ether"
        and item.get("wireless") is False
        and isinstance(item.get("name"), str)
    ]
    if requested is not None:
        if requested not in names:
            raise ValueError("requested interface is not present in the Ethernet inventory")
        return requested

    for route in routes:
        device = route.get("device")
        if device in names:
            return device
    for item in interfaces:
        if item.get("name") in names and item.get("operstate") == "UP":
            return item["name"]
    return next(iter(names), None)


def collect_local_check(interface: str | None = None) -> DiagnosticResult:
    """Inspect local interfaces, default routes, DNS config and optional link state.

    This collector does not send packets, resolve DNS names, request DHCP leases,
    ping a gateway, scan peers or test Internet reachability.
    """
    interface_result = collect_ip_interfaces()
    route_result = collect_default_routes()
    dns_result = collect_dns_config()

    interfaces = interface_result.data.get("interfaces", [])
    routes = route_result.data.get("routes", [])
    selected_interface = _select_ethernet_interface(interfaces, routes, interface)

    components = {
        "interfaces": interface_result.to_dict(),
        "routes": route_result.to_dict(),
        "dns": dns_result.to_dict(),
    }
    has_wired_interface = any(
        item.get("link_type") == "ether" and item.get("wireless") is False
        for item in interfaces
    )
    component_status = {
        "interfaces": interface_result.status,
        "wired_interface": "available" if has_wired_interface else "not_available",
        "routes": route_result.status,
        "dns": dns_result.status,
    }
    findings = [
        *interface_result.findings,
        *route_result.findings,
        *dns_result.findings,
    ]
    limitations = [
        *interface_result.limitations,
        *route_result.limitations,
        *dns_result.limitations,
    ]

    if not any(
        item.get("link_type") == "ether" and item.get("wireless") is False
        for item in interfaces
    ):
        unclassified = any(
            item.get("link_type") == "ether" and item.get("wireless") is None
            for item in interfaces
        )
        findings.append(
            Finding(
                code=(
                    "ETH-INTERFACE-MEDIUM-UNKNOWN"
                    if unclassified
                    else "ETH-INTERFACE-NOT-FOUND"
                ),
                severity="warning",
                title=(
                    "Ethernet interface type could not be confirmed"
                    if unclassified
                    else "No Ethernet interface found"
                ),
                detail=(
                    "One or more Ethernet-like interfaces could not be classified as wired or Wi-Fi."
                    if unclassified
                    else "No confirmed wired Ethernet interface was returned by iproute2 and sysfs."
                ),
                recommendation=(
                    "Check /sys/class/net interface metadata and the kernel driver."
                    if unclassified
                    else "Connect a supported Ethernet adapter and check the system driver."
                ),
            )
        )
        component_status["link"] = "not_available"
    elif selected_interface is not None:
        link_result = collect_link_status(selected_interface)
        components["link"] = link_result.to_dict()
        component_status["link"] = link_result.status
        findings.extend(link_result.findings)
        limitations.extend(link_result.limitations)
    else:
        component_status["link"] = "not_available"

    route_devices = {
        route.get("device")
        for route in routes
        if isinstance(route.get("device"), str) and route.get("device")
    }
    if (
        selected_interface is not None
        and route_devices
        and selected_interface not in route_devices
    ):
        findings.append(
            Finding(
                code="ROUTE-DEFAULT-OTHER-INTERFACE",
                severity="warning",
                title="Default route uses another interface",
                detail=(
                    f"The selected Ethernet interface is {selected_interface}, but the "
                    f"default route is associated with: {', '.join(sorted(route_devices))}."
                ),
                recommendation=(
                    "Check route metrics and the intended wired interface before treating "
                    "the default route as evidence of wired connectivity."
                ),
            )
        )

    if selected_interface is not None:
        selected = next(
            (item for item in interfaces if item.get("name") == selected_interface),
            {},
        )
        if not selected.get("addresses"):
            findings.append(
                Finding(
                    code="INTERFACE-NO-IP-ADDRESS",
                    severity="warning",
                    title="Selected Ethernet interface has no IP address",
                    detail=f"No IPv4 or IPv6 address was listed for {selected_interface}.",
                    recommendation="Check the interface configuration and DHCP/static addressing.",
                )
            )

    required_statuses = (
        interface_result.status,
        route_result.status,
        dns_result.status,
        component_status["link"],
    )
    if interface_result.status == "error":
        status = "error"
    elif any(value not in ("ok", "not_available") for value in required_statuses):
        status = "warning"
    elif findings:
        status = "warning"
    else:
        status = "ok"

    limitations.append(
        "Local readiness check only: no DHCP exchange, DNS query, gateway ping, TCP probe, "
        "active discovery, packet injection or Internet reachability test is performed."
    )
    result = DiagnosticResult(
        collector="network.local_check",
        status=status,
        interface=selected_interface,
        data={
            "selected_interface": selected_interface,
            "component_status": component_status,
            "components": components,
            "active_probes": False,
        },
        findings=findings,
        limitations=limitations,
    )
    result.data["assessment"] = analyze_local_check(result)
    return result
