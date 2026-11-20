# Software strategy before Flipper One delivery

Status: reviewed 2026-11-20. This document separates official upstream plans, project decisions, and hardware assumptions.

## 1. Operating model: standalone first

The target user experience is that ordinary diagnostics are started, controlled, and reviewed directly on Flipper One using its built-in display and physical controls. A PC is not a runtime dependency.

Flipper One has a dual-processor architecture: RK3576 runs Linux and user applications; RP2350 handles the display and local controls. Official FlipCTL documentation describes the built-in 256×144 LCD and physical controls as a primary frontend. It also describes optional browser, terminal, and desktop frontends.

Sources:
- https://docs.flipper.net/one/cpu-software/about
- https://docs.flipper.net/one/cpu-software/flipctl
- https://docs.flipper.net/one/mcu-firmware/architecture

A PC/phone may optionally be used for:
- remote dashboard and larger visualizations;
- downloading/exporting PCAP, CSV, HTML/PDF reports;
- deep packet analysis in Wireshark;
- development, debugging, and firmware/package recovery.

The core product must not require a PC, internet connection, cloud service, or external display for ordinary use. Any feature that cannot reasonably fit the small built-in screen should provide a useful on-device summary and optionally expose detailed output remotely.

## 2. Official Flipper features that overlap our initial backlog

The official Flipper One product feature specification already describes:
- Ethernet MitM sniffer: transparent two-port bridge, compact live traffic log, PCAP storage, optional mirroring to a PC.
- LAN discovery (passive and active): L2/L3 observation, ARP/IPv6 neighbor discovery, DHCP/network configuration and service probing.
- Flipper OS built-in profiles including Network sniffer.
- FlipCTL wrappers around standard tools such as ping, nmap and traceroute.

Sources:
- https://docs.flipper.net/one/general/features
- https://docs.flipper.net/one/cpu-software/flipper-os
- https://docs.flipper.net/one/cpu-software/flipctl

Important status distinction: the Features page is a high-level product/user-story specification. It does not prove that every feature is already implemented or shipped. We must check source code, issues, tests, and release notes before assuming availability.

### Scope decision

Do not independently recreate Flipper OS, its boot/profile manager, the FlipCTL UI, router/VPN modes, Ethernet transparent bridge/sniffer, or basic LAN discovery if upstream provides them.

Instead:
- detect and reuse installed system tools and native Flipper capabilities;
- integrate through a documented FlipCTL wrapper/plugin interface when it is stable;
- build higher-level network diagnostics and analysis that add value above raw tools;
- provide graceful fallback on ordinary Debian/Linux during development.

Our differentiated scope is the NetAlly-style diagnostic workflow: guided AutoTest, end-to-end connectivity checks, DHCP/DNS/gateway validation, latency/loss/jitter, TCP/HTTP/MTU tests, LLDP/CDP/VLAN evidence, route/path analysis where supported, iPerf orchestration, device inventory enrichment, baseline comparison, fault explanation, trends, and portable reports.

Packet capture should be an integration point: use upstream sniffer mode and standard tools, then add filtering, protocol summaries, findings, and report links. Do not create a competing capture engine unless a verified gap requires it.

## 3. FlipCTL integration strategy and upstream status

There are two distinct upstream projects that must not be confused:

1. `flipperdevices/flipctl` is the earlier/high-level architecture proposal. Its README describes backend services, command wrappers and multiple frontends, but the repository still has open architecture/plugin proposals and no stable versioned third-party plugin API was found.
2. `flipperdevices/flipctl-slint` is the current shipped panel UI/app framework referenced by the Linux image build scripts. Its documented app contract is already concrete enough for a first integration prototype.

At commit `483ad588f5cd21e26eed416c949811821bb29a1f` (2026-11-19), `flipctl-slint/docs/apps.md` documents:
- Python and JavaScript `.fap.py` / `.fap.js` scripts, discovered from a manifest comment;
- a Python runtime app that provides the `py` runtime and the `flipctl` Python UI module;
- `flipctl.Menu`, `Detail`, `Log`, buttons and physical-key handling;
- AppImage bundles for compiled apps;
- an app's own writable data directory and optional Debian package dependencies.

The official `flipperone-linux-build-scripts` currently builds `flipctl` from `flipctl-slint`, installs the panel UI and remote-view assets, and deliberately ships no user apps by default: apps are installed from the catalogue or copied into `~/Apps`. This gives us a concrete on-device integration path without waiting for a generic plugin API.

### Project decision

- Keep the diagnostic core independent of FlipCTL internals and keep the CLI/JSON interface.
- Build the first device UI as a documented Python `.fap.py` app using the upstream `flipctl` module.
- Package the `flipper_diag` core beside the script in the app folder; do not duplicate diagnostic logic inside the UI.
- The Flipper One display and physical keys are the primary frontend. PC/browser are optional.
- Keep a thin UI layer: it calls core collectors, saves local results and renders concise summaries.
- Re-check `flipctl-slint/docs/apps.md` and its app examples before changing the app contract. The `dev` branch is active development, not a semver-stable API.

### Existing upstream overlap to avoid

The current `flipctl-slint` tree already contains:
- `apps/ping.fap.py`: a working example of a Python app and ICMP UI;
- `apps/Test Tools/ethernet-tester.fap.py`: an experimental two-port cable/loopback test.

