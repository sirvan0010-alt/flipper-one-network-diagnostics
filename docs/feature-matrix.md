# Feature matrix F-01–F-57: reuse vs. build

Last reviewed: 2026-11-20. The authoritative backlog remains in [AGENTS.md](../AGENTS.md); detailed behavior and acceptance criteria are in [functional specification](functional-specification.md). This document decides where our implementation should live.

**Status vocabulary**

- **Reuse** — call an upstream/system capability; do not reimplement it.
- **Integrate** — consume upstream output and add workflow, normalization, persistence or findings.
- **Build** — genuinely missing higher-level diagnostic logic.
- **Verify first** — product documentation or an experimental app exists, but target implementation/capability is not proven.
- **Defer** — not part of the first wired MVP or depends on unverified hardware.

A feature appearing in product documentation, a source tree or an App Manager catalogue is not proof that it is installed or released in the device image. Hardware validation remains separate.

| ID | Planned capability | Upstream overlap / dependency | Our action |
|---|---|---|---|
| F-01 | Wired AutoTest | Native link, route, discovery and standard Linux tools are available building blocks; no complete NetAlly-style guided result established | **Partially implemented:** local-check aggregates local config only; **build next:** DHCP, DNS resolution, gateway and bounded active checks behind authorization |
| F-02 | Profiles and test targets | FlipCTL provides app/menu framework, not our diagnostic profiles | **Build** local profile schema and target groups |
| F-03 | Periodic AutoTest | No complete equivalent confirmed | **Build** scheduler and history; defer until core is stable |
| F-04 | Switch test (CDP/LLDP/EDP) | lldpd is not explicitly listed in the reviewed rootfs manifest; native discovery may expose some data | **Verify first**, then integrate native LLDP/CDP or add a bounded parser |
| F-05 | VLAN detection | Native discovery/sniffer may expose VLAN evidence; published product feature mentions VLAN visibility | **Integrate** captured/observed VLAN evidence; do not invent unsupported PHY capability |
| F-06 | Link speed and duplex | ethtool is not explicitly listed in the reviewed rootfs manifest | **Reuse** ethtool when present; fall back to kernel sysfs carrier/speed/duplex attributes when absent; verify PHY reports |
| F-07 | LLDP PoE offered power | Depends on LLDP TLVs and switch support; not PoE load measurement | **Build** read-only TLV interpretation; never claim loaded PoE testing |
| F-08 | Ping / TCP Connect / MTU | A Ping .fap.py app exists upstream; standard Linux tools are available | **Partially implemented:** one-target ICMP and one-port TCP CLI plus one-shot gateway UI behind explicit per-invocation confirmation; reuse native Ping UI; build integrated AutoTest and MTU workflow |
| F-09 | HTTP / FTP response time | Standard protocols/tools exist; no integrated test workflow confirmed | **Build** bounded timing checks and result normalization |
| F-10 | Wired Discovery | Official Flipper product docs describe LAN discovery | **Integrate** native inventory and enrich/persist; avoid competing scanner |
| F-11 | Layered LAN discovery | Official product docs describe passive and active discovery | **Reuse/integrate** native discovery; our app controls authorization and presents stages |
| F-12 | Problem engine | No complete equivalent confirmed | **Partially implemented:** evidence-bounded Local Check assessment with explicit uncertainty; **build next:** cross-layer and active-test correlations |
| F-13 | Path Analysis | FlipCTL exposes traceroute wrapper concept; SNMP/LLDP correlation is separate | **Reuse** traceroute; **build** L2/L3 correlation and interpretation |
| F-14 | Topology map | Native discovery may supply nodes/links; no complete local diagnostic graph confirmed | **Build** graph from verified LLDP/SNMP observations |
| F-15 | Packet capture 1G | Flipper OS documents a Network Sniffer profile; tcpdump is in the reviewed rootfs manifest | **Reuse/integrate** native capture and PCAP; add filters, summaries and links to findings |
| F-16 | Ethernet MitM sniffer | Official product docs describe Ethernet MitM Sniffer | **Verify first**, then integrate capture output; do not build a competing transparent bridge |
| F-17 | iPerf | iperf3 is explicitly in the reviewed rootfs manifest | **Reuse** iperf3; build guided test orchestration and result interpretation |
| F-18 | Reflector + controller | No confirmed native equivalent; needs two endpoints and a defined protocol | **Defer** to M7; design only after wired MVP |
| F-19 | LANBERT / media soak | Upstream Ethernet Tester is experimental and documents risky PHY-register/MII/raw-frame operations and link-drop races | **Defer/verify first**; do not copy undocumented PHY writes or claim cable BER testing |
| F-20 | Wi-Fi AutoTest | iw, NetworkManager and Wi-Fi tooling exist in the reviewed rootfs | **Build** workflow using native tools; validate driver/radio support on device |
| F-21 | Air Quality | iw can observe Wi-Fi networks; no non-Wi-Fi spectrum analyser is established | **Build** Wi-Fi-only channel utilization estimates; explicitly exclude non-Wi-Fi interference |
| F-22 | Channel map | Native scan results can supply AP/channel evidence | **Integrate/build** aggregation; do not imply simultaneous multi-channel capture with one radio |
| F-23 | AP and client list | Native Wi-Fi/LAN discovery may expose devices | **Integrate** native observations and add labels/authorization state |
| F-24 | Roaming test | NetworkManager and kernel events are potential data sources | **Build** correlation of association changes, signal and connectivity |
| F-25 | Locate | RSSI from scans is available in principle; directional antenna is an external hardware dependency | **Build** signal trend; **verify** driver/scan cadence; directional locating deferred |
| F-26 | Wi-Fi security audit | Native Wi-Fi scan/configuration provides evidence but not a full audit | **Build** passive/configuration checks; no deauth or disruptive tests |
| F-27 | Wi-Fi packet capture | Depends on MT7921 driver monitor mode, radiotap and regulatory constraints | **Verify first** on target; integrate native capture where supported |
| F-28 | Wi-Fi 7 visibility | Device radio is documented as Wi-Fi 6E; passive decoding of selected Wi-Fi 7 fields is not guaranteed | **Defer/verify first**; never claim Wi-Fi 7 operation |
| F-29 | Site survey | No floorplan workflow confirmed in native app | **Build** local measurement logging and export; simultaneous active/passive work may need second radio |
| F-30 | BLE discovery/survey | BlueZ is in the reviewed rootfs manifest | **Reuse** BlueZ; build inventory and local signal survey if supported |
| F-31 | Ping while walking | Upstream Ping app exists; BLE/Wi-Fi RSSI can be sampled separately | **Integrate** ping statistics with timestamped signal observations |
| F-32 | Regulatory domain | Kernel regulatory database and iw are native OS responsibilities | **Reuse** OS controls; display current domain and explain restrictions, do not bypass them |
| F-33 | IoT/OT/ICS discovery | Native discovery provides network observations; protocol classification is higher-level | **Build** cautious passive classification and confidence scoring |
| F-34 | Nmap in AutoTest | Nmap wrapper is an upstream UI task/proposal; nmap is not explicitly in reviewed rootfs package list | **Reuse** upstream wrapper if shipped; otherwise detect optional Nmap and gate active scans |
| F-35 | CVE lookup | No built-in vulnerability database/service confirmed | **Defer**; optional offline signatures and NSE only with explicit authorization |
| F-36 | Discovery Monitoring | Native discovery can supply observations; our SQLite baseline/diff exists | **Build/integrate** snapshots, history and change alerts |
| F-37 | Batch authorization | No native equivalent confirmed | **Build** local trusted/unknown labels and batch workflow |
| F-38 | CIS/NIS2 reports | No native compliance report confirmed | **Build** evidence mapping; clearly state it is not certification or compliance attestation |
| F-39 | Local reports | FlipCTL provides UI/runtime; report generation is our product logic | **Build** offline HTML/CSV first; PDF only after lightweight dependency evaluation |
| F-40 | Trend graphs | python3-plotly exists in rootfs manifest but heavy UI/graph use needs resource testing | **Build** compact on-device summaries; optional richer local export |
| F-41 | Local web dashboard | FlipCTL already provides optional remote/browser frontend | **Reuse** FlipCTL remote view for app control; add only a separate diagnostics dashboard if a clear gap remains |
| F-42 | Remote control | FlipCTL already has web/desktop remote-control concepts | **Reuse** platform remote control; do not implement VNC/control server |
| F-43 | Import/export settings | No complete diagnostic-profile format confirmed | **Build** versioned local JSON import/export |
| F-44 | Safe Mode | No assumption that platform UI policy equals our operation authorization | **Build** fail-closed operation policy in our core and expose state in app |
| F-45 | Proxmark5 connection/orchestration | Official Iceman client; USB baseline, BWM wireless transports need exact firmware verification | **Defer/verify first** to M7; do not reimplement PM3 protocol |

