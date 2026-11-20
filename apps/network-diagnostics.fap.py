#!/usr/bin/env python3
# /// flipctl
# name = "Network Diagnostics"
# status = true
# ///
"""Local-first network diagnostics for the Flipper One panel.

The device UI is deliberately read-only: it inventories local interfaces,
Ethernet link state, default routes and resolver configuration, and stores results
locally. Local Check combines these observations without sending network probes.
"""

from __future__ import annotations

import ipaddress

import flipctl

from flipper_diag.linux_dns import collect_dns_config
from flipper_diag.linux_ethtool import collect_link_status
from flipper_diag.linux_ip import collect_ip_interfaces
from flipper_diag.linux_routes import collect_default_routes
from flipper_diag.local_check import collect_local_check
from flipper_diag.ping import run_ping
from flipper_diag.safety import ActiveAuthorization
from flipper_diag.tcp_connect import run_tcp_connect
from flipper_diag.store import (
    default_database_path,
    list_results,
    save_result,
)

state = {
    "interfaces": [],
    "detail_rows": [],
    "detail_refresh": None,
    "history_lines": [],
    "last_saved": "",
    "confirm_rows": [],
    "pending_active_action": None,
}


def persist(result) -> str:
    """Store a result locally; keep the UI usable if storage is unavailable."""
    try:
        run_id = save_result(default_database_path(), result)
        state["last_saved"] = run_id[:8]
        return run_id[:8]
    except Exception as exc:
        state["last_saved"] = "not saved"
        return f"not saved ({type(exc).__name__})"


def refresh_interfaces():
    """Read local interface configuration; no packets are sent."""
    result = collect_ip_interfaces()
    state["interfaces"] = result.data.get("interfaces", [])
    saved = persist(result)
    rows = [
        flipctl.heading("Local interfaces", result.status.upper()),
        flipctl.pair("Found", str(result.data.get("count", 0))),
    ]
    for interface in state["interfaces"]:
        rows.append(flipctl.rule())
        rows.append(
            flipctl.heading(
                interface["name"],
                interface.get("operstate") or "unknown",
            )
        )
        rows.append(flipctl.pair("Type", interface.get("link_type") or "-"))
        rows.append(flipctl.pair("MAC", interface.get("mac_address") or "-"))
        rows.append(flipctl.pair("MTU", str(interface.get("mtu") or "-")))
        for address in interface.get("addresses", []):
            rows.append(
                flipctl.pair(
                    address.get("family", "IP"),
                    f"{address.get('local', '-')}/{address.get('prefixlen', '-')}",
                )
            )
    for finding in result.findings:
        rows.append(flipctl.text(finding.title))
    for note in result.limitations:
        rows.append(flipctl.text(note, dim=True))
    rows.append(flipctl.pair("Saved", saved, dim=True))
    state["detail_rows"] = rows
    state["detail_refresh"] = refresh_interfaces
    return result


def ethernet_interfaces():
    return [
        item for item in state["interfaces"]
        if item.get("link_type") == "ether" and item.get("wireless") is False
    ]


def refresh_link(interface: str):
    """Read the current link state of one local interface."""
    result = collect_link_status(interface)
    saved = persist(result)
    rows = [
        flipctl.heading(f"Ethernet {interface}", result.status.upper()),
    ]
    labels = (
        ("Link", "link_detected"),
        ("Speed", "speed_mbps"),
        ("Duplex", "duplex"),
        ("Autoneg", "auto_negotiation"),
    )
    for label, key in labels:
        value = result.data.get(key, "not available")
        if key == "speed_mbps" and isinstance(value, int):
            value = f"{value} Mb/s"
        rows.append(flipctl.pair(label, str(value)))
    for finding in result.findings:
        rows.append(flipctl.rule())
        rows.append(flipctl.text(finding.title))
        if finding.detail:
            rows.extend(flipctl.text(line) for line in flipctl.wrap(finding.detail))
        if finding.recommendation:
            rows.extend(
                flipctl.text(line, dim=True)
                for line in flipctl.wrap(finding.recommendation)
            )
    for note in result.limitations:
        rows.append(flipctl.text(note, dim=True))
    rows.append(flipctl.pair("Saved", saved, dim=True))
    state["detail_rows"] = rows
    state["detail_refresh"] = lambda: refresh_link(interface)
    detail.show()
    return result