The Ethernet tester source describes undocumented/reserved RTL8211F PHY registers, a privileged helper, raw test frames, link drops during tests and a kernel MII polling race. Treat it as an experimental upstream test utility, not a safe or released general-purpose feature. Do not copy its register poking or reproduce its cable-test implementation. Our first Ethernet scope stays with read-only link status and standard Linux interfaces.

Sources:
- https://github.com/flipperdevices/flipctl
- https://github.com/flipperdevices/flipctl/pulls
- https://github.com/flipperdevices/flipctl-slint
- https://github.com/flipperdevices/flipctl-slint/blob/dev/docs/apps.md
- https://github.com/flipperdevices/flipctl-slint/blob/dev/apps/ping.fap.py
- https://github.com/flipperdevices/flipctl-slint/blob/dev/apps/Test%20Tools/ethernet-tester.fap.py
- https://github.com/flipperdevices/flipperone-linux-build-scripts

## 4. Technology decision for the first implementation

Use Python 3.10+ and the standard library for the portable diagnostic core and the first FlipCTL script app. The current Flipper OS rootfs package manifest includes Python packages such as `python3-pandas` and `python3-plotly`, which pull in the Python interpreter; the FlipCTL Python Runtime app separately declares `python3` as an app dependency. Exact Python version and runtime behavior still need target verification. Add dependencies only when a concrete feature needs them.

Reasons:
- Most early functions wrap Linux tools (ip, iw, ethtool, ping, tcpdump, iperf3, nmap, SNMP utilities).
- Python is suitable for parsing command output, orchestration, JSON results, and fixtures.
- The core remains independent of UI and hardware.
- Performance-critical components can be moved to Rust or another language later if measurements justify it.

The official rootfs manifest explicitly includes `iproute2`, `iperf3`, `iputils-ping`, `iw`, `tcpdump`, `traceroute`, `bluez`, `python3-pandas` and `python3-plotly`. It does not explicitly include `ethtool`, `nmap`, `lldpd`, `snmp` or `tshark`; our doctor command must detect optional tools and the app must degrade gracefully. This is based on the published manifest at build-scripts commit `836f7e7f8937cba3a25a37b8f4ad888a121783cc`, not a claim that every future image is identical.

This is a project decision, not a claim that Python is the only or officially preferred Flipper One language. Final runtime compatibility, memory use, cold-start time, and battery impact must be measured on Flipper OS. Avoid a heavyweight always-on web stack on the handheld unless testing justifies it.

## 5. Work that can be completed without Flipper One

- Versioned diagnostic result schema.
- Safe Mode policy and authorization model.
- SQLite schema and migrations.
- Profile and target configuration.
- Finding/rule engine with synthetic fixtures.
- HTML/CSV/PDF report generation.
- Parsers for recorded Linux tool outputs (ip, ethtool, iw, LLDP, SNMP and Nmap).
- Automated unit and integration tests.
- Packaging and CI on ordinary Linux.
- Documentation and upstream compatibility tracking.

## 6. Work requiring Linux networking hardware or target validation

- Actual driver names, firmware versions and interface mapping.
- Monitor-mode stability and radiotap capture.
- 6 GHz channel availability and regulatory restrictions.
- Concurrent Wi-Fi station/monitor/AP modes.
- BLE scan stability and coexistence.
- Ethernet PHY counters and cable diagnostics support.
- Packet capture performance and sustained throughput.
- Battery, thermal and resource consumption on the handheld.
- FlipCTL display/input integration and final package installation.

A successful desktop test does not count as proof of Flipper One hardware support.

## 7. Initial milestones

### P0 — portable foundation
- Python package and CLI.
- Read-only doctor command.
- Versioned result envelope.
- Default-deny active-operation policy.
- Unit tests and CI.

Exit criteria: tests pass on ordinary Linux; doctor sends no network traffic.

### P1 — simulated diagnostics
- Fixture files for common Linux tool outputs.
- Parsers and normalized findings.
- Synthetic devices, VLANs, switches and baselines.
- SQLite schema and migrations.

Exit criteria: repeatable tests without network hardware or live targets.

### P2 — differentiated wired diagnostics
- Interface/link information.
- DHCP/DNS/gateway checks and guided AutoTest.
- Ping/TCP/HTTP/MTU tests behind explicit authorization.
- LLDP/CDP and VLAN observations where supported.
- Baseline, latency/loss/jitter, and fault rules.
- Integrate with native discovery/sniffer functions rather than duplicating them.

Exit criteria: tests pass on a Linux host; active actions enforce Safe Mode; each feature states its upstream dependency.

### P3 — Flipper OS and FlipCTL integration
- Verify install on supported RK3576 SBC or Flipper One.
- Confirm package/runtime dependencies and resource budget.
- Implement FlipCTL adapter against an implemented/documented interface.
- Validate built-in display navigation; optional remote web access.
- Do not require PC for ordinary workflows.

Exit criteria: installable package and tested UI integration on target OS.

### P4 — Wi-Fi, BLE and security
- Add only after hardware/driver verification.
- Reuse native Flipper OS capabilities where present.
- Preserve passive-first behavior and bounded authorization.
- Record driver/kernel/firmware provenance in every hardware test.

## 8. Explicit non-goals for the software-only phase

Software cannot create physical wiremap/TDR measurements, PoE load testing, optical/SFP measurements, non-Wi-Fi spectrum analysis, or multi-gigabit PHY capabilities when the required hardware is absent. These remain separate hardware-extension projects.
