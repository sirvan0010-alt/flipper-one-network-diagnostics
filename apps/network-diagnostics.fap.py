#!/usr/bin/env python3
# /// flipctl
# name = "Network Diagnostics"
# status = true
# ///
"""Local-first network diagnostics for the Flipper One panel.

This first device UI is deliberately read-only: it inventories local interfaces,
queries Ethernet link state, and stores results locally. It does not scan or probe
other devices on the network.
"""

from __future__ import annotations

import flipctl

from flipper_diag.linux_dns import collect_dns_config
from flipper_diag.linux_ethtool import collect_link_status
from flipper_diag.linux_ip import collect_ip_interfaces
from flipper_diag.linux_routes import collect_default_routes
from flipper_diag.local_check import collect_local_check
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
        if item.get("link_type") == "ether"
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
    rows.append(flipctl.pair("Ethernet", statuses.get("interfaces", "unknown")))
    rows.append(flipctl.pair("Link", statuses.get("link", "unknown")))
    rows.append(flipctl.pair("Default route", statuses.get("routes", "unknown")))
    rows.append(flipctl.pair("DNS config", statuses.get("dns", "unknown")))
    if result.interface:
        rows.append(flipctl.pair("Interface", result.interface))
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
        flipctl.item("Default route", status="IPv4 / IPv6"),
        flipctl.item("DNS config", status="Local"),
        flipctl.item("History", status="Local"),
        flipctl.item("Safe Mode", status="ON"),
        flipctl.item("About", status="v0.2"),
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
        flipctl.text("Active network tests are disabled."),
        flipctl.text("No scans or probes are sent."),
        flipctl.text("Current collectors only read local OS state."),
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
        flipctl.heading("Network Diagnostics", "v0.2"),
        flipctl.text("Standalone Flipper One app."),
        flipctl.rule(),
        flipctl.pair("Control", "device keys"),
        flipctl.pair("Storage", "local SQLite"),
        flipctl.pair("Network mode", "passive/read-only"),
        flipctl.pair("PC required", "no"),
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
            show_routes()
        elif selected == 4:
            show_dns()
        elif selected == 5:
            show_history()
        elif selected == 6:
            show_safe_mode()
        elif selected == 7:
            show_about()
    elif menu is link_menu:
        ports = ethernet_interfaces()
        if ports and menu.selected < len(ports):
            refresh_link(ports[menu.selected])


def main():
    global main_menu, link_menu, detail, history

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
