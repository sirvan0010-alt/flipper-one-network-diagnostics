from flipper_diag.doctor import collect_doctor_report


def test_doctor_report_is_read_only_and_versioned():
    report = collect_doctor_report()
    assert report["schema_version"] == 1
    assert report["mode"] == "read-only"
    assert report["network_traffic_generated"] is False
    assert isinstance(report["interfaces"], list)
    assert "ping" in report["tools"]
