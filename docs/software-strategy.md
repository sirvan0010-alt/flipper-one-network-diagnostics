# Software strategy before Flipper One delivery

Status: implementation plan, 2026-11-20. This document separates verified platform facts from project decisions and hardware assumptions.

## 1. Key platform finding

Official Flipper One documentation describes Flipper OS as Debian-based Linux on RK3576 and documents running Flipper OS on supported RK3576 single-board computers. Dev Log #10 describes trying the FlipCTL UI in a browser, App Manager, and OS profiles before Flipper One is available.

Sources:
- https://docs.flipper.net/one/cpu-software/about
- https://docs.flipper.net/one/dev-log/10
- https://docs.flipper.net/one/testing/general

This means development does not have to wait for the handheld. A supported RK3576 board is an optional way to test the target OS, not a prerequisite for building most application logic.

## 2. FlipCTL integration strategy

Official FlipCTL material describes a lightweight Linux UI framework with a backend that wraps operating-system services and CLI tools, and frontends for the Flipper display, web browser, terminal, and desktop. The public FlipCTL repository currently presents a high-level architecture and invites proposals; it does not establish a stable, versioned third-party plugin API that this project can safely depend on.

Sources:
- https://docs.flipper.net/one/cpu-software/flipctl
- https://github.com/flipperdevices/flipctl

Decision:
- Keep the diagnostic engine independent of FlipCTL.
- Expose versioned JSON results and a local API.
- Implement a FlipCTL adapter only after its actual extension/plugin contract is documented and tested.
- Do not duplicate FlipCTL's system-level UI or assume undocumented hooks.

## 3. Technology decision for the first implementation

Use Python 3.10+ and the standard library for the initial core. Add dependencies only when a concrete feature needs them.

Reasons:
- Most early functions wrap Linux tools (ip, iw, ethtool, ping, tcpdump, iperf3, nmap, SNMP utilities).
- Python is suitable for parsing command output, orchestration, JSON APIs, and test fixtures.
- The core must remain independent of UI and hardware.
- Performance-critical parsing can be moved to Rust or another language later if measurements justify it.

This is a project decision, not a claim that Python is the only or officially preferred Flipper One language.

## 4. Work that can be completed without Flipper One

- Versioned diagnostic result schema.
- Safe Mode policy and authorization model.
- SQLite schema and migrations.
- Profile and target configuration.
- Finding/rule engine with synthetic fixtures.
- HTML/CSV/PDF report generation.
- Local API and browser dashboard.
- Parsers for recorded Linux tool outputs (ip, ethtool, iw, LLDP, SNMP and Nmap).
- Automated unit and integration tests.
- Packaging and CI on ordinary Linux.
- Documentation and hardware verification procedures.

## 5. Work requiring Linux networking hardware or target validation

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

## 6. Initial milestones

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

### P2 — wired MVP on Linux
- Interface/link information.
- Ping/TCP/HTTP tests behind explicit authorization.
- LLDP and VLAN observations.
- Passive discovery and bounded active discovery.
- PCAP capture and iPerf integration.

Exit criteria: tests pass on a Linux host and all active actions enforce Safe Mode.

### P3 — Flipper OS and FlipCTL integration
- Verify installation on supported RK3576 SBC or Flipper One.
- Confirm package/runtime dependencies.
- Implement FlipCTL adapter against a documented interface.
- Validate small-screen navigation and local web control.

Exit criteria: installable package and tested UI integration on target OS.

### P4 — Wi-Fi, BLE and security
- Add only after hardware/driver verification.
- Preserve passive-first behavior and bounded authorization.
- Record driver/kernel/firmware provenance in every hardware test.

## 7. Explicit non-goals for the software-only phase

Software cannot create physical wiremap/TDR measurements, PoE load testing, optical/SFP measurements, non-Wi-Fi spectrum analysis, or multi-gigabit PHY capabilities when the required hardware is absent. These remain separate hardware-extension projects.
