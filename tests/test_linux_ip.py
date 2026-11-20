import json
from pathlib import Path

import pytest

from flipper_diag.linux_ip import parse_ip_address_json


FIXTURE = Path(__file__).parent / "fixtures" / "ip-address.json"


def test_parse_iproute2_interface_fixture():
    interfaces = parse_ip_address_json(FIXTURE.read_text(encoding="utf-8"))

    assert len(interfaces) == 2
    assert interfaces[1]["name"] == "eth0"
    assert interfaces[1]["operstate"] == "UP"
    assert interfaces[1]["mtu"] == 1500
    assert interfaces[1]["addresses"][0]["local"] == "192.0.2.10"
    assert interfaces[1]["addresses"][0]["prefixlen"] == 24


def test_parser_rejects_invalid_json():
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_ip_address_json("{broken")


def test_parser_rejects_wrong_root_type():
    with pytest.raises(ValueError, match="root must be an array"):
        parse_ip_address_json(json.dumps({"ifname": "eth0"}))


def test_parser_rejects_interface_without_name():
    with pytest.raises(ValueError, match="ifname"):
        parse_ip_address_json(json.dumps([{"ifindex": 2}]))