| F-46 | PM5 Wi-Fi transport | BWM Wi-Fi STA + TCP server and official TCP client transport; plain TCP security boundary | **Verify first** on exact BWM firmware; isolated LAN only, no WAN exposure |
| F-47 | PM5 BLE transport | BWM GATT forwarding; native Linux BLE transport or bridge; pairing documentation needs reconciliation | **Verify first** on exact firmware; disable control if unauthenticated plaintext |
| F-48 | PM5 status/battery | Official hw status/BWM telemetry commands | **Build** read-only adapter after transport verified |
| F-49 | Authorized LF/HF workflow | Official PM5 client command tree and antenna support | **Verify first** on PM5; own/lab media only; UHF excluded until supported |
| F-50 | RFID capture/analysis/export | Official capture/sniff/trace and analysis commands | **Verify first**; bounded capture and protected sensitive artifacts |
| F-51 | Test-tag write/verify/emulation | PM5 command capabilities, high-risk RF writes | **Defer** until separate safety review and lab hardware tests |
| F-52 | Adapter-neutral read-only automotive CAN capture | WiCAN PRO owned by user; future adapters remain possible | **Integrate** generic RX-only contract; WiCAN PRO is first planned adapter; M7 |\n| F-53 | WiCAN PRO discovery/capabilities | MeatPi Wi-Fi/BLE/USB and firmware-specific interfaces | **Verify first** exact firmware/API; manual endpoint selection; fail closed on unknown versions |\n| F-54 | WiCAN PRO passive CAN stream | Candidate Wi-Fi TCP/SLCAN, GVRET, BLE; protocol support varies by firmware | **Verify first** stable 4.x stream; receive-only parser; prove zero TX; no broad scan |\n| F-55 | WiCAN PRO capture import/export | SD/local logging and candidate candump/ASC/BLF/MDF4 formats | **Integrate/build** only verified formats; preserve raw artifact, checksum and provenance |\n| F-56 | AutoDiag evidence interoperability | Existing AutoDiag-WiCAN-Pro and AutoDiag-WiCAN-Diagnostic-Data projects; autodiag-can-capture-v1 | **Reuse/integrate** versioned contract and evidence packs; do not copy Kotlin runtime/classifier/scorer |\n| F-57 | CAN observation analysis/timeline | Existing AutoDiag PERIODIC/EVENT/MIXED classifier, counter filtering and M2 scorer | **Build** basic frame-rate/periodicity/gap timeline; keep advanced automotive analysis in AutoDiag |

