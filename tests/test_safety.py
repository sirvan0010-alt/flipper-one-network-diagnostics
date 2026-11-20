import pytest

from flipper_diag.safety import (
    ActiveAuthorization,
    ActiveOperationBlocked,
    require_active_allowed,
)


def test_safe_mode_blocks_even_with_authorization():
    auth = ActiveAuthorization(
        "connectivity check", "192.0.2.0/24", ("192.0.2.1",), True
    )
    with pytest.raises(ActiveOperationBlocked, match="Safe Mode"):
        require_active_allowed(safe_mode=True, authorization=auth)


def test_active_operation_requires_authorization_by_default():
    with pytest.raises(ActiveOperationBlocked, match="authorization"):
        require_active_allowed(safe_mode=False)


def test_unconfirmed_operation_is_blocked():
    auth = ActiveAuthorization("scan", "192.0.2.0/24", ("192.0.2.1",), False)
    with pytest.raises(ActiveOperationBlocked, match="not confirmed"):
        require_active_allowed(safe_mode=False, authorization=auth)


def test_bounded_confirmed_authorization_is_accepted():
    auth = ActiveAuthorization(
        "connectivity check", "192.0.2.0/24", ("192.0.2.1", "192.0.2.2"), True
    )
    require_active_allowed(safe_mode=False, authorization=auth)


def test_target_outside_scope_is_blocked():
    auth = ActiveAuthorization("scan", "192.0.2.0/24", ("198.51.100.10",), True)
    with pytest.raises(ActiveOperationBlocked, match="outside"):
        require_active_allowed(safe_mode=False, authorization=auth)


def test_hostname_target_is_blocked():
    auth = ActiveAuthorization("scan", "192.0.2.0/24", ("example.com",), True)
    with pytest.raises(ActiveOperationBlocked, match="literal"):
        require_active_allowed(safe_mode=False, authorization=auth)


def test_invalid_scope_is_blocked():
    auth = ActiveAuthorization("scan", "office VLAN", ("192.0.2.1",), True)
    with pytest.raises(ActiveOperationBlocked, match="CIDR"):
        require_active_allowed(safe_mode=False, authorization=auth)


def test_duplicate_targets_are_blocked():
    auth = ActiveAuthorization(
        "scan", "192.0.2.0/24", ("192.0.2.1", "192.0.2.1"), True
    )
    with pytest.raises(ActiveOperationBlocked, match="Duplicate"):
        require_active_allowed(safe_mode=False, authorization=auth)


@pytest.mark.parametrize("safe_mode", [None, 0, "false"])
def test_non_boolean_false_safe_mode_value_is_still_blocked(safe_mode):
    auth = ActiveAuthorization("connectivity", "192.0.2.0/24", ("192.0.2.1",), True)
    with pytest.raises(ActiveOperationBlocked, match="Safe Mode"):
        require_active_allowed(safe_mode=safe_mode, authorization=auth)


@pytest.mark.parametrize("target", [None, 1234, b"192.0.2.1", ""])
def test_non_string_or_empty_targets_are_blocked(target):
    auth = ActiveAuthorization("connectivity", "192.0.2.0/24", (target,), True)
    with pytest.raises(ActiveOperationBlocked, match="Targets must be"):
        require_active_allowed(safe_mode=False, authorization=auth)


def test_active_operation_is_bound_to_one_explicitly_authorized_target():
    auth = ActiveAuthorization(
        "connectivity check",
        "192.0.2.0/24",
        ("192.0.2.1", "192.0.2.2"),
        True,
    )
    require_active_allowed(
        safe_mode=False, authorization=auth, target="192.0.2.1"
    )
    with pytest.raises(ActiveOperationBlocked, match="not included"):
        require_active_allowed(
            safe_mode=False, authorization=auth, target="192.0.2.3"
        )


@pytest.mark.parametrize("target", [None, "example.com", 1234])
def test_active_operation_rejects_non_literal_requested_target(target):
    auth = ActiveAuthorization("connectivity check", "192.0.2.0/24", ("192.0.2.1",), True)
    with pytest.raises(ActiveOperationBlocked, match="literal IP"):
        require_active_allowed(
            safe_mode=False, authorization=auth, target=target
        )
