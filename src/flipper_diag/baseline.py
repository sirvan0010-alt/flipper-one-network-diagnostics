"""Offline inventory comparison rules; consumes observations, performs no scans."""

from __future__ import annotations

import ipaddress
from collections import defaultdict
from typing import Any, Iterable

from .models import Finding


def _normalize_mac(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("each observed device must have a MAC address")
    return value.strip().lower()


def _normalize_addresses(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if not isinstance(values, (list, tuple)):
        raise ValueError("device addresses must be a list")
    normalized = set()
    for value in values:
        address = value.get("local") if isinstance(value, dict) else value
        try:
            normalized.add(str(ipaddress.ip_address(address)))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"invalid IP address in inventory: {address!r}") from exc
    return tuple(sorted(normalized))


def _index_devices(devices: Iterable[dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    indexed: dict[str, tuple[str, ...]] = {}
    for device in devices:
        if not isinstance(device, dict):
            raise ValueError("each device observation must be an object")
        mac = _normalize_mac(device.get("mac_address"))
        if mac in indexed:
            raise ValueError(f"duplicate MAC address in inventory: {mac}")
        indexed[mac] = _normalize_addresses(device.get("addresses", []))
    return indexed


def compare_device_inventory(
    baseline_devices: Iterable[dict[str, Any]],
    current_devices: Iterable[dict[str, Any]],
) -> list[Finding]:
    """Compare two observed inventories using MAC identity and IP address sets."""
    baseline = _index_devices(baseline_devices)
    current = _index_devices(current_devices)
    findings: list[Finding] = []

    for mac in sorted(current.keys() - baseline.keys()):
        findings.append(
            Finding(
                code="INVENTORY-NEW-DEVICE",
                severity="warning",
                title="New device detected",
                detail=f"Device {mac} was not present in the saved baseline.",
                recommendation="Verify whether this device is authorized before trusting it.",
            )
        )

    for mac in sorted(baseline.keys() - current.keys()):
        findings.append(
            Finding(
                code="INVENTORY-MISSING-DEVICE",
                severity="warning",
                title="Previously known device is missing",
                detail=f"Device {mac} was present in the baseline but not in this observation.",
                recommendation="Repeat discovery and check power, cabling, VLAN and filtering.",
            )
        )

    for mac in sorted(baseline.keys() & current.keys()):
        if baseline[mac] != current[mac]:
            findings.append(
                Finding(
                    code="INVENTORY-ADDRESS-CHANGED",
                    severity="info",
                    title="Device address changed",
                    detail=(
                        f"Device {mac}: baseline addresses {baseline[mac]}; "
                        f"current addresses {current[mac]}."
                    ),
                    recommendation="Confirm whether the address change is expected.",
                )
            )

    owners: dict[str, set[str]] = defaultdict(set)
    for mac, addresses in current.items():
        for address in addresses:
            owners[address].add(mac)
    for address, macs in sorted(owners.items()):
        if len(macs) > 1:
            findings.append(
                Finding(
                    code="NETWORK-DUPLICATE-IP",
                    severity="critical",
                    title="Duplicate IP address observed",
                    detail=f"{address} is reported by multiple devices: {', '.join(sorted(macs))}.",
                    recommendation=(
                        "Verify DHCP reservations and static addresses; confirm the conflict "
                        "with a packet-level observation before remediation."
                    ),
                )
            )

    return findings
