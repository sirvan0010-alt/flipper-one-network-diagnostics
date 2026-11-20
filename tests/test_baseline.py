import pytest

from flipper_diag.baseline import compare_device_inventory


def test_inventory_comparison_finds_new_missing_and_changed_devices():
    baseline = [
        {"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.10"]},
        {"mac_address": "02:00:00:00:00:02", "addresses": ["192.0.2.20"]},
    ]
    current = [
        {"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.11"]},
        {"mac_address": "02:00:00:00:00:03", "addresses": ["192.0.2.30"]},
    ]

    findings = compare_device_inventory(baseline, current)
    codes = [finding.code for finding in findings]

    assert codes == [
        "INVENTORY-NEW-DEVICE",
        "INVENTORY-MISSING-DEVICE",
        "INVENTORY-ADDRESS-CHANGED",
    ]


def test_inventory_comparison_detects_duplicate_ip():
    current = [
        {"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.10"]},
        {"mac_address": "02:00:00:00:00:02", "addresses": ["192.0.2.10"]},
    ]

    findings = compare_device_inventory([], current)

    duplicate = [finding for finding in findings if finding.code == "NETWORK-DUPLICATE-IP"]
    assert len(duplicate) == 1
    assert duplicate[0].severity == "warning"


def test_inventory_comparison_normalizes_ip_and_mac():
    baseline = [{"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.1"]}]
    current = [{"mac_address": "02:00:00:00:00:01", "addresses": ["192.0.2.1/32"]}]

    findings = compare_device_inventory(baseline, current)

    assert findings == []


def test_inventory_rejects_missing_identity_and_invalid_ip():
    with pytest.raises(ValueError, match="MAC address"):
        compare_device_inventory([], [{"addresses": ["192.0.2.1"]}])
    with pytest.raises(ValueError, match="invalid IP address"):
        compare_device_inventory([], [{"mac_address": "aa:bb", "addresses": ["not-an-ip"]}])


def test_inventory_rejects_duplicate_mac():
    devices = [
        {"mac_address": "aa:bb", "addresses": []},
        {"mac_address": "AA:BB", "addresses": []},
    ]

    with pytest.raises(ValueError, match="duplicate MAC"):
        compare_device_inventory([], devices)
