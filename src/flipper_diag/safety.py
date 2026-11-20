"""Safety policy for operations that generate network traffic."""

from dataclasses import dataclass


class ActiveOperationBlocked(PermissionError):
    """Raised when an active operation lacks explicit authorization."""


@dataclass(frozen=True, slots=True)
class ActiveAuthorization:
    """Explicit operator authorization for one bounded active test."""

    purpose: str
    scope: str
    targets: tuple[str, ...]
    confirmed: bool


def require_active_allowed(
    *,
    safe_mode: bool,
    authorization: ActiveAuthorization | None,
) -> None:
    """Fail closed unless safe mode is off and a bounded test was confirmed."""
    if safe_mode:
        raise ActiveOperationBlocked("Safe Mode is enabled; active operation blocked.")
    if authorization is None:
        raise ActiveOperationBlocked("Explicit authorization is required.")
    if not authorization.confirmed:
        raise ActiveOperationBlocked("The operator has not confirmed this test.")
    if not authorization.purpose.strip() or not authorization.scope.strip():
        raise ActiveOperationBlocked("Purpose and authorized scope must be specified.")
    if not authorization.targets or any(not target.strip() for target in authorization.targets):
        raise ActiveOperationBlocked("At least one explicit, non-empty target is required.")
