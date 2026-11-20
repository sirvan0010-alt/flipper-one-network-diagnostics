"""Command-line entry point."""

import argparse
import json
from pathlib import Path

from . import __version__
from .doctor import collect_doctor_report
from .store import default_database_path, list_results


def main() -> None:
    parser = argparse.ArgumentParser(prog="flipper-diag")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor", help="show local platform capabilities without network probes"
    )
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")

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
