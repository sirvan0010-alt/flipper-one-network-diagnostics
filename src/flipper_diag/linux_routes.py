"""Read-only default-route inventory using iproute2 JSON output."""

from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
from typing import Any

from .models import DiagnosticResult, Finding

COMMAND_TIMEOUT_SECONDS = 5


def parse_default_routes(payload: str, *, family: str) -> list[dict[str, Any]]:
    """Normalize default routes from one iproute2 JSON response."""
    if family not in ("inet", "inet6"):
        raise ValueError("family must be 'inet' or 'inet6'")
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("iproute2 returned invalid route JSON") from exc
    if not isinstance(raw, list):
        raise ValueError("iproute2 route JSON root must be an array")

    routes: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each route must be an object")
        destination = item.get("dst", "default")
        if destination not in ("default", "0.0.0.0/0", "::/0"):
            continue

        gateway = item.get("gateway")
        if gateway is not None:
            if not isinstance(gateway, str):
                raise ValueError("route gateway must be an IP address")
            try:
                address = ipaddress.ip_address(gateway)
            except ValueError as exc:
                raise ValueError("route gateway must be an IP address") from exc
            expected_version = 4 if family == "inet" else 6
            if address.version != expected_version:
                raise ValueError("route gateway does not match address family")

        dev = item.get("dev")
        if dev is not None and not isinstance(dev, str):
            raise ValueError("route device must be a string")

        metric = item.get("metric")
        if metric is not None and (
            not isinstance(metric, int) or isinstance(metric, bool) or metric < 0
        ):
            raise ValueError("route metric must be a non-negative integer")

        routes.append(
            {
                "family": family,
                "destination": "default",
                "gateway": gateway,
                "device": dev,
                "metric": metric,
                "protocol": item.get("protocol"),
                "table": item.get("table"),
                "preferred_source": item.get("prefsrc"),
            }
        )
    return routes


def collect_default_routes() -> DiagnosticResult:
    """Read IPv4 and IPv6 default routes; this collector sends no packets."""
    executable = shutil.which("ip")
    if executable is None:
        return DiagnosticResult(
            collector="linux.default_routes",
            status="error",
            findings=[
                Finding(
                    code="COLLECTOR-TOOL-MISSING",
                    severity="warning",
                    title="iproute2 is not installed",
                    recommendation="Install iproute2 on the target Linux system.",
                )
            ],
            limitations=["The collector requires the local 'ip' executable."],
        )

    routes: list[dict[str, Any]] = []
    limitations: list[str] = []
    commands = (
        (["-j", "route", "show", "default"], "inet"),
        (["-6", "-j", "route", "show", "default"], "inet6"),
    )
    for arguments, family in commands:
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
            limitations.append(f"The {family} route query exceeded 5 seconds.")
            continue
        except OSError as exc:
            limitations.append(
                f"Unable to execute the {family} route query: {exc.__class__.__name__}."
            )
            continue

        if completed.returncode != 0:
            limitations.append(f"The {family} route query returned a non-zero exit status.")
            continue
        try:
            routes.extend(parse_default_routes(completed.stdout, family=family))
        except ValueError as exc:
            limitations.append(f"The {family} route response could not be parsed: {exc}")

    findings: list[Finding] = []
    if not routes:
        findings.append(
            Finding(
                code="ROUTE-DEFAULT-MISSING",
                severity="warning",
                title="No default route found",
                detail="No IPv4 or IPv6 default route was returned by the local routing table.",
                recommendation="Check the active network profile, DHCP configuration and gateway settings.",
            )
        )
    status = "ok" if routes else "warning"
    if limitations and not routes:
        status = "error"

    return DiagnosticResult(
        collector="linux.default_routes",
        status=status,
        data={
            "routes": routes,
            "count": len(routes),
            "ipv4_count": sum(route["family"] == "inet" for route in routes),
            "ipv6_count": sum(route["family"] == "inet6" for route in routes),
        },
        findings=findings,
        limitations=limitations
        + ["Local routing-table inspection only; gateway reachability is not tested."],
    )
