# Functional specification

**Status:** working specification / implementation contract  
**Version:** 0.1.0  
**Reviewed:** 2026-11-20  
**Branch:** arm64-runtime-validation

This document turns backlog F-01–F-52 into testable product requirements and adds optional Proxmark5 and read-only CAN extensions. It supplements [AGENTS.md](../AGENTS.md), the [feature matrix](feature-matrix.md), [roadmap](roadmap.md), [architecture](architecture.md), [verification register](verification.md), and [active-test policy](active-tests.md).

## 1. Product goal

Build a local-first diagnostic instrument for wired and wireless networks, comparable to software capabilities of NetAlly LinkRunner, EtherScope, AirCheck and CyberScope where Flipper One hardware and OS support them. Normal workflows must work directly on Flipper One without a mandatory PC, phone, cloud account or external server.

Primary workflow: select target/profile → inspect passive evidence → explicitly authorize active tests → collect bounded observations → explain findings with evidence/confidence → save locally → export offline report.

### Non-negotiable principles

1. Device-first: on-device UI is primary; PC, HDMI, browser and remote dashboard are optional.
2. Offline-first: SQLite is the system of record; HTML/CSV first, PDF after dependency/resource evaluation.
3. Reuse before reimplementation: use Flipper OS and FlipCTL. Do not create competing LAN discovery, Ethernet MitM capture, Ping, Nmap or traceroute implementations without a documented upstream gap.
4. Safe Mode is default-deny. Passive observation is default; active network traffic, RF transmissions, writes and emulation are separately classified and confirmed.
5. Evidence, not guesses: findings include source, timestamp, interface/device, parameters, confidence and limitations. Likely cause is not confirmed root cause.
6. Bounded operation: explicit target list/range, target count, rate, packet count, duration and timeout. Never infer permission to scan an entire subnet.
7. Hardware truth: hardware-dependent features stay Verify first until driver, OS, adapter and target are tested. CI mocks are not hardware evidence.
8. Proxmark/RFID and automotive CAN are optional accessory modules and must not become dependencies of the wired MVP.

## 2. Status model

Keep these dimensions separate; never collapse them into one “implemented” label.

| Dimension | Values | Meaning |
|---|---|---|
| Scope | Core / Optional / Deferred / Excluded | Product priority |
| Implementation | Not started / Prototype / Partial / Implemented | State of code in this repository |
| Dependency | Reuse / Integrate / Build / Verify first / Defer | Upstream relationship |
| Hardware verification | Not required / Not tested / Lab tested / Target tested | Evidence on real equipment |
| Acceptance | Not defined / Pending / CI passed / Target passed | Test state |

A parser or mock test does not make a hardware-dependent feature complete.

## 3. Architecture and module boundaries

- **Presentation / FlipCTL:** on-device menu, detail screens, physical controls and confirmation. Optional dashboard uses the same core contracts.
- **Diagnostic core:** orchestration, profiles, target validation, deadlines, cancellation, result normalization and evidence-based findings.
- **Collectors/adapters:** narrow wrappers around system tools, official Flipper capabilities and accessory clients. Each declares capability, version, privilege, traffic class and timeout.
- **Policy/Safe Mode:** central fail-closed gate; UI confirmation alone is insufficient. Core revalidates every request immediately before execution.
- **Storage:** versioned SQLite schema, migrations, inventory, profiles, jobs, observations, findings, baselines and history.
- **Reports/export:** offline HTML/CSV first, optional PDF; redact secrets and retain evidence provenance.
- **Linux/OS integration:** interface/route/DNS inventory, ethtool, iproute2, iw, BlueZ, process supervision and optional tools. Detect runtime capabilities rather than assuming packages.
- **Accessory adapters:** Proxmark5 USB/Wi-Fi/BLE and, separately, experimental read-only automotive CAN.

Core remains importable/testable on ordinary Linux without FlipCTL, Proxmark5, Wi-Fi hardware or a live network.

## 4. Common feature contract

