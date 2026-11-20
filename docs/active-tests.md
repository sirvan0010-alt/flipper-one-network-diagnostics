# Active test authorization

Status: a single-target ICMP collector is implemented for development/CLI testing. It has not been run against a live target and is not exposed in the Flipper app menu.

## Safe Mode

- Safe Mode is the default and blocks active operations.
- The on-device app currently keeps Safe Mode ON and exposes no control that disables it.
- The CLI ping command requires an explicit --confirm-active flag, a literal target IP, and a CIDR/IP scope.
- The target must be inside the scope and must also be present in the explicit authorization target list.
- The authorization is per invocation; it is not saved as a persistent permission.
- The CLI sends only one bounded ICMP test to one IP address: 1–5 requests, 1–5 seconds per request, no automatic retries, no hostname resolution and no subnet scanning.

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

## Current limitations

- ICMP echo only; it does not prove DNS, TCP service or Internet reachability.
- Some hosts/firewalls intentionally block ICMP.
- The parser supports the tested iputils and BusyBox summary formats; target output must be verified.
- The Flipper app does not yet expose active tests. A separate on-device confirmation screen and audit record are required before that changes.
- No live ping was performed during development; tests mock subprocess execution.
