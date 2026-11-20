"""Read-only inventory of the local Linux IPv4/IPv6 neighbor cache."""

from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
from typing import Any

from .models import DiagnosticResult, Finding

COMMAND_TIMEOUT_SECONDS = 5
USABLE_STATES = {"REACHABLE", "STALE", "DELAY", "PROBE", "PERMANENT"}


def parse_neighbor_json(payload: str, *, family: str) -> list[dict[str, Any]]:
    if family not in ("inet", "inet6"):
        raise ValueError("family must be 'inet' or 'inet6'")
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("iproute2 returned invalid neighbor JSON") from exc
    if not isinstance(raw, list):
        raise ValueError("iproute2 neighbor JSON root must be an array")

    neighbors = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each neighbor must be an object")
        destination = item.get("dst")
        if not isinstance(destination, str):
            continue
        try:
            address = ipaddress.ip_address(destination)
        except ValueError as exc:
            raise ValueError("neighbor destination must be an IP address") from exc
        expected_version = 4 if family == "inet" else 6
        if address.version != expected_version:
            raise ValueError("neighbor address does not match address family")

        raw_state = item.get("state", [])
        if isinstance(raw_state, str):
            states = [raw_state.upper()]
        elif isinstance(raw_state, list):
            states = [str(state).upper() for state in raw_state]
        else:
            raise ValueError("neighbor state must be a string or list")
        states = sorted(set(states))
        neighbors.append(
            {
                "family": family,
                "ip": str(address),
                "mac_address": item.get("lladdr"),
                "interface": item.get("dev"),
                "state": states,
                "usable": any(state in USABLE_STATES for state in states),
                "router": bool(item.get("router", False)),
            }
        )
    return neighbors


def collect_neighbor_cache() -> DiagnosticResult:
    """Read cached neighbors only; this collector does not discover or probe peers."""
    executable = shutil.which("ip")
    if executable is None:
        return DiagnosticResult(
            collector="linux.neighbor_cache",
            status="error",
            findings=[
                Finding(
                    code="COLLECTOR-TOOL-MISSING",
                    severity="warning",
                    title="iproute2 is not installed",
                    recommendation="Install iproute2 on the target Linux system.",
                )
            ],
            limitations=["The collector requires the local ip executable."],
        )

    neighbors: list[dict[str, Any]] = []
    limitations: list[str] = []
    for arguments, family in (
        (["-j", "neigh", "show"], "inet"),
        (["-6", "-j", "neigh", "show"], "inet6"),
    ):
        command = [executable, *arguments]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            limitations.append(f"The {family} neighbor-cache query exceeded 5 seconds.")
            continue
        except OSError as exc:
            limitations.append(
                f"Unable to execute the {family} neighbor-cache query: {exc.__class__.__name__}."
            )
            continue

        if completed.returncode != 0:
            limitations.append(f"The {family} neighbor-cache query returned a non-zero exit status.")
            continue
        try:
            neighbors.extend(parse_neighbor_json(completed.stdout, family=family))
        except ValueError as exc:
            limitations.append(f"The {family} neighbor-cache response could not be parsed: {exc}")

    findings = []
    for neighbor in neighbors:
        if any(state in ("FAILED", "INCOMPLETE") for state in neighbor["state"]):
            findings.append(
                Finding(
                    code="NEIGHBOR-UNRESOLVED",
                    severity="info",
                    title="Neighbor entry is unresolved",
                    detail=f"{neighbor['ip']} on {neighbor.get('interface') or 'unknown interface'} has state {', '.join(neighbor['state'])}.",
                    recommendation="The cache entry may resolve after ordinary network traffic; this tool does not trigger discovery.",
                )
            )

    return DiagnosticResult(
        collector="linux.neighbor_cache",
        status="ok" if neighbors or not limitations else "warning",
        data={
            "neighbors": neighbors,
            "count": len(neighbors),
            "usable_count": sum(item["usable"] for item in neighbors),
        },
        findings=findings,
        limitations=limitations
        + [
            "Kernel neighbor cache only; this is not a LAN discovery scan and may omit silent or expired devices."
        ],
    )
