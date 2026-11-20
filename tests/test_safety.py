import pytest

from flipper_diag.safety import (
    ActiveAuthorization,
    ActiveOperationBlocked,
    require_active_allowed,
)


def test_safe_mode_blocks_even_with_authorization():
    auth = ActiveAuthorization("connectivity check", "lab VLAN", ("192.0.2.1",), True)
    with pytest.raises(ActiveOperationBlocked):
        require_active_allowed(safe_mode=True, authorization=auth)


def test_active_operation_requires_authorization():
    with pytest.raises(ActiveOperationBlocked):
        require_active_allowed(safe_mode=False, authorization=None)


def test_unconfirmed_operation_is_blocked():
    auth = ActiveAuthorization("scan", "lab", ("192.0.2.1",), False)
    with pytest.raises(ActiveOperationBlocked):
        require_active_allowed(safe_mode=False, authorization=auth)


def test_bounded_confirmed_authorization_is_accepted():
    auth = ActiveAuthorization("connectivity check", "owned lab VLAN", ("192.0.2.1",), True)
    require_active_allowed(safe_mode=False, authorization=auth)
