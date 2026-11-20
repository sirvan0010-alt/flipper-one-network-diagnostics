"""Fail-closed authorization policy for future active network operations."""

from dataclasses import dataclass
import ipaddress


class ActiveOperationBlocked(PermissionError):
    """Raised when an active operation lacks explicit bounded authorization."""


MAX_AUTHORIZED_TARGETS = 256


@dataclass(frozen=True, slots=True)
class ActiveAuthorization:
    """Explicit authorization for targets inside one IP network scope.

    The scope must be an IP address or CIDR network. Targets must be literal
    IP addresses inside that network; hostnames are intentionally not accepted.
    """

    purpose: str
    scope: str
    targets: tuple[str, ...]
    confirmed: bool


def require_active_allowed(
    *,
    safe_mode: bool = True,
    authorization: ActiveAuthorization | None = None,
) -> None:
    """Fail closed unless an operator confirms a bounded IP-only scope."""
    if safe_mode:
        raise ActiveOperationBlocked("Safe Mode is enabled; active operation blocked.")
    if authorization is None:
        raise ActiveOperationBlocked("Explicit authorization is required.")
    if authorization.confirmed is not True:
        raise ActiveOperationBlocked("The operator has not confirmed this test.")
    if not authorization.purpose.strip():
        raise ActiveOperationBlocked("A non-empty test purpose must be specified.")
    if not authorization.scope.strip():
        raise ActiveOperationBlocked("An explicit IP network scope must be specified.")
    if not authorization.targets:
        raise ActiveOperationBlocked("At least one explicit target is required.")
    if len(authorization.targets) > MAX_AUTHORIZED_TARGETS:
        raise ActiveOperationBlocked(
            f"At most {MAX_AUTHORIZED_TARGETS} targets may be authorized per operation."
        )

    try:
        network = ipaddress.ip_network(authorization.scope, strict=False)
    except ValueError as exc:
        raise ActiveOperationBlocked("Scope must be a valid IP address or CIDR network.") from exc

    normalized_targets = set()
    for target in authorization.targets:
        try:
            address = ipaddress.ip_address(target)
        except ValueError as exc:
            raise ActiveOperationBlocked(
                "Targets must be literal IPv4 or IPv6 addresses; hostnames are not accepted."
            ) from exc
        if address not in network:
            raise ActiveOperationBlocked(
                f"Target {address} is outside the explicitly authorized scope {network}."
            )
        normalized_targets.add(address)

    if len(normalized_targets) != len(authorization.targets):
        raise ActiveOperationBlocked("Duplicate targets are not allowed.")
