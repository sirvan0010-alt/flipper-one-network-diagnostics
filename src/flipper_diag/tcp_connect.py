"""Explicitly authorized, single-target/single-port TCP connect diagnostics."""

from __future__ import annotations

import errno
import ipaddress
import socket

from .models import DiagnosticResult, Finding
from .safety import ActiveAuthorization, require_active_allowed

MAX_TIMEOUT_SECONDS = 5


def run_tcp_connect(
    target: str,
    port: int,
    *,
    authorization: ActiveAuthorization | None = None,
    safe_mode: bool = True,
    timeout_seconds: int = 3,
) -> DiagnosticResult:
    """Attempt one TCP handshake to one literal IP and authorized port; send no payload."""
    if not isinstance(target, str):
        raise ValueError("target must be a literal IPv4 or IPv6 address")
    try:
        address = ipaddress.ip_address(target)
    except ValueError as exc:
        raise ValueError("target must be a literal IPv4 or IPv6 address; hostnames are not accepted") from exc

    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("port must be an integer between 1 and 65535")
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
        port=port,
    )

    family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
    remote = (str(address), port, 0, 0) if address.version == 6 else (str(address), port)
    try:
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout_seconds)
            error_code = connection.connect_ex(remote)
    except OSError as exc:
        return DiagnosticResult(
            collector="linux.tcp_connect",
            status="error",
            data={
                "target": str(address),
                "ip_version": address.version,
                "port": port,
                "connected": False,
                "error": exc.__class__.__name__,
            },
            findings=[
                Finding(
                    code="TCP-CONNECT-EXECUTION-ERROR",
                    severity="warning",
                    title="TCP connection test could not be executed",
                    detail=exc.__class__.__name__,
                    recommendation="Check local socket permissions and network interface state.",
                )
            ],
        )

    data = {
        "target": str(address),
        "ip_version": address.version,
        "port": port,
        "connected": error_code == 0,
        "error_code": error_code,
        "timeout_seconds": timeout_seconds,
    }
    if error_code == 0:
        status = "ok"
        findings = []
    elif error_code == errno.ECONNREFUSED:
        status = "warning"
        findings = [
            Finding(
                code="TCP-PORT-REFUSED",
                severity="warning",
                title="TCP connection was refused",
                detail=f"The target responded to the connection attempt on port {port}, but did not accept it.",
                recommendation="Check whether the intended service is listening and whether the port is correct.",
            )
        ]
    elif error_code == errno.ETIMEDOUT:
        status = "warning"
        findings = [
            Finding(
                code="TCP-CONNECT-TIMEOUT",
                severity="warning",
                title="TCP connection timed out",
                detail=f"No successful TCP handshake completed within {timeout_seconds} seconds.",
                recommendation="Check the route and firewall policy; timeout alone does not prove the host is down.",
            )
        ]
    else:
        status = "warning"
        findings = [
            Finding(
                code="TCP-CONNECT-FAILED",
                severity="warning",
                title="TCP connection failed",
                detail=f"Socket error code: {error_code}.",
                recommendation="Check the target, route, local permissions and firewall policy.",
            )
        ]

    return DiagnosticResult(
        collector="linux.tcp_connect",
        status=status,
        data=data,
        findings=findings,
        limitations=[
            "One TCP handshake attempt to one explicitly authorized IP and port.",
            "No application payload, banner grab, TLS handshake, retry or port scan is performed.",
            "A successful TCP handshake does not validate application-level health.",
        ],
    )