def show_local_check():
    """Show combined local-only readiness results; no network probes are sent."""
    result = collect_local_check()
    saved = persist(result)
    statuses = result.data.get("component_status", {})
    rows = [flipctl.heading("Local Check", result.status.upper())]
    rows.append(flipctl.rule())
    rows.append(flipctl.pair("Interfaces", statuses.get("interfaces", "unknown")))
    rows.append(flipctl.pair("Wired port", statuses.get("wired_interface", "unknown")))
    rows.append(flipctl.pair("Link", statuses.get("link", "unknown")))
    rows.append(flipctl.pair("Default route", statuses.get("routes", "unknown")))
    rows.append(flipctl.pair("DNS config", statuses.get("dns", "unknown")))
    if result.interface:
        rows.append(flipctl.pair("Interface", result.interface))
    assessment = result.data.get("assessment", {})
    rows.append(flipctl.rule())
    rows.append(flipctl.heading("Assessment", ""))
    rows.extend(
        flipctl.text(line)
        for line in flipctl.wrap(assessment.get("summary", "No assessment available."))
    )
    for cause in assessment.get("likely_causes", []):
        rows.append(flipctl.heading(cause["title"], cause["confidence"]))
        rows.extend(flipctl.text(line, dim=True) for line in flipctl.wrap(cause["detail"]))
        rows.extend(flipctl.text(line) for line in flipctl.wrap(cause["recommendation"]))
    for finding in result.findings:
        rows.append(flipctl.rule())
        rows.append(flipctl.text(f"{finding.severity.upper()}: {finding.title}"))
        if finding.detail:
            rows.extend(flipctl.text(line, dim=True) for line in flipctl.wrap(finding.detail))
        if finding.recommendation:
            rows.extend(flipctl.text(line, dim=True) for line in flipctl.wrap(finding.recommendation))
    rows.append(flipctl.rule())
    rows.append(flipctl.text("Local configuration only; no DHCP, DNS or gateway probes.", dim=True))
    rows.append(flipctl.pair("Saved", saved, dim=True))
    state["detail_rows"] = rows
    state["detail_refresh"] = show_local_check
    detail.show()


def show_routes():
    """Show local IPv4 and IPv6 default routes without probing gateways."""
    result = collect_default_routes()
    saved = persist(result)
    rows = [flipctl.heading("Default routes", result.status.upper())]
    for route in result.data.get("routes", []):
        rows.append(flipctl.rule())
        rows.append(flipctl.heading(route["family"], route.get("device") or "no device"))
        rows.append(flipctl.pair("Gateway", route.get("gateway") or "on-link"))
        rows.append(flipctl.pair("Metric", str(route["metric"] if route.get("metric") is not None else "-")))
        rows.append(flipctl.pair("Protocol", route.get("protocol") or "-"))
    if not result.data.get("routes"):
        rows.append(flipctl.text("No default route found."))
    for finding in result.findings:
        rows.append(flipctl.text(finding.title))
        if finding.recommendation:
            rows.extend(flipctl.text(line, dim=True) for line in flipctl.wrap(finding.recommendation))
    for note in result.limitations:
        rows.append(flipctl.text(note, dim=True))
    rows.append(flipctl.pair("Saved", saved, dim=True))
    state["detail_rows"] = rows
    state["detail_refresh"] = show_routes
    detail.show()


def show_dns():
    """Show local resolver settings; no DNS request is sent."""
    result = collect_dns_config()
    saved = persist(result)
    data = result.data
    rows = [flipctl.heading("DNS configuration", result.status.upper())]
    rows.append(flipctl.rule())
    for index, server in enumerate(data.get("nameservers", []), start=1):
        rows.append(flipctl.pair(f"DNS {index}", server))
    for domain in data.get("search_domains", []):
        rows.append(flipctl.pair("Search", domain))
    if data.get("local_stub"):
        rows.append(flipctl.text("Local resolver stub; upstream servers not shown.", dim=True))
    if not data.get("nameservers"):
        rows.append(flipctl.text("No valid nameserver configured."))
    for finding in result.findings:
        rows.append(flipctl.text(finding.title))
        if finding.detail:
            rows.extend(flipctl.text(line) for line in flipctl.wrap(finding.detail))
    for note in result.limitations:
        rows.append(flipctl.text(note, dim=True))
    rows.append(flipctl.pair("Saved", saved, dim=True))
    state["detail_rows"] = rows
    state["detail_refresh"] = show_dns
    detail.show()



