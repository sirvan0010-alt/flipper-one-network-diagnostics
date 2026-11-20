# WiCAN PRO integration specification

**Status:** design / hardware-integration contract  
**Version:** 0.1.0  
**Reviewed:** 2026-11-20  
**Target:** owned MeatPi WiCAN PRO + Flipper One Network Diagnostics  
**Milestone:** M7 optional accessory; does not block wired MVP

This document defines how the project may use the user's existing WiCAN PRO without duplicating the separate automotive diagnostic projects.

## 1. Decision and project boundaries

WiCAN PRO is now the **primary planned automotive CAN adapter** for this project, not a hypothetical future transceiver. It is an ESP32-S3-based OBD-II/CAN interface with a dedicated OBD interpreter, Wi-Fi, BLE, USB-related interfaces and local SD logging.

Keep responsibilities separate:

- **Flipper One Network Diagnostics:** adapter discovery, safe connection, passive stream acquisition/import, timestamped evidence, local visualization, storage and export.
- **AutoDiag-WiCAN-Pro:** existing Android/Kotlin runtime and automotive diagnostic workflows. Reuse its existing transport/core work where appropriate; do not fork or reimplement it in this repository.
- **AutoDiag-WiCAN-Diagnostic-Data:** canonical vehicle profiles, evidence definitions, provenance and data contracts. Reuse the existing `autodiag-can-capture-v1` contract and evidence-pack conventions where compatible.
- **WiCAN PRO firmware:** device-side CAN/OBD interface. Treat its firmware API and protocol support as version-specific.

The Flipper integration is an adapter/consumer, not a replacement for the Android application or a new ECU diagnostic tool.

## 2. Hardware and firmware facts

Official MeatPi sources reviewed 2026-11-20:

- Product page: https://www.meatpi.com/products/wican-pro/
- Documentation landing page: https://docs.meatpi.com/wican-pro/
- Datasheet: https://docs.meatpi.com/wican-pro/hardware/datasheet/
- WiCAN firmware repository: https://github.com/meatpiHQ/wican-fw
- WiCAN PRO application transports: https://docs.meatpi.com/wican-pro/send-data/apps/

Documented hardware includes ESP32-S3, dedicated OBD interpreter, Wi-Fi 2.4 GHz, Bluetooth LE, microSD logging, a USB host port and multiple vehicle-bus/protocol interfaces. The published product/datasheet describes raw CAN, ISO 15765-4, J1939, MS-CAN, GMLAN single-wire CAN and legacy OBD protocols. These are adapter capabilities, **not a claim that this application supports or safely captures every bus/protocol**.

### Firmware-version gate — important

The current MeatPi documentation landing page explicitly warns that firmware 6.0 is beta and directs users to stable 4.52. The new `docs.meatpi.com/wican-pro/` manual, including its HTTP/BLE API pages, describes firmware 6.0.0 or newer and states that it does not apply to 4.x.

Therefore:

1. Do not tell the user to upgrade to firmware 6 beta.
2. Do not code against the v6 HTTP/BLE API and assume it exists on stable 4.x.
3. First read the installed firmware version from the user's device and pin the matching legacy manual/source tag.
4. Record hardware revision, firmware version, transport mode and exact stream protocol in every capture.
5. Firmware update/recovery is out of scope for this application.

The user's installed firmware version is currently **unknown**. The existence of the physical adapter is known; exact protocol/API compatibility is not yet verified.

### USB distinction

Do not assume USB-C is a general CAN data port. The published documentation describes USB-C primarily for flashing/debug/recovery; the USB host port is for accessories. Any USB serial/network transport must be confirmed on the installed WiCAN PRO firmware and on the actual Flipper One host before implementation.

## 3. Transport strategy

Use a transport-neutral interface:

`CanAdapter` → `CanTransport` → `FrameStream` → `CanEvidenceNormalizer`

Transport order:

1. **Wi-Fi TCP / SLCAN or documented receive stream:** first candidate for a Flipper integration, subject to exact 4.x firmware verification.
2. **Wi-Fi GVRET / other documented stream:** optional, only after protocol and firmware compatibility are proven.
3. **BLE:** secondary transport; verify actual GATT service, pairing, encryption, MTU, loss behavior and stable-4.x support. Do not infer v6 BLE API compatibility.
4. **USB:** investigate only after verifying the exact device-side USB mode and Flipper host enumeration. USB-C flashing/debug alone is not a CAN data transport.
5. **Offline SD-card import:** useful fallback for captured files where the file format and export path are verified; no live connection required.

