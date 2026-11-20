#!/usr/bin/env python3
"""Assemble a self-contained FlipCTL script app directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "apps" / "network-diagnostics.fap.py"
CORE_SOURCE = ROOT / "src" / "flipper_diag"
APP_FILENAME = "network-diagnostics.fap.py"

APP_README = """Network Diagnostics for Flipper One

Install:
1. Copy this entire "Network Diagnostics" directory into /home/user/Apps/ on Flipper One.
2. Open Apps > Network Diagnostics > Network Diagnostics.
3. If prompted, install "Python Runtime" from the FlipCTL App Manager.

The app currently performs local, read-only interface inventory and Ethernet link
queries. It does not scan other devices or send active diagnostic probes.
Results are stored locally under ~/.local/share/flipper-one-network-diagnostics/.
"""


def build(output: Path) -> Path:
    """Copy the app script and the exact core source into a deployable folder."""
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if not APP_SOURCE.is_file() or not CORE_SOURCE.is_dir():
        raise FileNotFoundError("app source or flipper_diag core package is missing")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    shutil.copy2(APP_SOURCE, output / APP_FILENAME)
    shutil.copytree(
        CORE_SOURCE,
        output / "flipper_diag",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    (output / "README.txt").write_text(APP_README, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "Network Diagnostics",
        help="new output directory (must not already exist)",
    )
    args = parser.parse_args()
    destination = build(args.output)
    print(f"FlipCTL app assembled at: {destination}")
    print("Copy this folder to /home/user/Apps/ on Flipper One.")


if __name__ == "__main__":
    main()