## External repository reuse review

- [hypery11/flipper-tesla-fsd](https://github.com/hypery11/flipper-tesla-fsd): only CAN capture, timestamping, capability detection, host-side test fixtures and black-box evidence patterns may inform optional F-52. Exclude FSD unlock, nag suppression, CAN injection/replay and vehicle-control changes.
- [teslamotors/buildroot](https://github.com/teslamotors/buildroot): no direct code reuse; the current target plan uses Debian/Flipper OS packages, not Tesla's Buildroot fork.
- [Lunars/tesla](https://github.com/Lunars/tesla): exclude; rooted legacy MCU1/Tegra Model S/X scripts are outside product scope.
- [Zeratul-X/web-tracing-analysis](https://github.com/Zeratul-X/web-tracing-analysis): dashboard timeline/trend/drill-down ideas only; do not import its Spring Boot/MySQL service into an offline-first app.
- [Zeratul-X/three-scope-map-skill](https://github.com/Zeratul-X/three-scope-map-skill): exclude; geographic Earth/China map is not a network topology graph.

## Current implementation slice

The first implementation slice is intentionally passive and local:

- doctor: host/runtime/tool inventory.
- interfaces: local interface addresses and state.
- link: read-only ethtool link data, if available.
- routes: local IPv4/IPv6 default-route inventory.
- dns: local resolver-file parsing; no DNS query.
- local-check: aggregate local-only interface/link/DNS configuration and provide an evidence-bounded assessment; explicitly not a reachability test.
- SQLite history and named inventory baselines.

Interface inventory uses /sys/class/net/<interface>/wireless to distinguish Wi-Fi devices from wired Ethernet; unknown media are not silently treated as wired. These are building blocks, not a complete AutoTest. No DHCP exchange, DNS resolution, gateway ping, TCP probe, active discovery, packet injection or port scan is run by these commands.

## Decision gates before enabling active tests

1. Safe Mode must be default and enforced in the core, not just hidden in the UI.
2. Each active test must state targets, ports/protocols, duration, rate and expected traffic before execution.
3. User must explicitly authorize a bounded target/range; no implicit whole-subnet scan.
4. Tests must have timeout, cancellation and bounded concurrency.
5. Store authorization context and test parameters with the result.
6. Keep passive collection available when active operations are disabled.
7. Verify target OS tools, privileges, interface names and hardware before enabling a collector.

Active test authorization and current CLI boundaries are documented in [active-tests.md](active-tests.md).

## Sources reviewed

- [Flipper One product features](https://docs.flipper.net/one/general/features)
- [Flipper OS](https://docs.flipper.net/one/cpu-software/flipper-os)
- [FlipCTL app development](https://github.com/flipperdevices/flipctl-slint/blob/dev/docs/apps.md)
- [Upstream Ping app](https://github.com/flipperdevices/flipctl-slint/blob/dev/apps/ping.fap.py)
- [Experimental Ethernet Tester](https://github.com/flipperdevices/flipctl-slint/blob/dev/apps/Test%20Tools/ethernet-tester.fap.py)
- [Flipper One Linux rootfs package manifest](https://github.com/flipperdevices/flipperone-linux-build-scripts/blob/dev/debian-rk3576-ospack.yaml)
- [Upstream overlap register](upstream-watch.md)

Hardware and upstream implementation status must be rechecked at the commit/tag being integrated. This matrix is not proof of feature availability on a shipped device.


## WiCAN PRO upstream references\n\n- [MeatPi WiCAN PRO product](https://www.meatpi.com/products/wican-pro/)\n- [MeatPi WiCAN PRO manual and firmware-version warning](https://docs.meatpi.com/wican-pro/)\n- [MeatPi WiCAN PRO datasheet](https://docs.meatpi.com/wican-pro/hardware/datasheet/)\n- [MeatPi WiCAN firmware](https://github.com/meatpiHQ/wican-fw)\n- [WiCAN PRO app transports](https://docs.meatpi.com/wican-pro/send-data/apps/)\n\nThe current MeatPi docs warn that firmware 6.0 is beta and stable 4.52 uses a different legacy manual; v6 API pages must not be applied to 4.x. The user's installed version is not yet known. See [WiCAN PRO integration specification](wican-pro-integration.md) for firmware gates, RX-only constraints and AutoDiag interoperability.\n\n## Proxmark5 upstream references

- [Iceman PM5 BWM usage](https://github.com/RfidResearchGroup/proxmark3/blob/master/doc/md/PM5_Start_Here/PM5-BWM-USAGE.md)
- [Iceman command reference](https://github.com/RfidResearchGroup/proxmark3/blob/master/doc/commands.md)
- [PM5 getting started](https://github.com/RfidResearchGroup/proxmark3/blob/master/doc/md/PM5_Start_Here/Getting_Started_With_PM5.md)

The BWM guide documents Wi-Fi STA/TCP and BLE GATT forwarding. It describes plain TCP and no BLE bonding, while the command reference lists pairing/passkey controls. This discrepancy must be tested against the exact firmware before enabling wireless control. Full UX, safety and acceptance contracts are in [functional-specification.md](functional-specification.md).