def wired_gateway_route():
    """Return the default route that uses a confirmed wired Ethernet interface."""
    wired_names = {item["name"] for item in ethernet_interfaces()}
    result = collect_default_routes()
    candidates = [
        route
        for route in result.data.get("routes", [])
        if route.get("device") in wired_names and route.get("gateway")
    ]
    candidates.sort(
        key=lambda route: (
            route.get("family") != "inet",
            route.get("metric") if route.get("metric") is not None else 0,
        )
    )
    return candidates[0] if candidates else None


def show_active_confirmation(title, target, interface, description, action):
    """Present a one-shot confirmation before any active packet is sent."""
    state["confirm_rows"] = [
        flipctl.heading(title, "ACTIVE"),
        flipctl.rule(),
        flipctl.pair("Target", target),
        flipctl.pair("Interface", interface or "-"),
        flipctl.text(description),
        flipctl.rule(),
        flipctl.text("This action sends traffic to one target only."),
        flipctl.text("No scan, background task or automatic retry."),
        flipctl.text("Press Confirm to send, or Cancel to return."),
    ]
    state["pending_active_action"] = action
    confirm_detail.show()


def render_active_result(title, result):
    saved = persist(result)
    rows = [flipctl.heading(title, result.status.upper())]
    for key in ("target", "ip_version", "port", "connected", "packets_transmitted",
                "packets_received", "packet_loss_percent", "rtt_avg_ms",
                "timeout_seconds"):
        if key in result.data:
            label = key.replace("_", " ").title()
            value = result.data[key]
            if key == "rtt_avg_ms" and value is not None:
                value = f"{value} ms"
            rows.append(flipctl.pair(label, str(value)))
    for finding in result.findings:
        rows.append(flipctl.rule())
        rows.append(flipctl.text(f"{finding.severity.upper()}: {finding.title}"))
        if finding.detail:
            rows.extend(flipctl.text(line, dim=True) for line in flipctl.wrap(finding.detail))
        if finding.recommendation:
            rows.extend(flipctl.text(line) for line in flipctl.wrap(finding.recommendation))
    for note in result.limitations:
        rows.append(flipctl.text(note, dim=True))
    rows.append(flipctl.pair("Saved", saved, dim=True))
    state["detail_rows"] = rows
    state["detail_refresh"] = None
    detail.show()


def run_confirmed_active_action():
    action = state.pop("pending_active_action", None)
    if action is None:
        main_menu.show()
        return
    try:
        result, title = action()
    except Exception as exc:
        state["detail_rows"] = [
            flipctl.heading("Active test failed", "ERROR"),
            flipctl.text(type(exc).__name__),
            flipctl.text("No retry was attempted."),
        ]
        state["detail_refresh"] = None
        detail.show()
        return
    render_active_result(title, result)


def show_ping_gateway_confirmation():
    route = wired_gateway_route()
    if route is None:
        state["detail_rows"] = [
            flipctl.heading("Ping gateway", "UNAVAILABLE"),
            flipctl.text("No default gateway was found on a confirmed wired Ethernet interface."),
            flipctl.text("Connect the wired port and check its route before testing."),
        ]
        state["detail_refresh"] = None
        detail.show()
        return

    target = route["gateway"]
    interface = route.get("device") or "-"
    def action():
        address = ipaddress.ip_address(target)
        prefix = 32 if address.version == 4 else 128
        authorization = ActiveAuthorization(
            purpose="one-shot wired gateway ICMP test",
            scope=f"{address}/{prefix}",
            targets=(str(address),),
            confirmed=True,
        )
        result = run_ping(
            str(address),
            authorization=authorization,
            safe_mode=False,
            count=3,
            timeout_seconds=1,
        )
        return result, "ICMP gateway test"

    show_active_confirmation(
        "Confirm ICMP test",
        target,
        interface,
        "Will send 3 ICMP echo requests with a 1-second per-request timeout.",
        action,
    )


