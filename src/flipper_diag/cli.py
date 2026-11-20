"""Command-line entry point."""

import argparse
import json

from . import __version__
from .doctor import collect_doctor_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="flipper-diag")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor", help="show local platform capabilities without network probes"
    )
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")

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


if __name__ == "__main__":
    main()
