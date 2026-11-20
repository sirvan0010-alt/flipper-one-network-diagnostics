import enum
import sys
import types
from pathlib import Path

from flipper_diag.models import DiagnosticResult


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "network-diagnostics.fap.py"


class FakeKey(enum.Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    OK = "ok"
    BACK = "back"
    ESCAPE = "escape"
    VIEW = "view"
    POWER = "power"
    EDIT = "edit"
    RUN = "run"
    PTT = "ptt"


class FakeView:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.selected = 0
        self.handler = None
        self.shown = False
        self.ran = False

    def on_key(self, handler):
        self.handler = handler
        return handler

    def show(self):
        self.shown = True

    def run(self, *args, **kwargs):
        self.ran = True

    def redraw(self):
        return None


def fake_flipctl():
    module = types.ModuleType("flipctl")
    module.Key = FakeKey
    module.Menu = lambda items, **kwargs: FakeView(items=items, **kwargs)
    module.Detail = lambda rows, **kwargs: FakeView(rows=rows, **kwargs)
    module.Log = lambda lines, **kwargs: FakeView(lines=lines, **kwargs)
    module.item = lambda label, **kwargs: {"label": label, **kwargs}
    module.pair = lambda label, value, **kwargs: {
        "kind": "pair", "label": label, "value": value, **kwargs
    }
    module.heading = lambda label, value="": {
        "kind": "heading", "label": label, "value": value
    }
    module.rule = lambda: {"kind": "rule"}
    module.text = lambda value, **kwargs: {"kind": "text", "value": value, **kwargs}
    module.wrap = lambda value: [value]
    return module


def load_app(monkeypatch):
    fake = fake_flipctl()
    monkeypatch.setitem(sys.modules, "flipctl", fake)
    namespace = {"__name__": "network_diagnostics_app", "__file__": str(APP)}
    source = APP.read_text(encoding="utf-8")
    exec(compile(source, str(APP), "exec"), namespace)
    return namespace


def test_panel_menu_and_ethernet_flow_use_shared_core(monkeypatch):
    namespace = load_app(monkeypatch)
    interfaces = [
        {
            "name": "end0",
            "link_type": "ether",
            "wireless": False,
            "mac_address": "02:00:00:00:00:01",
            "operstate": "UP",
            "mtu": 1500,
            "addresses": [{"family": "inet", "local": "192.0.2.10", "prefixlen": 24}],
        }
    ]
    monkeypatch.setitem(
        namespace,
        "collect_ip_interfaces",
        lambda: DiagnosticResult(
            collector="linux.ip_address",
            status="ok",
            data={"interfaces": interfaces, "count": 1},
        ),
    )
    monkeypatch.setitem(
        namespace,
        "collect_link_status",
        lambda interface: DiagnosticResult(
            collector="linux.ethtool",
            status="ok",
            interface=interface,
            data={
                "link_detected": True,
                "speed_mbps": 1000,
                "duplex": "full",
                "auto_negotiation": True,
            },
        ),
    )
    monkeypatch.setitem(namespace, "save_result", lambda *args: "12345678-abcd")
    namespace["main"]()

    menu = namespace["main_menu"]
    assert menu.ran is True
    assert [item["label"] for item in menu.kwargs["items"]()] == [
        "Interfaces", "Ethernet link", "Local Check", "Ping wired gateway",
        "TCP gateway port", "Default route", "DNS config", "History", "Safe Mode", "About"
    ]

    menu.selected = 0
    assert menu.handler(FakeKey.OK) is True
    detail = namespace["detail"]
    assert detail.shown is True
    assert any(row.get("label") == "end0" for row in detail.kwargs["rows"]())

    menu.selected = 1
    assert menu.handler(FakeKey.OK) is True
    link_menu = namespace["link_menu"]
    assert [item["label"] for item in link_menu.kwargs["items"]()] == ["end0"]
    assert link_menu.handler(FakeKey.OK) is True
    rows = detail.kwargs["rows"]()
    assert any(row.get("label") == "Speed" and row.get("value") == "1000 Mb/s" for row in rows)



def test_route_and_dns_screens_use_read_only_collectors(monkeypatch):
    namespace = load_app(monkeypatch)
    monkeypatch.setitem(
        namespace,
        "collect_ip_interfaces",
        lambda: DiagnosticResult(
            collector="linux.ip_address", status="ok", data={"interfaces": [], "count": 0}
        ),
    )
    monkeypatch.setitem(namespace, "save_result", lambda *args: "12345678-abcd")
    monkeypatch.setitem(
        namespace,
        "collect_default_routes",
        lambda: DiagnosticResult(
            collector="linux.default_routes",
            status="ok",
            data={
                "routes": [
                    {
                        "family": "inet",
                        "device": "end0",
                        "gateway": "192.0.2.1",
                        "metric": 100,
                        "protocol": "dhcp",
                    }
                ]
            },
        ),
    )
    monkeypatch.setitem(
        namespace,
        "collect_dns_config",
        lambda: DiagnosticResult(
            collector="linux.resolver_config",
            status="ok",
            data={
                "nameservers": ["192.0.2.53"],
                "search_domains": ["lan.example"],
                "local_stub": False,
            },
        ),
    )
    namespace["main"]()
    menu = namespace["main_menu"]
    detail = namespace["detail"]

    menu.selected = 5
    assert menu.handler(FakeKey.OK) is True
    route_rows = detail.kwargs["rows"]()
    assert any(row.get("label") == "Gateway" and row.get("value") == "192.0.2.1"
               for row in route_rows)

    menu.selected = 6
    assert menu.handler(FakeKey.OK) is True
    dns_rows = detail.kwargs["rows"]()
    assert any(row.get("label") == "DNS 1" and row.get("value") == "192.0.2.53"
               for row in dns_rows)


def test_local_check_panel_is_labelled_as_non_active(monkeypatch):
    namespace = load_app(monkeypatch)
    monkeypatch.setitem(
        namespace,
        "collect_ip_interfaces",
        lambda: DiagnosticResult(
            collector="linux.ip_address", status="ok", data={"interfaces": [], "count": 0}
        ),
    )
    monkeypatch.setitem(namespace, "save_result", lambda *args: "12345678-abcd")
    monkeypatch.setitem(
        namespace,
        "collect_local_check",
        lambda: DiagnosticResult(
            collector="network.local_check",
            status="warning",
            interface="end0",
            data={
                "active_probes": False,
                "assessment": {
                    "summary": "Local configuration needs attention.",
                    "likely_causes": [
                        {
                            "title": "Possible address configuration issue",
                            "confidence": "low",
                            "detail": "The interface has no address.",
                            "recommendation": "Check DHCP or static settings.",
                        }
                    ],
                },
                "component_status": {
                    "interfaces": "ok",
                    "link": "ok",
                    "routes": "warning",
                    "dns": "ok",
                },
            },
        ),
    )
    namespace["main"]()
    menu = namespace["main_menu"]
    menu.selected = 2
    assert menu.handler(FakeKey.OK) is True
    rows = namespace["detail"].kwargs["rows"]()
    assert any(row.get("label") == "Link" and row.get("value") == "ok" for row in rows)
    assert any(
        "no DHCP, DNS or gateway probes" in row.get("value", "")
        for row in rows
    )
    assert any(
        "Local configuration needs attention." in row.get("value", "")
        for row in rows
    )


def _wired_test_interfaces():
    return [
        {
            "name": "end0",
            "link_type": "ether",
            "wireless": False,
            "operstate": "UP",
            "addresses": [{"family": "inet", "local": "192.0.2.10", "prefixlen": 24}],
        }
    ]


def _wired_default_route():
    return DiagnosticResult(
        collector="linux.default_routes",
        status="ok",
        data={
            "routes": [
                {
                    "family": "inet",
                    "device": "end0",
                    "gateway": "192.0.2.1",
                    "metric": 100,
                }
            ]
        },
    )


def test_ping_gateway_requires_on_device_confirmation(monkeypatch):
    namespace = load_app(monkeypatch)
    calls = []
    monkeypatch.setitem(
        namespace,
        "collect_ip_interfaces",
        lambda: DiagnosticResult(
            collector="linux.ip_address",
            status="ok",
            data={"interfaces": _wired_test_interfaces(), "count": 1},
        ),
    )
    monkeypatch.setitem(namespace, "collect_default_routes", _wired_default_route)
    monkeypatch.setitem(namespace, "save_result", lambda *args: "12345678-abcd")

    def fake_ping(target, **kwargs):
        calls.append((target, kwargs))
        return DiagnosticResult(
            collector="linux.ping",
            status="ok",
            data={"target": target, "packets_transmitted": 3, "packets_received": 3},
        )

    monkeypatch.setitem(namespace, "run_ping", fake_ping)
    namespace["main"]()
    menu = namespace["main_menu"]
    menu.selected = 3
    assert menu.handler(FakeKey.OK) is True

    confirm = namespace["confirm_detail"]
    assert confirm.shown is True
    assert calls == []
    confirm_rows = confirm.kwargs["rows"]()
    assert any(row.get("label") == "Target" and row.get("value") == "192.0.2.1"
               for row in confirm_rows)

    assert confirm.handler(FakeKey.RUN) is True
    assert len(calls) == 1
    target, kwargs = calls[0]
    assert target == "192.0.2.1"
    assert kwargs["safe_mode"] is False
    assert kwargs["authorization"].targets == ("192.0.2.1",)
    assert namespace["detail"].shown is True


def test_tcp_gateway_port_requires_confirmation_and_authorizes_one_port(monkeypatch):
    namespace = load_app(monkeypatch)
    calls = []
    monkeypatch.setitem(
        namespace,
        "collect_ip_interfaces",
        lambda: DiagnosticResult(
            collector="linux.ip_address",
            status="ok",
            data={"interfaces": _wired_test_interfaces(), "count": 1},
        ),
    )
    monkeypatch.setitem(namespace, "collect_default_routes", _wired_default_route)
    monkeypatch.setitem(namespace, "save_result", lambda *args: "12345678-abcd")

    def fake_tcp(target, port, **kwargs):
        calls.append((target, port, kwargs))
        return DiagnosticResult(
            collector="linux.tcp_connect",
            status="ok",
            data={"target": target, "port": port, "connected": True},
        )

    monkeypatch.setitem(namespace, "run_tcp_connect", fake_tcp)
    namespace["main"]()
    menu = namespace["main_menu"]
    menu.selected = 4
    assert menu.handler(FakeKey.OK) is True

    port_menu = namespace["tcp_port_menu"]
    assert [item["label"] for item in port_menu.kwargs["items"]()] == [
        "DNS", "HTTP", "HTTPS", "SSH"
    ]
    port_menu.selected = 2
    assert port_menu.handler(FakeKey.OK) is True

    confirm = namespace["confirm_detail"]
    assert confirm.shown is True
    assert calls == []
    assert confirm.handler(FakeKey.RUN) is True

    assert len(calls) == 1
    target, port, kwargs = calls[0]
    assert target == "192.0.2.1"
    assert port == 443
    assert kwargs["safe_mode"] is False
    assert kwargs["authorization"].targets == ("192.0.2.1",)
    assert kwargs["authorization"].ports == (443,)