Every feature and implementation PR documents: purpose and exclusions; UX and cancellation; inputs; outputs/evidence; dependencies and version probes; traffic class (passive, active network, RF transmit, write, emulation, firmware update); authorization; persistence/redaction; timeout/rate/target limits; parser/unit/mock/packaging/hardware tests; observable acceptance criteria.

### Shared safety and data rules

- Passive means no deliberate probe/transmission initiated by the workflow. Association, DHCP, DNS probe, ping, TCP connect, Nmap, iPerf and RF commands are active.
- Active network operations require explicit target/CIDR, bounded targets, visible ports/protocols, rate limit, deadline and revalidation of interface/route.
- Cancel stops new work and terminates child processes where safe. Timeout is a result, not an indefinite wait.
- Use fixed executables and argument arrays; never interpolate user input into shell commands.
- Credentials, PSKs, recovered keys, full card dumps and authentication material are not written to ordinary logs/reports.
- RFID write/emulation/relay and automotive CAN transmit are not passive diagnostics; disabled by default and require a separate lab-only policy.
- No deauthentication, jamming, rogue association, credential capture, unauthorized cloning, access-control bypass or disruptive RF.
- No undocumented PHY writes, unsupported BER/cable qualification claims, false Wi-Fi 7 operation claims or compliance certification/attestation.

## 5. Wired networking — F-01 to F-19

### F-01 — Wired AutoTest
One guided run checks link, address/DHCP evidence, DNS, gateway, speed/duplex and selected service reachability. UX selects wired interface/profile and shows each stage, elapsed time, evidence and pass/warn/fail/unknown. Reuse local inventory/readiness and native Ping UI; build bounded DHCP/DNS/ICMP/TCP/HTTP orchestration. Local inspection is passive; probes are active and individually disclosed. Acceptance: disconnected cable, missing address/route, resolver failure and reachable/unreachable targets are distinguishable; cancellation/timeout yields a valid partial report.

### F-02 — Profiles and targets
Store reusable target sets, protocols, thresholds, interface preferences and stages; optional groups for explicitly selected VLAN workflows. Provide create/clone/edit/validate/import/export with schema version. Running a profile inherits each stage's authorization; it cannot silently widen targets. Acceptance: round-trip survives restart; stale interfaces and invalid targets are rejected; secrets are not stored in plaintext.

### F-03 — Periodic AutoTest
Repeat selected profiles from 1 minute to 24 hours and retain bounded history. Scheduler shows last/next run and supports pause/resume/stop. Passive stages may run unattended; active stages require a separate approved recurring policy with explicit scope and expiry. Acceptance: no burst replay of missed jobs and no overlapping runs.

### F-04 — Switch test (CDP/LLDP/EDP)
Decode neighbor identity, local/remote port, capabilities and advertised VLAN/voice VLAN TLVs. Display raw evidence and normalized fields. Verify native Flipper LLDP/CDP first; integrate upstream output or use a bounded parser. Passive receive only. Acceptance: known fixtures parse; malformed/truncated TLVs are ignored safely; unknown values stay unknown.

### F-05 — VLAN detection
Report VLAN IDs actually observed in tagged frames, interface, counts and sample window. Distinguish configured, advertised and observed values. Reuse native capture and add parser only for gaps. Passive only. Acceptance: tagged/untagged fixtures parse; unseen VLANs are not inferred.

### F-06 — Link speed/duplex
Show carrier, negotiated speed, duplex and link state; flag downshift only with comparable history. Reuse ethtool; fallback to sysfs. Record source and unavailable reason. Passive local inspection. Acceptance: tests cover absent tool, unsupported fields, down link and unknown speed; compare with actual switch/target link.

### F-07 — LLDP PoE offered power
Decode LLDP Power-via-MDI TLVs and display advertised power/class/priority. Explicitly distinguish switch-advertised capability from power actually delivered. Passive only. Acceptance: TLV fixtures parse and UI never calls this loaded PoE testing or a PoE analyzer.

