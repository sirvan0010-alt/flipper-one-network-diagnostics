"""Read-only parser and collector for the local resolver configuration."""

from __future__ import annotations

import ipaddress
from pathlib import Path

from .models import DiagnosticResult, Finding

DEFAULT_RESOLV_CONF = Path("/etc/resolv.conf")
MAX_RESOLV_CONF_BYTES = 65536
LOCAL_STUB_ADDRESSES = {"127.0.0.53", "127.0.0.1", "::1"}


def parse_resolv_conf(payload: str) -> dict[str, list[str]]:
    """Parse nameserver, search/domain and options directives."""
    parsed = {"nameservers": [], "search": [], "options": []}
    for line in payload.splitlines():
        directive = line.split("#", 1)[0].split(";", 1)[0].strip()
        if not directive:
            continue
        fields = directive.split()
        key = fields[0].lower()
        values = fields[1:]
        if key == "nameserver" and values:
            parsed["nameservers"].append(values[0])
        elif key in ("search", "domain"):
            parsed["search"].extend(values)
        elif key == "options":
            parsed["options"].extend(values)
    return parsed


def collect_dns_config(path: str | Path = DEFAULT_RESOLV_CONF) -> DiagnosticResult:
    """Read resolver configuration from disk without issuing DNS queries."""
    resolver_path = Path(path)
    try:
        if resolver_path.stat().st_size > MAX_RESOLV_CONF_BYTES:
            raise ValueError("resolver configuration exceeds the 64 KiB safety limit")
        payload = resolver_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError) as exc:
        return DiagnosticResult(
            collector="linux.resolver_config",
            status="error",
            findings=[
                Finding(
                    code="DNS-CONFIG-UNAVAILABLE",
                    severity="warning",
                    title="Resolver configuration is unavailable",
                    detail=f"Unable to read {resolver_path}: {exc.__class__.__name__}.",
                    recommendation="Check the local resolver configuration and permissions.",
                )
            ],
            limitations=["No DNS query was sent; only the local resolver file was inspected."],
        )

    parsed = parse_resolv_conf(payload)
    nameservers: list[str] = []
    invalid_nameservers: list[str] = []
    for value in parsed["nameservers"]:
        try:
            normalized = str(ipaddress.ip_address(value))
        except ValueError:
            invalid_nameservers.append(value)
            continue
        if normalized not in nameservers:
            nameservers.append(normalized)

    findings: list[Finding] = []
    if invalid_nameservers:
        findings.append(
            Finding(
                code="DNS-CONFIG-INVALID-NAMESERVER",
                severity="warning",
                title="Invalid DNS server entry",
                detail=f"Invalid nameserver values: {', '.join(invalid_nameservers)}.",
                recommendation="Check the nameserver entries supplied by the active network configuration.",
            )
        )
    if not nameservers:
        findings.append(
            Finding(
                code="DNS-CONFIG-MISSING",
                severity="warning",
                title="No DNS server configured",
                detail="No valid nameserver address was found in the resolver configuration.",
                recommendation="Check DHCP DNS options or configure an approved resolver.",
            )
        )

    local_stubs = [value for value in nameservers if value in LOCAL_STUB_ADDRESSES]
    limitations = ["Local resolver configuration only; DNS resolution was not tested."]
    if local_stubs:
        limitations.append(
            "A loopback resolver is configured; its upstream DNS servers are not visible in this file."
        )

    return DiagnosticResult(
        collector="linux.resolver_config",
        status="warning" if findings else "ok",
        data={
            "path": str(resolver_path),
            "nameservers": nameservers,
            "search_domains": parsed["search"],
            "options": parsed["options"],
            "local_stub": bool(local_stubs),
            "invalid_nameservers": invalid_nameservers,
        },
        findings=findings,
        limitations=limitations,
    )
