# Active test authorization

Status: single-target ICMP and single-port TCP collectors are implemented in CLI and are now exposed in the Flipper app behind a one-shot on-device confirmation screen. No live target has been tested.

## Safe Mode

- Safe Mode is the default and blocks active operations.
- The on-device app currently keeps Safe Mode ON and exposes no control that disables it.
- The CLI ping command requires an explicit --confirm-active flag, a literal target IP, and a CIDR/IP scope.
- The target must be inside the scope and must also be present in the explicit authorization target list.
- The authorization is per invocation; it is not saved as a persistent permission.
- The CLI sends only one bounded ICMP test to one IP address: 1–5 requests, 1–5 seconds per request, no automatic retries, no hostname resolution and no subnet scanning.
- A separate TCP Connect command may attempt one TCP handshake to one explicitly authorized port (1–65535) on one authorized IP; it sends no application payload and has a 1–5 second timeout.

Example syntax (documentation only; the reserved TEST-NET address below is not a real target):

```bash
flipper-diag ping \
  --target 192.0.2.1 \
  --scope 192.0.2.1/32 \
  --confirm-active \
  --count 3 \
  --timeout 1 \
  --json
```

Do not execute this against a network unless you own it or have explicit permission from its operator. The scope flag is a technical boundary, not proof of legal authorization.

## TCP Connect example

```bash
flipper-diag tcp-connect \
  --target 192.0.2.1 \
  --port 443 \
  --scope 192.0.2.1/32 \
  --confirm-active \
  --timeout 3 \
  --json
```

The port must be included in the explicit authorization object. A successful handshake does not validate the application protocol; a refusal is not proof that the host is down.

## Passive known-device list

The on-device Known devices screen reads the local kernel IPv4/IPv6 neighbor cache only. Entries may be missing or stale; this screen does not send ARP, NDP or other discovery packets. Native Flipper LAN Discovery remains the preferred full discovery workflow.

## Current limitations

- ICMP echo only; it does not prove DNS, TCP service or Internet reachability.
- Some hosts/firewalls intentionally block ICMP.
- The parser supports the tested iputils and BusyBox summary formats; target output must be verified.
- The Flipper app uses only the detected wired default gateway and a preset port list (53, 80, 443, 22), because the reviewed Python FlipCTL API does not expose free-form text input.
- Each action requires the user to open a confirmation screen and press the explicit Confirm soft key. Cancel sends nothing. There is no global Safe Mode disable.
- Immediately before sending, the app refreshes the wired interface inventory and default route. If the gateway or interface differs from the values shown on the confirmation screen, the action is aborted and the user must reopen and review the test.
- Link-local IPv6 gateways are skipped until the active collectors support an explicit interface/scope ID.
- The on-device flow is unit-tested with mocked sockets/subprocesses, but physical key/display behavior is not yet hardware-validated.
- No live ping was performed during development; tests mock subprocess execution.
