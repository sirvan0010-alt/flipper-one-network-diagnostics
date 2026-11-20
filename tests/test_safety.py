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
