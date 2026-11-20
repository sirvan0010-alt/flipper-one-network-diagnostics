import errno
import socket

import pytest

from flipper_diag.safety import ActiveAuthorization, ActiveOperationBlocked
from flipper_diag.tcp_connect import run_tcp_connect


def _authorization(target="192.0.2.1", scope="192.0.2.0/24", ports=(443,)):
    return ActiveAuthorization(
        purpose="single-port TCP diagnostic",
        scope=scope,
        targets=(target,),
        confirmed=True,
        ports=ports,
    )


class FakeSocket:
    def __init__(self, family, kind, error_code=0):
        self.family = family
        self.kind = kind
        self.error_code = error_code
        self.timeout = None
        self.remote = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def settimeout(self, value):
        self.timeout = value

    def connect_ex(self, remote):
        self.remote = remote
        return self.error_code


def test_tcp_connect_is_blocked_by_default_safe_mode(monkeypatch):
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *args: (_ for _ in ()).throw(AssertionError("socket must not be created")),
    )
    with pytest.raises(ActiveOperationBlocked, match="Safe Mode"):
        run_tcp_connect("192.0.2.1", 443)


def test_tcp_connect_requires_authorized_port():
    authorization = _authorization(ports=(22,))
    with pytest.raises(ActiveOperationBlocked, match="port"):
        run_tcp_connect(
            "192.0.2.1",
            443,
            authorization=authorization,
            safe_mode=False,
        )


@pytest.mark.parametrize("port", [0, 65536, True, "443"])
def test_tcp_connect_rejects_invalid_ports(port):
    with pytest.raises(ValueError, match="port must be"):
        run_tcp_connect(
            "192.0.2.1",
            port,
            authorization=_authorization(),
            safe_mode=False,
        )


def test_tcp_connect_rejects_hostname_and_out_of_range_timeout():
    with pytest.raises(ValueError, match="literal IPv4 or IPv6"):
        run_tcp_connect(
            "example.com",
            443,
            authorization=_authorization(),
            safe_mode=False,
        )
    with pytest.raises(ValueError, match="timeout_seconds"):
        run_tcp_connect(
            "192.0.2.1",
            443,
            authorization=_authorization(),
            safe_mode=False,
            timeout_seconds=6,
        )


def test_authorized_tcp_connect_uses_one_socket_and_no_payload(monkeypatch):
    sockets = []

    def make_socket(family, kind):
        instance = FakeSocket(family, kind)
        sockets.append(instance)
        return instance

    monkeypatch.setattr(socket, "socket", make_socket)
    result = run_tcp_connect(
        "192.0.2.1",
        443,
        authorization=_authorization(),
        safe_mode=False,
        timeout_seconds=2,
    )

    assert result.status == "ok"
    assert result.data["connected"] is True
    assert len(sockets) == 1
    assert sockets[0].family == socket.AF_INET
    assert sockets[0].kind == socket.SOCK_STREAM
    assert sockets[0].timeout == 2
    assert sockets[0].remote == ("192.0.2.1", 443)


def test_tcp_connect_refusal_is_not_reported_as_host_down(monkeypatch):
    monkeypatch.setattr(
        socket,
        "socket",
        lambda family, kind: FakeSocket(family, kind, errno.ECONNREFUSED),
    )
    result = run_tcp_connect(
        "192.0.2.1",
        443,
        authorization=_authorization(),
        safe_mode=False,
    )
    assert result.status == "warning"
    assert result.findings[0].code == "TCP-PORT-REFUSED"
    assert "did not accept" in result.findings[0].detail


def test_tcp_connect_timeout_is_bounded(monkeypatch):
    monkeypatch.setattr(
        socket,
        "socket",
        lambda family, kind: FakeSocket(family, kind, errno.ETIMEDOUT),
    )
    result = run_tcp_connect(
        "192.0.2.1",
        443,
        authorization=_authorization(),
        safe_mode=False,
        timeout_seconds=2,
    )
    assert result.status == "warning"
    assert result.findings[0].code == "TCP-CONNECT-TIMEOUT"


def test_ipv6_tcp_connect_uses_ipv6_socket_address(monkeypatch):
    sockets = []

    def make_socket(family, kind):
        instance = FakeSocket(family, kind)
        sockets.append(instance)
        return instance

    monkeypatch.setattr(socket, "socket", make_socket)
    authorization = _authorization(
        target="2001:db8::1",
        scope="2001:db8::/64",
        ports=(443,),
    )
    result = run_tcp_connect(
        "2001:db8::1",
        443,
        authorization=authorization,
        safe_mode=False,
    )

    assert result.status == "ok"
    assert sockets[0].family == socket.AF_INET6
    assert sockets[0].remote == ("2001:db8::1", 443, 0, 0)
