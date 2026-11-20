"""Read-only Ethernet link status collector using ethtool."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

from .models import DiagnosticResult, Finding

INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,15}$")
COMMAND_TIMEOUT_SECONDS = 5


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
    return fields


def collect_link_status(interface: str) -> DiagnosticResult:
    """Query one local interface; does not transmit diagnostic network probes."""
    if not INTERFACE_PATTERN.fullmatch(interface):
        raise ValueError("invalid interface name")

    executable = shutil.which("ethtool")
    if executable is None:
        return DiagnosticResult(
            collector="linux.ethtool",
            status="error",
            interface=interface,
            findings=[
                Finding(
                    code="COLLECTOR-TOOL-MISSING",
                    severity="warning",
                    title="ethtool is not installed",
                    recommendation="Install ethtool on the target Linux system.",
                )
            ],
        )

    try:
        completed = subprocess.run(
            [executable, interface],
            check=False,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return DiagnosticResult(
            collector="linux.ethtool",
            status="error",
            interface=interface,
            limitations=["The local ethtool query exceeded the 5 second timeout."],
        )
    except OSError as exc:
        return DiagnosticResult(
            collector="linux.ethtool",
            status="error",
            interface=interface,
            limitations=[f"Unable to execute ethtool: {exc.__class__.__name__}"],
        )

    if completed.returncode != 0:
        return DiagnosticResult(
            collector="linux.ethtool",
            status="error",
            interface=interface,
            data={"returncode": completed.returncode, "stderr": completed.stderr[:1000]},
            limitations=["ethtool returned a non-zero exit status."],
        )

    try:
        data = parse_ethtool_output(completed.stdout)
    except ValueError as exc:
        return DiagnosticResult(
            collector="linux.ethtool",
            status="error",
            interface=interface,
            limitations=[str(exc)],
        )

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