### F-08 — Ping/TCP Connect/MTU
Bounded latency/loss, TCP connect timing and path-MTU checks. Reuse native Ping and traceroute wrappers; add orchestration/normalization. One target by default; show interface, target, port, count and timeout before active confirmation. Acceptance: Cancel sends zero packets; confirmation sends only configured bounded probes; gateway/interface change aborts before execution; no retry loop or implicit sweep.

### F-09 — HTTP/FTP response time
Measure bounded application-layer timing for explicitly configured endpoints. Report DNS/connect/TLS/first-byte timings only where measured. Active; one request/session per target by default. Acceptance: local success, refused port, DNS/TLS error and timeout covered; credentials redacted.

### F-10 — Wired Discovery
Enrich inventory with hostname, vendor/service hints, VLAN, switch/port and SNMP observations where available. Integrate official Flipper discovery first; optional SNMP only if installed and explicitly enabled. Passive cache parsing default; active discovery/SNMP requires scope. Acceptance: no competing scanner when native discovery is available; provenance retained.

### F-11 — Layered LAN discovery
Stage from passive ARP/IPv6 neighbor cache to user-approved active discovery. Reuse native discovery engine; app controls stages/authorization. Active DHCP/probes opt-in with target cap/rate. Acceptance: passive refresh sends no packets; stale route/interface aborts; subnet scan never implicit.

### F-12 — Problem engine
Correlate evidence for duplicate IP, missing gateway/DNS, DHCP, duplex mismatch, link errors, STP/neighbor changes and protocol configuration. Each finding has severity, confidence, evidence, likely cause and next check. Local deterministic rules first. Analysis passive; active follow-up separately authorized. Acceptance: contradictory evidence lowers confidence; no root cause invented.

### F-13 — Path Analysis
Reuse traceroute for L3 path; correlate with LLDP/SNMP for cautious L2/L3 view. Show hop timings, loss caveats and source evidence. Active probes require confirmation and bounds. Acceptance: filtered hops/timeouts are not treated as definitive failure.

### F-14 — Topology map
Build a local graph from verified LLDP/SNMP observations with source, timestamp, confidence and conflict markers. This is a network graph, not a geographic map. Depends on F-04/F-10/F-13. Passive generation; SNMP policy separate. Acceptance: no fabricated links; graph rebuilds from local evidence.

### F-15 — Ethernet packet capture
Reuse Flipper OS Network Sniffer/native capture. Add diagnostic filters, bounded duration/size/snap length and finding links. Receive-only by default. Acceptance: exported PCAP opens in standard tools; truncation/dropped-packet/storage limits are visible.

### F-16 — Ethernet MitM sniffer
Expose/analyze official transparent Ethernet MitM capability if available. Verify upstream and supported physical topology; do not build competing bridge. Not default; explicit physical setup and lab confirmation; no stealth interception. Acceptance: isolated lab tests and documented link/power-loss behavior before release.

### F-17 — iPerf
Guided TCP/UDP throughput via iperf3 against user-controlled endpoint. Default one stream and short duration. Optional package detected at runtime. High-volume active traffic requires explicit target/duration/streams. Acceptance: lab reference comparison, cancellation stops traffic, missing tool is clear.

### F-18 — Reflector + controller
Optional two-unit performance test using project-owned documented protocol. Requires two compatible units, explicit pairing and rate/duration limits. NetAlly compatibility not assumed. Defer to M7. Acceptance: protocol/authentication/replay/version compatibility specified before implementation.

### F-19 — Media soak/LANBERT
Long-duration media error/throughput observation using verified counters and supported peer/loopback. Verify RTL8211F/driver counter semantics and upstream Ethernet Tester. Counter-only is not BER or cable qualification. No undocumented PHY writes. Defer M7 until repeatable lab evidence exists.

## 6. Wi-Fi and Bluetooth — F-20 to F-32

