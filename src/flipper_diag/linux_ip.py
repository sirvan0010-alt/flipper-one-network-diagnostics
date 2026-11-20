"""Read-only Linux interface inventory based on `ip -j address show`."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .models import DiagnosticResult, Finding

COMMAND_TIMEOUT_SECONDS = 5
SYS_CLASS_NET = Path("/sys/class/net")


def parse_ip_address_json(payload: str) -> list[dict[str, Any]]:
    """Normalize JSON output from iproute2 without querying the network."""
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("iproute2 returned invalid JSON") from exc
    if not isinstance(raw, list):
        raise ValueError("iproute2 JSON root must be an array")

    interfaces: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("ifname"), str):
            raise ValueError("each interface must be an object with an ifname")
        addresses = []
        for address in item.get("addr_info", []):
            if not isinstance(address, dict):
                continue
            addresses.append(
                {
                    key: address[key]
                    for key in ("family", "local", "prefixlen", "scope", "broadcast")
                    if key in address
                }
            )
        interfaces.append(
            {
                "name": item["ifname"],
                "link_type": item.get("link_type"),
                "mac_address": item.get("address"),
                "operstate": item.get("operstate"),
                "mtu": item.get("mtu"),
                "flags": item.get("flags", []),
                "addresses": addresses,
            }
        )
    return interfaces


def _is_wireless_interface(interface_name: str) -> bool | None:
    """Return wireless state from sysfs; None means it cannot be classified."""
    interface_path = SYS_CLASS_NET / interface_name
    if not interface_path.is_dir():
        return None
    return (interface_path / "wireless").is_dir()


def collect_ip_interfaces() -> DiagnosticResult:
    """Run a bounded, read-only local iproute2 query and return normalized data."""
    executable = shutil.which("ip")
    if executable is None:
        return DiagnosticResult(
            collector="linux.ip_address",
            status="error",
            findings=[
                Finding(
                    code="COLLECTOR-TOOL-MISSING",
                    severity="warning",
                    title="iproute2 is not installed",
                    recommendation="Install the iproute2 package on the target Linux system.",
                )
            ],
            limitations=["The collector requires the local 'ip' executable."],
        )

    try:
        completed = subprocess.run(
            [executable, "-j", "address", "show"],
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return DiagnosticResult(
            collector="linux.ip_address",
            status="error",
            limitations=["The local iproute2 query exceeded the 5 second timeout."],
        )
    except OSError as exc:
        return DiagnosticResult(
            collector="linux.ip_address",
            status="error",
            limitations=[f"Unable to execute iproute2: {exc.__class__.__name__}"],
        )

    if completed.returncode != 0:
        return DiagnosticResult(
            collector="linux.ip_address",
            status="error",
            limitations=["iproute2 returned a non-zero exit status."],
            data={"returncode": completed.returncode, "stderr": completed.stderr[:1000]},
        )

    try:
        interfaces = parse_ip_address_json(completed.stdout)
        for interface in interfaces:
            interface["wireless"] = _is_wireless_interface(interface["name"])
    except ValueError as exc:
        return DiagnosticResult(
            collector="linux.ip_address",
            status="error",
            limitations=[str(exc)],
        )

    return DiagnosticResult(
        collector="linux.ip_address",
        status="ok",
        data={"interfaces": interfaces, "count": len(interfaces)},
        limitations=["Interface inventory only; no connectivity test is performed."],
    )
