from flipper_diag import linux_dns


def test_parse_resolv_conf_directives_and_comments():
    parsed = linux_dns.parse_resolv_conf(
        """
        # generated file
        nameserver 192.0.2.53
        nameserver 2001:db8::53 ; secondary
        search example.test lab.example.test
        options timeout:2 attempts:3
        """
    )
    assert parsed == {
        "nameservers": ["192.0.2.53", "2001:db8::53"],
        "search": ["example.test", "lab.example.test"],
        "options": ["timeout:2", "attempts:3"],
    }


def test_collector_detects_loopback_stub_without_querying_dns(tmp_path):
    resolver = tmp_path / "resolv.conf"
    resolver.write_text(
        "nameserver 127.0.0.53\nsearch lan.example\n", encoding="utf-8"
    )
    result = linux_dns.collect_dns_config(resolver)
    assert result.status == "ok"
    assert result.data["local_stub"] is True
    assert result.data["nameservers"] == ["127.0.0.53"]
    assert any("upstream DNS" in item for item in result.limitations)


def test_collector_reports_missing_and_invalid_nameservers(tmp_path):
    resolver = tmp_path / "resolv.conf"
    resolver.write_text("nameserver not-an-ip\n", encoding="utf-8")
    result = linux_dns.collect_dns_config(resolver)
    assert result.status == "warning"
    assert result.data["invalid_nameservers"] == ["not-an-ip"]
    assert {item.code for item in result.findings} == {
        "DNS-CONFIG-INVALID-NAMESERVER",
        "DNS-CONFIG-MISSING",
    }


def test_collector_handles_missing_file(tmp_path):
    result = linux_dns.collect_dns_config(tmp_path / "missing")
    assert result.status == "error"
    assert result.findings[0].code == "DNS-CONFIG-UNAVAILABLE"


def test_last_search_or_domain_directive_replaces_previous_list():
    parsed = linux_dns.parse_resolv_conf(
        "search first.example second.example\ndomain final.example\n"
    )
    assert parsed["search"] == ["final.example"]