### F-20 — Wi-Fi AutoTest
Profile-based association and connectivity: signal, DHCP/DNS/gateway and bounded service probes. Verify MT7921AUN, wpa_supplicant/NetworkManager and 802.1X on target. Association/probes active; credentials never logged. Acceptance: WPA2/WPA3/802.1X claims only after target tests; no silent fallback network.

### F-21 — Air Quality
Estimate Wi-Fi channel occupancy/co-channel contention from visible frames. Requires monitor mode/channel dwell. Passive. Report only 802.11-derived estimates; never claim non-Wi-Fi interference or spectrum analysis.

### F-22 — Channel map
Aggregate AP/client counts, retry evidence and short history for supported bands. Single radio cannot capture all channels simultaneously. Passive. Show dwell and gaps; missing channels are not zero activity.

### F-23 — AP/client inventory
List observed BSSIDs/SSIDs and clients with signal/channel/security/first-last seen. Allow local labels and known/unknown/authorized status. Passive; no forced disassociation. Randomized MACs treated as transient. Acceptance: same SSID/different BSSID remain distinct.

### F-24 — Roaming test
Correlate association/BSSID changes, RSSI, packet loss and latency while moving. Requires association events and optional F-31. Active association/ping; user selects network/target. Distinguish roam from RSSI fluctuation.

### F-25 — Locate
Track RSSI trend for selected AP/client. Direction finding requires verified external adapter; no false distance/bearing. Passive. Show scan cadence, variance and uncertainty.

### F-26 — Wi-Fi security audit
Identify observable open/weak security, suspicious duplicate/rogue AP evidence and risky broadcast behavior. Passive only; no deauth, injection, password cracking or disruptive testing. Findings must state evidence and confidence.

### F-27 — Wi-Fi packet capture
Monitor-mode PCAP with band/channel/filter/snap length/duration. Verify MT7921 driver, radiotap, channel and regulatory support. Receive-only; injection excluded. Unsupported modes disabled, not simulated.

### F-28 — Wi-Fi 7 visibility
Optionally parse Wi-Fi 7 information elements visible in frames received by Wi-Fi 6E radio. Clearly state device is not operating as Wi-Fi 7 client/AP. Passive. No 320 MHz/MLO capability claim for Flipper One.

### F-29 — Site survey
Log signal observations against user-selected floor-plan points and export heat-map data. No invented GPS/indoor location. Passive by default; throughput test separate and confirmed. Active/passive concurrency may require second radio.

### F-30 — BLE discovery/survey
List BLE advertisements and signal/time observations using BlueZ. Show address type/name/services/RSSI where available; private/random addresses treated carefully. Passive scanning default; pairing/connection is active. Acceptance: no connection during passive survey.

### F-31 — Ping while walking
Correlate bounded ICMP stream with timestamped Wi-Fi signal/association observations. One explicit target and duration. Cancellation stops probes; signal gaps visible; no location inferred.

### F-32 — Regulatory domain
Display OS-reported regulatory domain and channel/power restrictions. No bypass or arbitrary domain change in MVP. Acceptance: values match OS source and unsupported channels never enabled.

## 7. Security and OT — F-33 to F-38

### F-33 — IoT/OT/ICS discovery
Cautiously classify devices using passive fingerprints and authorized service evidence. Unknown is valid; no ICS classification from a port alone. Active protocol queries require authorization and safe rate.

### F-34 — Nmap in AutoTest
Reuse official FlipCTL Nmap wrapper if shipped; otherwise detect optional Nmap. Explicit targets, ports, mode, rate and timeout. Active/default-disabled; no default full-port/subnet scan. Acceptance: exact scope preview and policy enforcement.

### F-35 — CVE lookup
Map observed service/version evidence to local or explicitly fetched vulnerability references. Show source date, version uncertainty and confidence; no exploit execution. Defer until inventory stable. Ambiguous version cannot yield confirmed CVE.

### F-36 — Discovery Monitoring
Compare inventory snapshots; show new/missing/changed devices, baseline, time and evidence. SQLite. Comparison passive; collection inherits its policy. Transient observations do not silently delete known devices.

