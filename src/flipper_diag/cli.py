"""Command-line entry point."""

import argparse
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .baseline import compare_device_inventory
from .doctor import collect_doctor_report
from .linux_dns import collect_dns_config
from .linux_ethtool import collect_link_status
from .linux_ip import collect_ip_interfaces
from .linux_routes import collect_default_routes
from .local_check import collect_local_check
from .store import (
    default_database_path,
    list_baselines,
    list_results,
    load_baseline,
    save_baseline,
    save_result,
)


def _read_inventory(path: Path, parser: argparse.ArgumentParser) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read inventory JSON: {exc}")
    if not isinstance(payload, list):
        parser.error("inventory JSON root must be an array of device objects")
    return payload


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

    local_check = subparsers.add_parser(
        "local-check", help="combine local-only interface, link, route and DNS checks"
    )
    local_check.add_argument("--interface", help="Ethernet interface to inspect")
    local_check.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    local_check.add_argument("--no-save", action="store_true", help="do not store this result")
    local_check.add_argument("--db", type=Path, default=default_database_path())

    routes = subparsers.add_parser(
        "routes", help="read local IPv4 and IPv6 default routes without probing"
    )
    routes.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    routes.add_argument("--no-save", action="store_true", help="do not store this result")
    routes.add_argument("--db", type=Path, default=default_database_path())

    dns = subparsers.add_parser(
        "dns", help="read local resolver configuration without DNS queries"
    )
    dns.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    dns.add_argument("--no-save", action="store_true", help="do not store this result")
    dns.add_argument("--db", type=Path, default=default_database_path())

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

    baseline = subparsers.add_parser(
        "baseline", help="manage local device inventory baselines"
    )
    baseline_commands = baseline.add_subparsers(
        dest="baseline_command", required=True
    )
    baseline_save = baseline_commands.add_parser("save", help="save an inventory JSON file")
    baseline_save.add_argument("--name", required=True)
    baseline_save.add_argument("--input", required=True, type=Path)
    baseline_save.add_argument("--json", action="store_true")
    baseline_save.add_argument("--db", type=Path, default=default_database_path())

    baseline_compare = baseline_commands.add_parser(
        "compare", help="compare an inventory JSON file with a saved baseline"
    )
    baseline_compare.add_argument("--name", required=True)
    baseline_compare.add_argument("--input", required=True, type=Path)
    baseline_compare.add_argument("--json", action="store_true")
    baseline_compare.add_argument("--db", type=Path, default=default_database_path())

    baseline_list = baseline_commands.add_parser("list", help="list saved baselines")
    baseline_list.add_argument("--json", action="store_true")
    baseline_list.add_argument("--db", type=Path, default=default_database_path())

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
    elif args.command == "local-check":
        result = collect_local_check(args.interface)
        run_id = None if args.no_save else save_result(args.db, result)
        envelope = result.to_dict()
        if run_id:
            envelope["run_id"] = run_id
        if args.json:
            print(json.dumps(envelope, indent=2, ensure_ascii=False))
        else:
            print(f"{result.collector} · status: {result.status}")
            print(json.dumps(result.data.get("component_status", {}), indent=2))
            assessment = result.data.get("assessment", {})
            print(assessment.get("summary", "No assessment available."))
            for cause in assessment.get("likely_causes", []):
                print(
                    "Likely cause "
                    f"({cause['confidence']}): {cause['title']}"
                )
            for finding in result.findings:
                print(f"{finding.severity}: {finding.title} — {finding.detail}")
            if run_id:
                print(f"Saved run: {run_id}")
            for note in result.limitations:
                print(f"Note: {note}")
    elif args.command in ("routes", "dns"):
        result = (
            collect_default_routes()
            if args.command == "routes"
            else collect_dns_config()
        )
        run_id = None if args.no_save else save_result(args.db, result)
        envelope = result.to_dict()
        if run_id:
            envelope["run_id"] = run_id
        if args.json:
            print(json.dumps(envelope, indent=2, ensure_ascii=False))
        else:
            print(f"{result.collector} · status: {result.status}")
            print(json.dumps(result.data, indent=2, ensure_ascii=False))
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
    elif args.command == "baseline":
        if args.baseline_command == "save":
            devices = _read_inventory(args.input, parser)
            try:
                baseline_id = save_baseline(args.db, args.name, devices)
            except sqlite3.IntegrityError:
                parser.error("a baseline with this name already exists")
            output = {"baseline_id": baseline_id, "name": args.name, "device_count": len(devices)}
            print(json.dumps(output, indent=2) if args.json else
                  f"Saved baseline '{args.name}' with {len(devices)} devices.")
        elif args.baseline_command == "compare":
            saved = load_baseline(args.db, args.name)
            if saved is None:
                parser.error(f"baseline '{args.name}' does not exist")
            current = _read_inventory(args.input, parser)
            findings = compare_device_inventory(saved["devices"], current)
            output = [asdict(item) for item in findings]
            if args.json:
                print(json.dumps(output, indent=2, ensure_ascii=False))
            elif not findings:
                print(f"No inventory differences against baseline '{args.name}'.")
            else:
                for finding in findings:
                    print(f"{finding.severity}: {finding.title} — {finding.detail}")
        elif args.baseline_command == "list":
            items = list_baselines(args.db)
            print(json.dumps(items, indent=2, ensure_ascii=False) if args.json else
                  "\n".join(f"{item['name']} · {item['created_at']}" for item in items)
                  or "No baselines saved.")


if __name__ == "__main__":
    main()
