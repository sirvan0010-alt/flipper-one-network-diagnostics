"""Explicitly authorized, single-target ICMP echo diagnostics."""

from __future__ import annotations

import ipaddress
import re
import shutil
import subprocess
from typing import Any

from .models import DiagnosticResult, Finding
from .safety import ActiveAuthorization, require_active_allowed

MAX_PING_COUNT = 5
MAX_TIMEOUT_SECONDS = 5


def parse_ping_output(output: str) -> dict[str, Any]:
    """Parse iputils/BusyBox packet summary and optional RTT statistics."""
    packet_match = re.search(
        r"(\d+)\s+packets? transmitted,\s*(\d+)\s+(?:packets?\s+)?received,\s*([\d.]+)% packet loss",
        output,
        re.IGNORECASE,
    )
    if not packet_match:
        raise ValueError("ping output does not contain a recognized packet summary")

    data: dict[str, Any] = {
        "packets_transmitted": int(packet_match.group(1)),
        "packets_received": int(packet_match.group(2)),
        "packet_loss_percent": float(packet_match.group(3)),
        "rtt_min_ms": None,
        "rtt_avg_ms": None,
        "rtt_max_ms": None,
        "rtt_mdev_ms": None,
    }
    rtt_match = re.search(
        r"(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*"
        r"([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)\s*ms",
        output,
        re.IGNORECASE,
    )
    if rtt_match:
        data["rtt_min_ms"] = float(rtt_match.group(1))
        data["rtt_avg_ms"] = float(rtt_match.group(2))
        data["rtt_max_ms"] = float(rtt_match.group(3))
        data["rtt_mdev_ms"] = float(rtt_match.group(4))
    return data


def run_ping(
    target: str,
    *,
    authorization: ActiveAuthorization | None = None,
    safe_mode: bool = True,
    count: int = 3,
    timeout_seconds: int = 1,
) -> DiagnosticResult:
    """Ping one literal IP target; Safe Mode blocks this unless explicitly authorized."""
    if not isinstance(target, str):
        raise ValueError("target must be a literal IPv4 or IPv6 address")
    try:
        address = ipaddress.ip_address(target)
    except ValueError as exc:
        raise ValueError("target must be a literal IPv4 or IPv6 address; hostnames are not accepted") from exc

    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= MAX_PING_COUNT:
        raise ValueError(f"count must be an integer between 1 and {MAX_PING_COUNT}")
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS
    ):
        raise ValueError(
            f"timeout_seconds must be an integer between 1 and {MAX_TIMEOUT_SECONDS}"
        )

    require_active_allowed(
        safe_mode=safe_mode,
        authorization=authorization,
        target=str(address),
    )

    executable = shutil.which("ping")
    if executable is None:
        return DiagnosticResult(
            collector="linux.ping",
            status="error",
            interface=None,
            data={"target": str(address), "count": count, "timeout_seconds": timeout_seconds},
            findings=[
                Finding(
                    code="COLLECTOR-TOOL-MISSING",
                    severity="warning",
                    title="ping is not installed",
                    recommendation="Install iputils-ping or the supported BusyBox ping applet.",
                )
            ],
            limitations=["No ICMP packet was sent because the ping executable is unavailable."],
        )

    command = [executable, "-n", "-q"]
    if address.version == 6:
        command.append("-6")
    command.extend(
        ["-c", str(count), "-W", str(timeout_seconds), str(address)]
    )

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=(count * timeout_seconds) + 3,
        )
    except subprocess.TimeoutExpired:
        return DiagnosticResult(
            collector="linux.ping",
            status="warning",
            data={
                "target": str(address),
                "ip_version": address.version,
                "count": count,
                "timeout_seconds": timeout_seconds,
            },
            findings=[
                Finding(
                    code="PING-COLLECTOR-TIMEOUT",
                    severity="warning",
                    title="Ping command exceeded its time limit",
                    recommendation="Check target response and local ICMP permissions; no automatic retry was attempted.",
                )
            ],
            limitations=["An explicit ICMP test was attempted; command timeout is not proof that the host is down."],
        )
    except OSError as exc:
        return DiagnosticResult(
            collector="linux.ping",
            status="error",
            data={"target": str(address), "ip_version": address.version},
            findings=[
                Finding(
                    code="PING-EXECUTION-ERROR",
                    severity="warning",
                    title="Ping command could not be executed",
                    detail=exc.__class__.__name__,
                    recommendation="Check the local ping binary and its permissions.",
                )
            ],
        )

    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    try:
        parsed = parse_ping_output(output)
    except ValueError:
        return DiagnosticResult(
            collector="linux.ping",
            status="error" if completed.returncode not in (0, 1) else "warning",
            data={
                "target": str(address),
                "ip_version": address.version,
                "count": count,
                "timeout_seconds": timeout_seconds,
                "exit_code": completed.returncode,
            },
            findings=[
                Finding(
                    code="PING-OUTPUT-UNPARSED",
                    severity="warning",
                    title="Ping output could not be interpreted",
                    recommendation="Check the target ping implementation and retain the raw diagnostic log.",
                )
            ],
            limitations=["The command ran, but its summary did not match supported output formats."],
        )

    data = {
        "target": str(address),
        "ip_version": address.version,
        "count": count,
        "timeout_seconds": timeout_seconds,
        **parsed,
    }
    findings = []
    if parsed["packets_received"] == 0:
        findings.append(
            Finding(
                code="PING-NO-REPLIES",
                severity="warning",
                title="No ICMP echo replies received",
                detail="The target did not return an ICMP echo reply during this test.",
                recommendation="Check the target, route and ICMP policy; the target may intentionally block ping.",
            )
        )
    elif parsed["packet_loss_percent"] > 0:
        findings.append(
            Finding(
                code="PING-PACKET-LOSS",
                severity="warning",
                title="ICMP packet loss detected",
                detail=f"Observed packet loss: {parsed['packet_loss_percent']}%.",
                recommendation="Repeat only if authorized and compare with interface/link counters; a short sample is not a long-term quality measurement.",
            )
        )

    if completed.returncode not in (0, 1):
        status = "error"
    else:
        status = "ok" if completed.returncode == 0 and not findings else "warning"
    return DiagnosticResult(
        collector="linux.ping",
        status=status,
        data=data,
        findings=findings,
        limitations=[
            "This is an explicitly authorized ICMP echo test to one literal IP address.",
            "ICMP reachability does not prove that DNS, TCP services or Internet access work.",
            "No hostname lookup, retry loop, subnet scan or additional target probing is performed.",
        ],
    )