### F-37 — Batch authorization
Bulk-label devices known/unknown/approved/excluded with reason, scope and expiry. Labels are annotations, not proof of ownership. Active jobs still need target validation and explicit confirmation; expired approvals not reused.

### F-38 — CIS/NIS2 support reports
Map findings/evidence to versioned control references. Report gaps/source/date/limitations. Explicitly not certification, audit opinion, legal assessment or compliance attestation.

## 8. Platform/reporting — F-39 to F-44

### F-39 — Local reports
Export selected jobs/findings/inventory to offline HTML/CSV; PDF later. Include parameters, versions, evidence and limitations. Redact secrets. Deterministic output for same data/version.

### F-40 — Trend graphs
Visualize latency/loss/throughput/link/RSSI/finding trends from timestamped observations. Show gaps and sample counts; never interpolate missing data as measured values.

### F-41 — Local web dashboard
Optional richer view of local results/inventory/topology/trends. Reuse FlipCTL remote view where adequate. Read-only and localhost-bound by default; LAN access requires explicit enablement/authentication. Core works with dashboard stopped.

### F-42 — Remote control
Reuse official FlipCTL remote/desktop workflow. No custom VNC/control server without documented gap and threat model. Core job model independent of remote UI; sessions revocable.

### F-43 — Settings import/export
Transfer versioned profiles, thresholds, labels and non-secret preferences. Validate preview/conflicts/schema migration. Malformed/newer unsupported schema rejected without partial mutation.

### F-44 — Safe Mode
Central fail-closed policy allowing passive operations and denying active ones unless explicitly authorized. Visible state and reason. Every collector checks policy immediately before execution and revalidates route/interface/target. Tests prove default denial, zero packets on cancel and no UI/CLI/profile bypass.

## 9. Proxmark5 accessory — F-45 to F-51

Proxmark5 is optional, not a network-diagnostics prerequisite. Official Iceman documentation describes the PM5 BWM (ESP32-C2) forwarding path, Wi-Fi station/TCP and BLE transports. Wireless requires BWM and BWM-enabled firmware. Exact firmware/client/security behavior must be verified before release.

### F-45 — PM5 connection/orchestration
One accessory screen supports USB baseline and optional Wi-Fi/BLE. Show transport, device/firmware identity, BWM status, latency and connection state. Use official Iceman client; do not reimplement PM3 protocol. Serialize jobs unless upstream proves concurrency. Acceptance: connect/disconnect/reconnect on each transport; cable/radio loss handled; USB remains fallback.

### F-46 — PM5 Wi-Fi
Connect to PM5 BWM on selected Wi-Fi network and use official client over TCP. Setup over USB or BLE; show SSID label/IP/hostname/port/status; never log PSK. Requires BWM firmware, official TCP transport and valid route. Official guide describes plain TCP: require isolated trusted SSID/VLAN, firewall ACL, no WAN/port-forwarding. Acceptance: join/status/connect/stop and route-loss handling; untrusted network blocked by product policy.

### F-47 — PM5 BLE
Scan/select BWM and connect without external PC. Show name/address type/security/pairing state; provide disconnect/forget. Verify current GATT service/characteristic, pairing and native Linux transport or maintained bridge. Command reference lists BLE pairing/passkey controls while BWM usage text describes plaintext/no bonding; resolve mismatch on exact firmware. If unauthenticated plaintext GATT remains, mark insecure and disable outside trusted lab. Acceptance: pair/reconnect/forget, PM5 reboot and radio-loss recovery.

### F-48 — PM5 status/battery
Read-only screen for PM5 firmware, FPGA/BWM version, battery %, voltage, temperature, health, power-save and wireless status. Use official status commands; unknown fields remain unknown. No automatic charger/voltage writes. Acceptance: parser fixtures and real-device comparison.

### F-49 — Authorized LF/HF tag workflow
Guide identification/read of user-owned or lab tags; show technology/frequency, protocol and available metadata. Official PM5 client commands and supported antennas; LF 125–500 kHz/HF 13.56 MHz only as verified. UHF excluded until client/antenna support confirmed. RF read is active; exact operation confirmed. Mask UID in general reports. No automatic write/clone.

