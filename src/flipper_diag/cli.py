"""Command-line entry point."""

import argparse
import json
from pathlib import Path

from . import __version__
from .doctor import collect_doctor_report
from .linux_ethtool import collect_link_status
from .linux_ip import collect_ip_interfaces
from .store import default_database_path, list_results, save_result


def main() -> None:
    parser = argparse.ArgumentParser(prog="flipper-diag")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor", help="show local platform capabilities without network probes"
    )
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    interfaces = subparsers.add_parser(
        "interfaces", help="read local Linux interface and address information"
    )
    interfaces.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    interfaces.add_argument("--no-save", action="store_true", help="do not store this result")
    interfaces.add_argument(
        "--db", type=Path, default=default_database_path(), help="SQLite database path"
    )

    link = subparsers.add_parser(
        "link", help="read Ethernet link speed, duplex and carrier state"
    )
    link.add_argument("interface", help="local interface name, for example eth0")
    link.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    link.add_argument("--no-save", action="store_true", help="do not store this result")
    link.add_argument(
        "--db", type=Path, default=default_database_path(), help="SQLite database path"
    )

    history = subparsers.add_parser(
        "history", help="show locally stored diagnostic runs"
    )
    history.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    history.add_argument("--limit", type=int, default=20, help="maximum rows (1–500)")
    history.add_argument(
        "--db",
        type=Path,
        default=default_database_path(),
        help="SQLite database path",
    )

    args = parser.parse_args()
    if args.command == "doctor":
        report = collect_doctor_report()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"Flipper Diagnostics doctor · {report['platform']}")
            print(f"Architecture: {report['machine']} · Python: {report['python']}")
            print("Interfaces: " + (", ".join(report["interfaces"]) or "none detected"))
            print("Available tools:")
            for name, path in report["tools"].items():
                print(f"  {name:10} {path or 'not installed'}")
            print("\nRead-only: no network traffic generated.")
    elif args.command == "interfaces":
        result = collect_ip_interfaces()
        run_id = None if args.no_save else save_result(args.db, result)
        envelope = result.to_dict()
        if run_id:
            envelope["run_id"] = run_id
        if args.json:
            print(json.dumps(envelope, indent=2, ensure_ascii=False))
        else:
            print(f"Interface inventory · status: {result.status}")
            for interface in result.data.get("interfaces", []):
                addresses = ", ".join(
                    f"{item.get('local')}/{item.get('prefixlen')}"
                    for item in interface["addresses"]
                )
                print(
                    f"{interface['name']:12} {interface.get('operstate') or '-':8} "
                    f"{interface.get('mac_address') or '-':18} {addresses}"
                )
            if run_id:
                print(f"Saved run: {run_id}")
            for note in result.limitations:
                print(f"Note: {note}")
    elif args.command == "link":
        result = collect_link_status(args.interface)
        run_id = None if args.no_save else save_result(args.db, result)
        envelope = result.to_dict()
        if run_id:
            envelope["run_id"] = run_id
        if args.json:
            print(json.dumps(envelope, indent=2, ensure_ascii=False))
        else:
            print(f"Ethernet link · {args.interface} · status: {result.status}")
            for key, value in result.data.items():
                print(f"{key}: {value}")
            for finding in result.findings:
                print(f"{finding.severity}: {finding.title} — {finding.detail}")
            if run_id:
                print(f"Saved run: {run_id}")
            for note in result.limitations:
                print(f"Note: {note}")
    elif args.command == "history":
        results = list_results(args.db, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif not results:
            print(f"No diagnostic runs stored in {args.db}")
        else:
            print(f"Recent diagnostic runs · {args.db}")
            for item in results:
                print(
                    f"{item['started_at']}  {item['status']:8} "
                    f"{item['collector']}  {item.get('interface') or '-'}  "
                    f"{item['run_id']}"
                )


if __name__ == "__main__":
    main()