Never hardcode ports, endpoints, GATT UUIDs or protocol framing from a different firmware major version. Discover capabilities or load a version-pinned profile. Unknown versions/protocols fail closed.

## 4. Read-only safety contract

The first release is strictly passive/read-only.

Allowed:
- receive raw CAN frames from a configured WiCAN stream;
- import already-created local capture files;
- inspect adapter identity, firmware, transport state and read-only counters;
- calculate frame IDs, DLC, rate, bus-load estimates only where input supports them, timestamp gaps, duplicate patterns and capture-quality indicators;
- decode only with a validated, explicitly selected DBC/profile and retain raw source frames;
- correlate capture windows with externally supplied event metadata as temporal correlation only.

Forbidden in this project phase:
- CAN frame transmit, injection, replay, spoofing or fuzzing;
- OBD PID polling initiated by this app;
- UDS diagnostic requests, ECU writes, DTC clearing, actuator routines, coding or programming;
- J2534 PassThru control/reflash workflows;
- steering, braking, propulsion, driver-assistance or vehicle-configuration changes;
- automatic firmware/configuration changes to WiCAN PRO.

Important: SLCAN, GVRET, ELM/OBD and other protocols may support both receive and transmit. A UI label saying "read-only" is insufficient. The implementation must expose a receive-only API, reject transmit/control opcodes, and include tests that prove no transmit path is reachable. Before any vehicle-connected acceptance test, verify zero CAN TX with an independent bus-side monitor or isolated bench arrangement. A receive-only software client does not make the adapter electrically receive-only.

## 5. Data model and evidence quality

Preserve raw evidence before interpretation. Each capture includes:

- capture UUID and schema version;
- adapter model/hardware revision and firmware version;
- selected bus/interface and configured bitrate, if known;
- transport and stream protocol;
- host monotonic timestamps and wall-clock/UTC mapping;
- adapter timestamps, if supplied, with clock-quality metadata;
- CAN ID, standard/extended flag, RTR/error flags where available, DLC and payload bytes;
- frame count, dropped-frame indicators, sequence gaps, buffer overflow and disconnect/reconnect events;
- start/end time, capture duration, filter and explicit capture profile;
- provenance, parser/decoder version and DBC/profile identity;
- safety mode and confirmation record.

Never invent bitrate, bus identity, ECU identity, signal meaning or causal relationships. Unknown remains unknown. If the adapter does not expose dropped-frame counters, report that loss cannot be ruled out.

Use the existing `autodiag-can-capture-v1` schema where compatible. Do not silently fork it; if an extension is required, version it and document compatibility. Keep original capture artifacts immutable and link derived observations to their source offsets/timestamps.

## 6. Existing AutoDiag work — reuse, do not duplicate

Prior work in `AutoDiag-WiCAN-Pro` / `feat/can-mining-pipeline` includes a read-only capture direction, transport metadata, evidence sequencing, `autodiag-can-capture-v1`, `CanMiningDiff`, PERIODIC/EVENT/MIXED classification, counter filtering and an M2 scorer. The data companion repository holds profiles/evidence/provenance.

Integration rules:

- inspect the current upstream branch/PR state before writing a second implementation;
- prefer importing/exporting the versioned evidence contract over copying Kotlin code into Python;
- keep the PERIODIC/EVENT/MIXED classifier, counter detection and automotive-specific scoring in AutoDiag unless a separate portable specification is agreed;
- Flipper may display/import resulting labels and evidence but must not claim to have independently reproduced the classifier;
- event triggers (including any Tesla API-derived event) are metadata for temporal alignment only, not proof that the event caused a CAN frame or vehicle behavior;
- retain the existing Monday/Thursday review cadence as an AutoDiag workflow, not as a hard-coded schedule in Flipper One.

The earlier AutoDiag wireless blocker must be resolved against the exact WiCAN PRO firmware and the target host. Do not assume a Wi-Fi module incompatibility has disappeared merely because WiCAN PRO advertises Wi-Fi/BLE; test actual network association, TCP stream and Flipper host routing.

## 7. Feature contracts

### F-52 — Adapter-neutral read-only automotive CAN capture

Keep a generic CAN capture contract so a future adapter can be added without changing storage/UI. WiCAN PRO is the first planned adapter. Receive-only, no TX. M7, optional.

### F-53 — WiCAN PRO discovery and capability report

Discover a manually configured or explicitly selected WiCAN endpoint. Show model, firmware, network identity, reachable transports and supported stream protocols only when verified. No broad network scan; discovery is passive/manual or bounded to a user-selected endpoint. Do not store Wi-Fi passwords in capture records.

Acceptance: stable 4.x and any later supported version have separate fixtures; unknown firmware/API is unsupported, not guessed.

