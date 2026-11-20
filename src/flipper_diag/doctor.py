"""Read-only host capability inventory; sends no network packets."""

import platform
import shutil
import socket
import sys


TOOLS = (
    "ip",
    "iw",
    "ethtool",
    "ping",
    "tcpdump",
    "tshark",
    "iperf3",
    "nmap",
    "lldpcli",
    "snmpwalk",
)


def collect_doctor_report() -> dict:
    """Collect basic OS, Python, interface-name and tool availability information."""
    interfaces = []
    try:
        interfaces = sorted(name for _, name in socket.if_nameindex())
    except OSError:
        pass

    return {
        "schema_version": 1,
        "mode": "read-only",
        "network_traffic_generated": False,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "interfaces": interfaces,
        "tools": {name: shutil.which(name) for name in TOOLS},
        "notes": [
            "Tool presence does not prove driver or hardware capability.",
            "No active network tests are run by the doctor command.",
        ],
    }
