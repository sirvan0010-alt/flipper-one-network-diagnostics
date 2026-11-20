"""Local-only readiness check combining passive configuration collectors."""

from __future__ import annotations

from .linux_dns import collect_dns_config
from .linux_ethtool import collect_link_status
from .linux_ip import collect_ip_interfaces
from .linux_routes import collect_default_routes
from .models import DiagnosticResult, Finding


def _select_ethernet_interface(
    interfaces: list[dict], routes: list[dict], requested: str | None
) -> str | None:
    names = {
        item["name"]
        for item in interfaces
        if item.get("link_type") == "ether" and isinstance(item.get("name"), str)
    }
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
    component_status = {
        "interfaces": interface_result.status,
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

    if not any(item.get("link_type") == "ether" for item in interfaces):
        findings.append(
            Finding(
                code="ETH-INTERFACE-NOT-FOUND",
                severity="warning",
                title="No Ethernet interface found",
                detail="No interface with Ethernet link type was returned by iproute2.",
                recommendation="Connect a supported Ethernet adapter and check the system driver.",
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
    return DiagnosticResult(
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
