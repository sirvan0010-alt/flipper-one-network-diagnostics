"""Read-only Ethernet link status collector with an ethtool/sysfs fallback."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .models import DiagnosticResult, Finding

INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,15}$")
COMMAND_TIMEOUT_SECONDS = 5
SYS_CLASS_NET = Path("/sys/class/net")


def parse_ethtool_output(output: str) -> dict[str, Any]:
    """Parse the stable human-readable fields emitted by ethtool."""
    fields: dict[str, Any] = {}
    patterns = {
        "speed_mbps": re.compile(r"^\s*Speed:\s*(\d+)Mb/s\s*$", re.MULTILINE),
        "duplex": re.compile(r"^\s*Duplex:\s*(Half|Full|Unknown)\s*$", re.MULTILINE),
        "auto_negotiation": re.compile(r"^\s*Auto-negotiation:\s*(on|off)\s*$", re.MULTILINE),
        "link_detected": re.compile(r"^\s*Link detected:\s*(yes|no)\s*$", re.MULTILINE),
    }
    for key, pattern in patterns.items():
        match = pattern.search(output)
        if match:
            value = match.group(1)
            if key == "speed_mbps":
                fields[key] = int(value)
            elif key == "auto_negotiation":
                fields[key] = value == "on"
            elif key == "link_detected":
                fields[key] = value == "yes"
            else:
                fields[key] = value.lower()
    if "link_detected" not in fields:
        raise ValueError("ethtool output does not contain 'Link detected'")
    fields["source"] = "ethtool"
    return fields


def _collect_sysfs_link_status(interface: str) -> DiagnosticResult:
    """Fallback to standard kernel sysfs attributes when ethtool is absent."""
    interface_path = SYS_CLASS_NET / interface
    if not interface_path.is_dir():
        return DiagnosticResult(
            collector="linux.sysfs_link",
            status="error",
            interface=interface,
            findings=[
                Finding(
                    code="ETH-LINK-STATUS-UNAVAILABLE",
                    severity="warning",
                    title="Ethernet link status is unavailable",
                    detail=f"No sysfs network device was found for {interface}.",
                    recommendation="Check the interface name and kernel driver.",
                )
            ],
        )

    def read_attribute(name: str) -> str | None:
        try:
            return (interface_path / name).read_text(encoding="utf-8").strip()
        except OSError:
            return None

    operstate = read_attribute("operstate")
    carrier_raw = read_attribute("carrier")
    speed_raw = read_attribute("speed")
    duplex_raw = read_attribute("duplex")

    carrier = carrier_raw if carrier_raw in ("0", "1") else None
    speed = None
    if speed_raw is not None:
        try:
            parsed_speed = int(speed_raw)
            if parsed_speed > 0:
                speed = parsed_speed
        except ValueError:
            pass
    duplex = (
        duplex_raw.lower()
        if duplex_raw and duplex_raw.lower() in ("full", "half")
        else None
    )
    link_detected = carrier == "1" if carrier is not None else None

    findings = []
    status = "ok"
    if carrier == "0" or operstate == "down":
        status = "warning"
        findings.append(
            Finding(
                code="ETH-LINK-DOWN",
                severity="warning",
                title="Ethernet link is down",
                detail=f"The kernel reports no active carrier on {interface}.",
                recommendation="Check cable seating, remote port power and switch configuration.",
            )
        )
    elif carrier is None:
        status = "warning"
        findings.append(
            Finding(
                code="ETH-LINK-STATUS-UNAVAILABLE",
                severity="warning",
                title="Kernel carrier state is unavailable",
                detail=f"The driver did not expose a valid carrier attribute for {interface}.",
                recommendation="Use ethtool if it is supported by the target image and driver.",
            )
        )

    return DiagnosticResult(
        collector="linux.sysfs_link",
        status=status,
        interface=interface,
        data={
            "link_detected": link_detected,
            "speed_mbps": speed,
            "duplex": duplex,
            "auto_negotiation": None,
            "operstate": operstate,
            "source": "sysfs",
        },
        findings=findings,
        limitations=[
            "Kernel sysfs fallback; auto-negotiation details and cable wiremap/TDR are not available."
        ],
    )


def collect_link_status(interface: str) -> DiagnosticResult:
    """Query one local interface; does not transmit diagnostic network probes."""
    if interface in (".", "..") or not INTERFACE_PATTERN.fullmatch(interface):
        raise ValueError("invalid interface name")

    executable = shutil.which("ethtool")
    if executable is None:
        return _collect_sysfs_link_status(interface)

    try:
        completed = subprocess.run(
            [executable, interface],
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return _collect_sysfs_link_status(interface)
    except OSError:
        return _collect_sysfs_link_status(interface)

    if completed.returncode != 0:
        return _collect_sysfs_link_status(interface)

    try:
        data = parse_ethtool_output(completed.stdout)
    except ValueError:
        return _collect_sysfs_link_status(interface)

    findings = []
    status = "ok"
    if not data["link_detected"]:
        status = "warning"
        findings.append(
            Finding(
                code="ETH-LINK-DOWN",
                severity="warning",
                title="Ethernet link is down",
                detail=f"No physical link is detected on {interface}.",
                recommendation="Check cable seating, remote port power and switch configuration.",
            )
        )
    return DiagnosticResult(
        collector="linux.ethtool",
        status=status,
        interface=interface,
        data=data,
        findings=findings,
        limitations=["Link status only; no cable wiremap, TDR or PoE load test is performed."],
    )
