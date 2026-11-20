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

import sqlite3

import flipctl

from flipper_diag.linux_ethtool import collect_link_status
from flipper_diag.linux_ip import collect_ip_interfaces
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
    except (OSError, sqlite3.Error) as exc:
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


def show_history():
    """Show the newest local diagnostic runs."""
    try:
        results = list_results(default_database_path(), limit=12)
    except (OSError, sqlite3.Error) as exc:
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
        flipctl.item("History", status="Local"),
        flipctl.item("Safe Mode", status="ON"),
        flipctl.item("About", status="v0.1"),
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
        flipctl.heading("Network Diagnostics", "v0.1"),
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
            show_history()
        elif selected == 3:
            show_safe_mode()
        elif selected == 4:
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
