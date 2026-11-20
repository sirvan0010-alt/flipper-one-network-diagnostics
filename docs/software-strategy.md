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

Official FlipCTL material (README at commit `3285ba6caf`, 2026-06-19) describes:
- a backend for OS services and command-line tools;
- app wrappers/plugins;
- a frontend using HTML/JavaScript;
- a headless WebKit renderer on the Flipper display;
- optional Web UI, TUI, and desktop/browser control interfaces.

The public `flipperdevices/flipctl` repository currently has a high-level architecture README and open proposals. The README explicitly asks the community to propose the architecture and plugin system. At the 2026-11-20 review, its default `dev` branch had no demonstrated stable, versioned third-party plugin contract. The linked Fake FLipCTL2 is described upstream as a rough prototype needing rework. Do not infer that a proposed plugin API or fake UI harness is production-ready.

Sources:
- https://github.com/flipperdevices/flipctl
- https://github.com/flipperdevices/flipctl/pulls

Decision:
- Keep our diagnostic engine independent of FlipCTL internals.
- Keep versioned JSON results and command-line entry points.
- Prepare an adapter boundary, not a competing UI framework.
- Once the upstream plugin schema/API is implemented and documented, write a thin FlipCTL wrapper that calls our CLI/core.
- Re-check upstream before each integration change; do not target a fork or an unmerged proposal as if it were official.

The upstream `flipperdevices/flipperone-testing` repository contains `fake-flipctl2`, which the FlipCTL README describes as a rough AI-made prototype needing rework. It is not proof of the production FlipCTL runtime or a faithful emulator of the final device/backend.

Source:
- https://github.com/flipperdevices/flipperone-testing/tree/dev/fake-flipctl2

## 4. Technology decision for the first implementation

Use Python 3.10+ and the standard library for the portable diagnostic core. Add dependencies only when a concrete feature needs them.

Reasons:
- Most early functions wrap Linux tools (ip, iw, ethtool, ping, tcpdump, iperf3, nmap, SNMP utilities).
- Python is suitable for parsing command output, orchestration, JSON results, and fixtures.
- The core remains independent of UI and hardware.
- Performance-critical components can be moved to Rust or another language later if measurements justify it.

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