### F-54 — WiCAN PRO passive CAN stream

Consume a documented receive stream, initially prioritize stable-firmware-compatible Wi-Fi transport and a proven protocol such as SLCAN. GVRET/other protocols are optional. Use fixed protocol parsers, bounded buffers, backpressure, cancellation and reconnect handling. Transmit/control operations are not exposed.

Acceptance: golden captures, malformed/truncated frame handling, timestamp ordering, high-rate soak test, disconnect/reconnect, buffer-loss reporting and independent zero-TX verification.

### F-55 — WiCAN PRO capture import and evidence export

Import supported SD/log exports or stream captures without changing source bytes. Candidate formats include candump/ASC/BLF/MDF4 only when verified against the installed firmware and parser. Export raw data plus a manifest; redact vehicle identifiers from general reports by default.

Acceptance: deterministic round-trip for supported formats, explicit unsupported-format error, checksums and provenance.

### F-56 — AutoDiag evidence interoperability

Import/export the existing `autodiag-can-capture-v1` contract and compatible evidence packs. Keep schema version and source project/commit metadata. Do not duplicate Kotlin runtime, classifier or scorer.

Acceptance: contract fixtures validate; unknown major versions are rejected; round-trip preserves timestamps, raw frames, provenance and loss indicators.

### F-57 — CAN observation analysis and timeline

Provide basic on-device summaries: frame rate by ID, periodicity overview, burst/gap detection, timestamp quality, selected event-window comparison and raw-frame drill-down. Advanced counter filtering, PERIODIC/EVENT/MIXED classification and vehicle-specific scoring remain owned by AutoDiag until explicitly ported from a stable specification.

Acceptance: all derived values link to source frames; no unsupported signal decoding; temporal correlation is not described as causation.

### Deferred — OBD/UDS telemetry and diagnostics

Do not add active OBD PID polling, UDS, DTC clearing, J2534 or ECU functions to the first Flipper integration. Although WiCAN PRO hardware/firmware advertises these capabilities, many require requests/transmissions and violate the current passive-only boundary. Revisit only with a separate explicit scope and safety decision; do not silently expand F-52–F-57.

## 8. Test plan

Host-side tests first:
- parser fixtures for each pinned stream protocol and firmware;
- malformed frames, extended IDs, DLC limits, error frames and timestamp wrap/reset;
- bounded queue/backpressure and cancellation;
- reconnect and partial capture recovery;
- unsupported firmware/protocol fail-closed;
- no transmit/control command can be generated by the adapter API;
- schema compatibility with AutoDiag fixtures;
- deterministic artifact checksums and redaction.

Hardware validation in stages:
1. Read installed WiCAN firmware/hardware revision; back up configuration.
2. Test on an isolated CAN bench with a passive sender and independent bus monitor.
3. Verify receive stream, timestamps, frame-loss behavior and zero TX.
4. Test Wi-Fi transport on the actual Flipper host; separately test BLE/USB only if supported.
5. Only after these gates, consider a stationary vehicle observation with explicit permission and electrical/safety review. Never test transmit features.

CI mocks and host fixtures do not count as physical WiCAN or Flipper One verification.

## 9. Current blockers / facts to confirm

- Installed WiCAN PRO firmware version and hardware revision.
- Whether the device currently uses stable 4.52 or another 4.x release; do not assume v6 beta.
- Which stable-firmware stream protocols are available in the device's current configuration.
- Wi-Fi TCP reachability from the intended Flipper host and whether the prior AutoDiag Wi-Fi incompatibility still exists.
- BLE pairing/security and stream behavior on the installed firmware.
- Whether any USB data mode actually exposes a usable stream; USB-C flashing/debug is not sufficient.
- Current AutoDiag branch/PR and schema commit before selecting interoperability fixtures.

## 10. References

- MeatPi WiCAN PRO product: https://www.meatpi.com/products/wican-pro/
- MeatPi WiCAN PRO docs and firmware-version warning: https://docs.meatpi.com/wican-pro/
- MeatPi WiCAN PRO datasheet: https://docs.meatpi.com/wican-pro/hardware/datasheet/
- MeatPi WiCAN firmware: https://github.com/meatpiHQ/wican-fw
- MeatPi apps over Wi-Fi/BLE: https://docs.meatpi.com/wican-pro/send-data/apps/
- AutoDiag-WiCAN-Pro: https://github.com/sirvan0010-alt/AutoDiag-WiCAN-Pro
- AutoDiag-WiCAN-Diagnostic-Data: https://github.com/sirvan0010-alt/AutoDiag-WiCAN-Diagnostic-Data