### F-50 — RFID capture/analysis/export
Capture authorized LF/HF exchanges, demodulate/analyze locally and export bounded traces. Store timestamp, antenna/frequency, parser version and metadata separately. Raw dumps may contain credentials; sensitive export opt-in. Acceptance: round-trip capture/analysis, truncation/drop flags and no raw artifact in general reports by default.

### F-51 — Test-tag write/verify/emulation
Optional lab workflow for blank test media or user-created profiles, with dry-run preview, media type, affected blocks, backup and verify. High-risk RF write/emulation disabled by default; only designated lab media; no third-party credential cloning/replay. First release may remain read-only. Requires separate safety review and hardware tests.

### PM5 wireless security/version gate

- PM5 BWM is an accessory; wireless requires BWM-enabled firmware (official build option PLATFORM_EXTRAS=BWM).
- Official BWM guide describes Wi-Fi STA + TCP and BLE GATT forwarding. It describes plain TCP and no BLE bonding, while current command reference lists BLE pairing/passkey controls. Treat this documentation/firmware discrepancy as a release blocker until measured on the exact version.
- Never expose PM5 TCP port to internet. Prefer USB; otherwise isolated trusted LAN. Treat BLE as insecure until pairing and encryption are verified.
- Do not automatically flash PM5/BWM firmware from this app.
- Bulk transfer over BLE/Wi-Fi may be slower than USB and have streaming limitations.

## 10. Optional automotive CAN adapter — F-52

### F-52 — Read-only automotive CAN capture
Optional separate lab/bench module inspired by CAN capture and black-box evidence practices in Flipper Tesla projects. Capture/timestamp frames, show IDs/rates and export traces. Decoding requires a validated signal database and applicability metadata. Requires external CAN transceiver/interface; no assumption that Flipper One has a compatible ready-made adapter. Receive-only by design: no frame injection/replay/spoofing, ECU writes, steering/braking/powertrain control or driver-assistance modification. M7 only; isolated bench acceptance first, including bitrate, timestamps, errors and bus-off behavior. Do not connect to road vehicle until electrical isolation/safety independently reviewed.

## 11. Repository reuse review