def tcp_port_items():
    return [
        flipctl.item("DNS", status="TCP 53"),
        flipctl.item("HTTP", status="TCP 80"),
        flipctl.item("HTTPS", status="TCP 443"),
        flipctl.item("SSH", status="TCP 22"),
    ]


def show_tcp_gateway_confirmation(port):
    route = wired_gateway_route()
    if route is None:
        state["detail_rows"] = [
            flipctl.heading("TCP gateway test", "UNAVAILABLE"),
            flipctl.text("No default gateway was found on a confirmed wired Ethernet interface."),
        ]
        state["detail_refresh"] = None
        detail.show()
        return

    target = route["gateway"]
    interface = route.get("device") or "-"
    def action():
        address = ipaddress.ip_address(target)
        prefix = 32 if address.version == 4 else 128
        authorization = ActiveAuthorization(
            purpose=f"one-shot wired TCP connect to port {port}",
            scope=f"{address}/{prefix}",
            targets=(str(address),),
            confirmed=True,
            ports=(port,),
        )
        result = run_tcp_connect(
            str(address),
            port,
            authorization=authorization,
            safe_mode=False,
            timeout_seconds=3,
        )
        return result, f"TCP gateway port {port}"

    show_active_confirmation(
        f"Confirm TCP port {port}",
        target,
        interface,
        f"Will attempt one TCP handshake to {target}:{port}. No application payload will be sent.",
        action,
    )


def show_history():
    """Show the newest local diagnostic runs."""
    try:
        results = list_results(default_database_path(), limit=12)
    except Exception as exc:
        state["history_lines"] = [f"History unavailable: {type(exc).__name__}"]
    else:
        lines = []
        for item in results:
            timestamp = item.get("started_at", "").replace("T", " ")[:19]
            interface = item.get("interface") or "-"
            lines.append(
                f"{timestamp} {item.get('status', '?')} "
                f"{item.get('collector', '?')} {interface}"
            )
        state["history_lines"] = lines or ["No diagnostic runs saved yet."]
    history.offset = 0
    history.show()


def menu_items():
    count = len(state["interfaces"])
    ethernet_count = len(ethernet_interfaces())
    return [
        flipctl.item("Interfaces", status=f"{count} found"),
        flipctl.item("Ethernet link", status=f"{ethernet_count} ports"),
        flipctl.item("Local Check", status="No probes"),
        flipctl.item("Ping wired gateway", status="3 ICMP requests"),
        flipctl.item("TCP gateway port", status="One port at a time"),
        flipctl.item("Default route", status="IPv4 / IPv6"),
        flipctl.item("DNS config", status="Local"),
        flipctl.item("History", status="Local"),
        flipctl.item("Safe Mode", status="ON"),
        flipctl.item("About", status="v0.5"),
    ]


def link_menu_items():
    ports = ethernet_interfaces()
    if not ports:
        return [flipctl.item("No Ethernet interfaces", status="none", dim=True)]
    return [
        flipctl.item(
            interface["name"],
            status=interface.get("operstate") or "unknown",
        )
        for interface in ports
    ]


def show_safe_mode():
    state["detail_rows"] = [
        flipctl.heading("Safe Mode", "ON"),
        flipctl.rule(),
        flipctl.text("Safe Mode is ON by default."),
        flipctl.text("Active tests require a one-shot on-device confirmation."),
        flipctl.text("Only one gateway IP and one selected TCP port are tested."),
        flipctl.text("No subnet scans, background tests or automatic retries."),
        flipctl.rule(),
        flipctl.pair("Interface inventory", "read-only"),
        flipctl.pair("Ethernet link", "read-only"),
        flipctl.pair("Database", "local SQLite"),
        flipctl.text("Active tests require a separate authorization workflow."),
    ]
    state["detail_refresh"] = show_safe_mode
    detail.show()


def show_about():
    state["detail_rows"] = [
        flipctl.heading("Network Diagnostics", "v0.5"),
        flipctl.text("Designed for standalone Flipper One use."),
        flipctl.rule(),
        flipctl.pair("Control", "device keys"),
        flipctl.pair("Storage", "local SQLite"),
        flipctl.pair("Network mode", "passive + confirmed one-shot tests"),
        flipctl.pair("PC required", "no; target validation pending"),
        flipctl.rule(),
        flipctl.text("Optional PC/browser tools are not needed for normal use."),
    ]
    state["detail_refresh"] = show_about
    detail.show()


