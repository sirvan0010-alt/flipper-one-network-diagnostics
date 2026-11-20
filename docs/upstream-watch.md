# Upstream watch and overlap register

Last reviewed: 2026-11-20

This register prevents duplicate implementation and tracks official changes that can invalidate our assumptions. Upstream specifications are not automatically proof of shipped functionality.

## Repositories and sources to watch

| Upstream source | What we watch | How it affects our project |
|---|---|---|
| [flipperone-docs](https://github.com/flipperdevices/flipperone-docs) | Features, Flipper OS, FlipCTL, hardware specs, open tasks | Authoritative published product intent and documented constraints |
| [flipctl](https://github.com/flipperdevices/flipctl) | Architecture proposals, backend/API, wrappers, releases, PRs/issues | High-level proposal; do not treat as stable plugin API |
| [flipctl-slint](https://github.com/flipperdevices/flipctl-slint) | Current panel UI, Python/JS app contract, runtimes, app catalogue and example apps | Primary on-device app integration target |
| [flipperone-ui](https://github.com/flipperdevices/flipperone-ui) | Built-in display, navigation, controls, UI APIs | Avoid rebuilding device-level UI |
| [flipperone-linux-build-scripts](https://github.com/flipperdevices/flipperone-linux-build-scripts) | RootFS, packages, profiles, kernel/image changes | Runtime and packaging compatibility |
| [flipperone-testing](https://github.com/flipperdevices/flipperone-testing) | Test harnesses, fake FlipCTL, validation scripts | Desktop/CI smoke tests only; not a hardware emulator |
| [flipper-linux-kernel](https://github.com/flipperdevices/flipper-linux-kernel) | Driver and kernel changes | Wi-Fi/Ethernet/Bluetooth feasibility |
| [flipperone-hardware](https://github.com/flipperdevices/flipperone-hardware) | Board revisions, PHY/radio/port changes | Hardware capability assumptions |
| [flipperone-mcu-firmware](https://github.com/flipperdevices/flipperone-mcu-firmware) | Display/input/power integration | Device-native control and battery behavior |

## Initial overlap assessment

| Capability | Official Flipper status in published docs | Our policy |
|---|---|---|
| FlipCTL UI, device display and controls | Defined as core platform UX | Do not build replacement UI framework |
| App wrappers for ping/Nmap/traceroute | Explicit FlipCTL concept | Reuse when implemented; avoid redundant shell menus |
| Network sniffer OS profile | Listed as built-in profile | Verify installed contents; do not build another profile |
| Ethernet transparent MitM sniffer and PCAP | Explicit product feature/user story | Integrate; add diagnostics and analysis above capture |
| Passive/active LAN discovery | Explicit product feature/user story | Reuse native discovery; enrich results and guide diagnosis |
| Router, VPN gateway, USB network adapter | Explicit product feature/user stories | Out of our scope |
| Guided network AutoTest and fault explanation | Not established by reviewed feature page | Core differentiated project scope |
| DHCP/DNS/gateway/HTTP/TCP/MTU and latency/loss/jitter diagnosis | Individual tools exist; integrated NetAlly-like workflow not established | Build as orchestrated tests |
| LLDP/CDP, VLAN evidence, SNMP/path analysis | Not established as complete built-in workflow | Build where hardware/network permit |
| Baselines, historical trends, reports | Not established as complete built-in workflow | Build locally |
| Wi-Fi/BLE capability and security tests | Need check current product specs, OS tools, drivers and hardware | Build only after evidence and target tests |

## 2026-11-20 findings

1. The official Features page explicitly documents Ethernet MitM sniffer and passive/active LAN discovery. These are product/user-story specifications; implementation and release status still need confirmation.
2. The Flipper OS page lists a Network sniffer OS profile.
3. The current image build scripts build the panel UI from `flipctl-slint`, not from the older high-level `flipctl` architecture repository. The `flipctl-slint` README and `docs/apps.md` document a Python/JavaScript script app contract and an AppImage app contract.
4. `flipctl-slint` commit `483ad588f5cd21e26eed416c949811821bb29a1f` (2026-11-19) documents Python `.fap.py` apps using `flipctl.Menu`, `Detail`, `Log`, physical keys and the Python Runtime app (`provides = "py"`).
5. Its tree already contains `apps/ping.fap.py` and an experimental `apps/Test Tools/ethernet-tester.fap.py`. The latter describes reserved RTL8211F registers, privileged MII ioctls, raw test frames, PHY link drops and a kernel polling race. Do not treat it as a safe/released cable tester and do not duplicate its low-level method.
6. The published rootfs package manifest at build-scripts commit `836f7e7f8937cba3a25a37b8f4ad888a121783cc` explicitly includes `iproute2`, `iperf3`, `iputils-ping`, `iw`, `tcpdump`, `traceroute`, `bluez`, `python3-pandas` and `python3-plotly`. It does not explicitly list `ethtool`, `nmap`, `lldpd`, `snmp` or `tshark`; detect optional tools instead of assuming they exist.
7. The public `flipperdevices/flipctl` repository's default branch is `dev` (latest visible commit `3285ba6caf`, 2026-06-19). Its README describes a backend, HTML/JavaScript frontend, headless WebKit renderer on DRM, app wrappers and multiple control interfaces. It explicitly invites architecture and plugin-system proposals. Open PRs include the web/TUI/plugin-system prototype and architecture proposals; we did not find a stable versioned third-party plugin contract. The README describes the linked Fake FLipCTL2 as a rough AI-made prototype needing rework, not a production runtime.
5. `fake-flipctl2` in `flipperone-testing` is a test UI harness, not the production FlipCTL implementation or a complete Flipper One emulator.
6. The official Open Tasks page was refreshed at `flipperone-docs` commit `59b8688dfe` (2026-11-20 01:19 UTC). It currently lists no open `help wanted` tasks in the Testing sub-project; the User Interface sub-project does list an Nmap wrapper UI task (#15). Do not submit a contribution without first reading the live issue and its comments.
7. The Flipper Network testing documentation now explicitly groups Wi-Fi access-point, client, concurrency and dual-band test modes; Ethernet, Bluetooth, cellular and satellite tests are separate areas. This is a testing plan/category, not proof every mode is shipped or supported by the production image.

Sources:
- https://docs.flipper.net/one/general/features
- https://docs.flipper.net/one/cpu-software/flipper-os
- https://docs.flipper.net/one/cpu-software/flipctl
- https://github.com/flipperdevices/flipctl
- https://github.com/flipperdevices/flipctl-slint
- https://github.com/flipperdevices/flipctl-slint/blob/dev/docs/apps.md
- https://github.com/flipperdevices/flipctl-slint/blob/dev/apps/ping.fap.py
- https://github.com/flipperdevices/flipctl-slint/blob/dev/apps/Test%20Tools/ethernet-tester.fap.py
- https://github.com/flipperdevices/flipctl/pulls
- https://github.com/flipperdevices/flipperone-testing/tree/dev/fake-flipctl2\n- https://docs.flipper.net/one/testing/network\n- https://github.com/flipperdevices/flipperone-ui/issues/15\n- https://github.com/flipperdevices/flipperone-linux-build-scripts/commit/836f7e7f89
- https://docs.flipper.net/one/dev-log/10
- https://docs.flipper.net/one/how-to-join

## Review procedure

Before adding or changing a feature:
1. Check upstream documentation and relevant repository default branch.
2. Check recent commits, releases, open issues and pull requests.
3. Search source code and test harness for an existing implementation.
4. Classify upstream state as: documented concept, prototype, merged code, tested on target, or released.
5. Mark each item in our feature matrix as reuse, integrate, extend, or implement.
6. Record the review date and exact upstream commit/tag/issue/PR references.
7. Do not implement a competing UI, profile manager, router, VPN, bridge/sniffer or generic discovery workflow without a documented gap.

## Limitations of monitoring

A periodic review can identify public changes; it cannot guarantee instant detection of every upstream change or inspect private development. Re-check upstream before a compatibility-sensitive release and whenever a relevant issue/PR is mentioned.
