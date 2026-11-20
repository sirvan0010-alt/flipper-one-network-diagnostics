# FlipCTL app integration

Status: first Python script app prototype, based on the public `flipctl-slint` app contract reviewed 2026-11-20.

## Why this integration

The current Flipper One image build scripts use `flipperdevices/flipctl-slint`. Its `docs/apps.md` documents script apps with a `# /// flipctl` manifest and a Python Runtime app that provides the `py` runtime and the `flipctl` UI module.

The Network Diagnostics app therefore runs as a native hosted FlipCTL app:
- it appears in the Flipper One Apps list;
- it uses the device's physical buttons and built-in 256×144 display;
- it imports the same `flipper_diag` core package as the portable CLI;
- it writes results to the device's local SQLite database;
- no PC, web server or cloud service is needed during normal operation.

## Build a deployable app folder

From the repository root:

```bash
python scripts/package_flipctl_app.py
```

The builder creates `dist/Network Diagnostics/` containing:
- `network-diagnostics.fap.py` – FlipCTL script app, identified by its `# /// flipctl` manifest;
- `flipper_diag/` – the exact core source used by the CLI, placed beside the script;
- `README.txt` – installation notes.

The output directory must not already exist; the builder refuses to overwrite it. The directory is a group in the Apps list; the `.fap.py` file inside it is the actual app. This matches the upstream script-app scanner, which reads the manifest from the script and derives the `py` runtime from its extension.

Copy the complete `Network Diagnostics` directory to `/home/user/Apps/` on the Flipper One, then open the group and launch Network Diagnostics. If FlipCTL asks for the Python Runtime, install it from the App Manager. The runtime supplies the `flipctl` module and uses the device's own Python interpreter. It runs the script by path; Python can therefore import the sibling `flipper_diag/` directory without installing our package globally.

A future release may be offered through the FlipCTL app catalogue. Catalogue submission and approval are separate from this repository's code.

## Current on-device functions

- Local interface/address inventory via `ip -j address show`.
- Ethernet link state via `ethtool` when installed, with a read-only `/sys/class/net` carrier/speed/duplex fallback when it is absent.
- IPv4/IPv6 default routes via `ip -j route`; this inspects the local routing table and does not test gateway reachability.
- Local resolver configuration from `/etc/resolv.conf`; this does not send DNS queries and flags loopback resolver stubs.
- Local SQLite result history.
- Safe Mode shown as ON; this prototype does not run active scans or probes.

The published rootfs manifest includes `iproute2`, but does not explicitly include `ethtool`. The app therefore reports the missing tool instead of assuming it exists. Do not add privileged PHY register access or experimental cable-test code.

## ARM64 software validation

The CI workflow includes a native `ubuntu-24.04-arm` job. It:
- verifies the runner and Python process are `aarch64`;
- runs the unit test suite and Ruff on ARM64;
- builds and checks a universal `py3-none-any` wheel;
- installs the wheel into a clean virtual environment with package-index access disabled;
- imports the installed core, checks SQLite availability and runs the read-only `doctor --json` command;
- assembles the FlipCTL app directory, then imports every bundled core module with Python site-packages disabled.

This validates the portable Python package on generic Linux ARM64. It does **not** validate the Flipper One root filesystem, the installed FlipCTL Python Runtime, app discovery, device permissions, UI input or hardware-specific interfaces.

## Limitations and validation

- The app has been syntax-checked and its package builder is covered by CI; it has not yet been launched on Flipper One hardware.
- The FlipCTL app API is documented on the active `dev` branch, not versioned as a stable SDK. Re-check `flipctl-slint/docs/apps.md` and pin the exact compatible upstream commit before a release.
- The Python runtime, app discovery, folder handling, UI key mapping and SQLite permissions need a target-device smoke test.
- The first UI is deliberately small. Detailed packet analysis, topology and large reports remain optional browser/PC workflows.