def open_selected(menu):
    if menu is main_menu:
        selected = menu.selected
        if selected == 0:
            refresh_interfaces()
            detail.show()
        elif selected == 1:
            refresh_interfaces()
            link_menu.selected = 0
            link_menu.show()
        elif selected == 2:
            show_local_check()
        elif selected == 3:
            show_ping_gateway_confirmation()
        elif selected == 4:
            tcp_port_menu.selected = 0
            tcp_port_menu.show()
        elif selected == 5:
            show_routes()
        elif selected == 6:
            show_dns()
        elif selected == 7:
            show_history()
        elif selected == 8:
            show_safe_mode()
        elif selected == 9:
            show_about()
    elif menu is link_menu:
        ports = ethernet_interfaces()
        if ports and menu.selected < len(ports):
            refresh_link(ports[menu.selected])


def main():
    global main_menu, link_menu, detail, history, confirm_detail, tcp_port_menu

    detail = flipctl.Detail(
        rows=lambda: state["detail_rows"],
        buttons=["Menu", "Refresh", "", "", ""],
        fit_gauges=True,
    )

    @detail.on_key
    def detail_keys(key):
        if key is flipctl.Key.ESCAPE:
            main_menu.show()
            return True
        if key is flipctl.Key.VIEW and state["detail_refresh"]:
            state["detail_refresh"]()
            return True
        return False

    confirm_detail = flipctl.Detail(
        rows=lambda: state["confirm_rows"],
        buttons=["Cancel", "", "", "", "Confirm"],
        fit_gauges=True,
    )

    @confirm_detail.on_key
    def confirm_detail_keys(key):
        if key in (flipctl.Key.ESCAPE, flipctl.Key.POWER):
            state["pending_active_action"] = None
            main_menu.show()
            return True
        if key is flipctl.Key.RUN:
            run_confirmed_active_action()
            return True
        return False

    tcp_port_menu = flipctl.Menu(
        items=tcp_port_items,
        buttons=["Menu", "", "", "", "Select"],
    )

    @tcp_port_menu.on_key
    def tcp_port_menu_keys(key):
        if key is flipctl.Key.ESCAPE:
            main_menu.show()
            return True
        if key in (flipctl.Key.OK, flipctl.Key.RUN):
            ports = [53, 80, 443, 22]
            if tcp_port_menu.selected < len(ports):
                show_tcp_gateway_confirmation(ports[tcp_port_menu.selected])
            return True
        return False

    history = flipctl.Log(
        lines=lambda: [
            part
            for line in state["history_lines"]
            for part in flipctl.wrap(line)
        ],
        title="Local history",
        buttons=["Menu", "", "", "", "Refresh"],
    )

    @history.on_key
    def history_keys(key):
        if key is flipctl.Key.ESCAPE:
            main_menu.show()
            return True
        if key is flipctl.Key.RUN:
            show_history()
            return True
        return False

    link_menu = flipctl.Menu(
        items=link_menu_items,
        buttons=["Menu", "Refresh", "", "", "Test"],
    )

    @link_menu.on_key
    def link_menu_keys(key):
        if key is flipctl.Key.ESCAPE:
            main_menu.show()
            return True
        if key is flipctl.Key.VIEW:
            refresh_interfaces()
            link_menu.redraw()
            return True
        if key in (flipctl.Key.OK, flipctl.Key.RUN):
            open_selected(link_menu)
            return True
        return False

    main_menu = flipctl.Menu(
        items=menu_items,
        buttons=["Close", "Refresh", "Safe", "History", "Open"],
    )

    @main_menu.on_key
    def main_menu_keys(key):
        if key is flipctl.Key.VIEW:
            refresh_interfaces()
            main_menu.redraw()
            return True
        if key is flipctl.Key.POWER:
            show_safe_mode()
            return True
        if key is flipctl.Key.EDIT:
            show_history()
            return True
        if key in (flipctl.Key.OK, flipctl.Key.RUN):
            open_selected(main_menu)
            return True
        return False

    refresh_interfaces()
    main_menu.run()


if __name__ == "__main__":
    main()