| Repository | Useful extraction | Decision |
|---|---|---|
| [hypery11/flipper-tesla-fsd](https://github.com/hypery11/flipper-tesla-fsd) | CAN capture/candump, capability detection, test profiles, host protocol tests and black-box evidence patterns | Ideas/test methodology only for optional F-52. Exclude FSD unlock, nag suppression, CAN injection, steering/powertrain changes and vehicle config replay. Different device/add-on; not a network diagnostics dependency. |
| [teslamotors/buildroot](https://github.com/teslamotors/buildroot) | Embedded Linux package/configuration practices | No direct code reuse. Tesla-maintained Buildroot fork; current Flipper One plan is Debian/Flipper OS package integration. Do not replace target rootfs/toolchain. Revisit only if official Flipper image build requires Buildroot. |
| [Lunars/tesla](https://github.com/Lunars/tesla) | Historical rooted MCU1/Tegra Tesla scripts | Exclude: targets legacy Model S/X MCU1/Tegra, not Flipper One or Model Y network diagnostics. |
| [Zeratul-X/web-tracing-analysis](https://github.com/Zeratul-X/web-tracing-analysis) | Event timeline, trend panels, summary-to-evidence drill-down | UI inspiration only for F-40/F-41. Spring Boot/MySQL/React service conflicts with offline-first architecture if copied wholesale. |
| [Zeratul-X/three-scope-map-skill](https://github.com/Zeratul-X/three-scope-map-skill) | Three.js geographic map presentation | Exclude from topology: Earth/China geographic map is not a network graph; adds frontend stack and GPL-3.0-or-later attribution obligations. |
| [Zeratul-X profile](https://github.com/Zeratul-X) | Profile URL, not a single repository | Relevant candidates above reviewed. If another specific repository was intended, it needs its exact URL for separate assessment. |

### Upstream references

- [Iceman Proxmark5 BWM usage](https://github.com/RfidResearchGroup/proxmark3/blob/master/doc/md/PM5_Start_Here/PM5-BWM-USAGE.md)
- [Iceman command reference](https://github.com/RfidResearchGroup/proxmark3/blob/master/doc/commands.md)
- [Proxmark5 getting started](https://github.com/RfidResearchGroup/proxmark3/blob/master/doc/md/PM5_Start_Here/Getting_Started_With_PM5.md)
- [Flipper One features](https://docs.flipper.net/one/general/features)
- [FlipCTL app contract](https://github.com/flipperdevices/flipctl-slint/blob/dev/docs/apps.md)

Before implementation, pin exact upstream commit/tag, firmware flags, device revision and verification date. Mutable documentation is not proof of target compatibility.

## 12. Milestones and dependency order

Existing roadmap milestone definitions remain authoritative; this table clarifies feature dependencies without renumbering them.

| Milestone | Existing goal | Feature focus / exit |
|---|---|---|
| M0 – Preparation | Source review, development platform and peripheral inventory | Pin source revisions, target OS/tools and capability matrix. |
| M1 – System | Install OS and verify interfaces | Reproducible interface/route/DNS/Wi-Fi/BT inventory on target. |
| M2 – Risk verification | Monitor mode, bands, radiotap, injection, STA+AP and PHY assumptions | Complete verification register. Unverified hardware features remain disabled. |
| M3 – Core | Collectors, SQLite, versioned JSON | Common contract, Safe Mode, job lifecycle, migrations and core tests. |
| M4 – Wired MVP | Discovery, profiles, Ping/TCP, capture, iPerf and reports | F-01/F-02/F-04–F-11/F-13/F-15/F-17/F-36/F-39 target-tested. |
| M5 – Wi-Fi/Bluetooth | Wi-Fi tests, channel map, roaming, Locate, capture and BLE | F-20–F-32 only to verified radio/driver/regulatory limits; F-43. |
| M6 – Security/dashboard | Problem engine, Nmap, monitoring, reports and dashboard | F-03/F-12/F-14/F-26/F-33–F-42 with separate active policy. |
| M7 – Optional | Reflector/LANBERT, Proxmark5 and custom hardware | F-18/F-19/F-45–F-52 independent experiments; never block MVP. |

Suggested implementation order: core policy/data model → passive wired evidence → target hardware validation → bounded wired active tests → reporting/topology → Wi-Fi/BLE → security/OT → accessories.

## 13. Current implementation and verification baseline

As of 2026-11-20, last verified project commit: 8d63a3d62862eca32e2d03c3f5f75f993291cf13.

- [Python checks 44771202433](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202433): 137 tests, Python 3.10–3.13, Ruff, package build, native Ubuntu ARM64 validation, Debian Trixie ARM64 container, docs validation and app startup with a test FlipCTL stub.
- [Python security 44771202422](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202422): pip-audit, Bandit high-severity and compilation checks.
- [CodeQL 44771202629](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202629): Python and GitHub Actions analysis.

These validate code, packaging, simulated FlipCTL startup and Linux ARM64 userspace/container behavior. They do **not** validate a physical Flipper One, actual FlipCTL runtime/UI, Ethernet PHY, Wi-Fi/BT radio, Proxmark5 transport or a live network. Those remain hardware verification tasks.

## 14. Change control

- Keep this document versioned. Change feature status only with linked test/commit or verification record.
- Feature IDs are append-only; do not recycle deferred/removed IDs.
- Changes to traffic class, authorization, target limits, hardware dependencies or retention require safety/architecture review.
- Upstream reuse decisions belong in feature-matrix.md/upstream-watch.md; this document defines product behavior and acceptance.
- Release notes distinguish CI success, target-device verification and live-network validation.
