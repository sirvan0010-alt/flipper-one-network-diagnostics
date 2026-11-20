# Roadmap

Podrobný backlog F-01 až F-57 a závazné podmínky jsou v kořenovém [AGENTS.md](../AGENTS.md). Podrobné UX, závislosti, bezpečnost a akceptační kritéria jsou v [functional specification](functional-specification.md). Tento soubor shrnuje milníky.

| Milník | Cíl | Výstup / exit criteria |
|---|---|---|
| M0 – Příprava | Projít oficiální dokumentaci a připravit vývojovou platformu | Zaznamenané verze zdrojů, vybraná deska a ověřený seznam periferií |
| M1 – Systém | Instalovat OS a ověřit základní rozhraní | Záznam `uname -a`, `iw list`, `ethtool`, síťových rozhraní a logů |
| M2 – Ověření rizik | Ověřit monitor mode, pásma, radiotap, injection, STA+AP a možnosti PHY | Vyplněné `docs/verification.md`; žádný předpoklad nesmí být prezentován jako ověřený |
| M3 – Jádro | Navrhnout kolektory, SQLite a jednotný JSON kontrakt | Architektura, schéma DB, testy parserů a safe-mode policy |
| M4 – Drátové MVP | Discovery, baseline, profily AutoTest, Ping/TCP, capture, iperf3 a reporty | Funkční testy na cílové platformě a lokální export |
| M5 – Wi-Fi/Bluetooth | Wi-Fi testy, mapa kanálů, roaming, Locate, capture, BLE | Ověřené limity rádia, regulační doména a druhý adaptér podle potřeby |
| M6 – Bezpečnost a dashboard | Problémový engine, Nmap, monitoring, reporty a dashboard | Aktivní testy chráněné safe mode a lokální přístup zabezpečený |
| M7 – Volitelné | Reflector/LANBERT, Proxmark5, WiCAN PRO, vlastní HW | Samostatně ověřené prototypy; nesmí blokovat MVP |

## Pravidlo postupu

Milník se nepovažuje za dokončený jen proto, že existuje kód. Musí mít reprodukovatelné testy, zdokumentovaná omezení a důkaz běhu na cílové platformě.

## Aktuální stav implementace (2026-11-20; aktualizováno po CI běhu)

Detailní rozhodnutí pro funkce F-01 až F-57 je v [feature matrix](feature-matrix.md); jejich funkční kontrakty jsou v [functional specification](functional-specification.md). Upstream změny se evidují v [upstream watch](upstream-watch.md).

CI evidence (2026-11-20): [Python checks run 44771202433](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202433) passed 137 tests on Python 3.10–3.13, Ruff, app packaging and artifact upload; native Ubuntu ARM64 passed clean offline wheel installation, SQLite/CLI smoke tests, isolated core imports and packaged `.fap.py` startup with a test FlipCTL stub. The same run's Debian Trixie ARM64 container job passed `python3`, SQLite 3.46.1, schema initialization and bundled-core imports. Documentation validation passed. [Security run 44771202422](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202422) passed pip-audit, high-severity Bandit and compilation. [CodeQL run 44771202629](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202629) completed successfully for Python and GitHub Actions. This remains CI/userspace validation; no Flipper One hardware or live network test has been performed.

Tento stav je softwarové ověření na GitHub CI a běžném Linuxu, nikoli potvrzení běhu na Flipper One.

| Oblast | Stav | Důkaz / omezení |
|---|---|---|
| Přenosný Python balíček a CLI | Implementováno | Instalace přes `pip install -e .`; běh v CI |
| Read-only doctor | Implementováno | Inventura OS, rozhraní a dostupných nástrojů; negeneruje síťové pakety |
| FlipCTL Python app | Prototyp implementován | `apps/network-diagnostics.fap.py` + package builder; cílový běh na Flipperu zatím neověřen |
| Výsledkový JSON kontrakt | Implementováno v1 | `DiagnosticResult` a `Finding` |
| Safe Mode základ | Implementováno jako policy API | Zatím není napojen na aktivní síťové kolektory |
| SQLite výsledky a historie | Implementováno v1 | Migrace schématu, atomické ukládání výsledků, `history`; CLI end-to-end test ukládá výsledek a načte jej znovu přes historii |
| SQLite inventory baseline | Implementováno v2 | Pojmenované baseline, ukládání/načítání |
| Linux interface inventory | Implementováno | Read-only `ip -j address show`; sysfs classification prevents Wi-Fi being treated as wired Ethernet; parser and mock tests |
| Ethernet link status | Implementováno | Read-only `ethtool <interface>` with `/sys/class/net` fallback; parser and sysfs mock tests; ethtool may be absent from rootfs |
| IPv4/IPv6 default-route inventory | Implementováno | Read-only `ip -j route show default` a `ip -6 -j route show default`; mock testy |
| Local DNS resolver configuration | Implementováno | Read-only parser `/etc/resolv.conf`; žádné DNS dotazy; mock testy |
| Local readiness check | Implementováno | Aggregates interface, Ethernet link, default route and DNS configuration; no active probes; unit/UI/CLI tests |
| Passive neighbor inventory | Implementováno | Read-only IPv4/IPv6 kernel neighbor cache; no discovery packets; CLI and on-device Known devices screen |
| Evidence-bounded problem engine | Částečně implementováno | Local Check reports observations and cautious likely causes; root cause is never marked confirmed |
| Inventory diff | Implementováno | Nová/chybějící zařízení, změna IP, duplicitní IP; vstupní pozorování musí dodat collector/import |
| DHCP/DNS/gateway AutoTest | Částečně připraveno | Local Check combines local config; one-target ICMP and single-port TCP commands exist in CLI and behind on-device confirmation; DHCP lease/offer, DNS resolution and full wired AutoTest UI are not yet implemented |
| LLDP/CDP/VLAN a SNMP | Nezahájeno | Je nutné nejprve ověřit nativní Flipper discovery a dostupné nástroje |
| FlipCTL integrace | Python app prototyp | `.fap.py` kontrakt dokumentovaný v `flipctl-slint`; statické/mock testy a balení v CI, cílový běh neověřen |
| Flipper One runtime/hardware | Neověřeno | Zařízení zatím není k dispozici; app API je ověřené proti zdrojům upstream, nikoli na fyzickém zařízení |
| WiCAN PRO | Fyzický adaptér uživatele; Flipper integrace neověřena | Přesná verze firmware, stable 4.x stream protokol a Wi-Fi/BLE/USB konektivita se musí ověřit. Žádné CAN TX. Detail v [wican-pro-integration.md](wican-pro-integration.md) |
| Linux ARM64 packaging/runtime | Ověřeno v GitHub Actions | Run [44771202433](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202433): nativní `aarch64`, 137 testů, Ruff, `py3-none-any` wheel, čistá offline instalace bez `--no-deps`, SQLite/CLI, sestavení FlipCTL balíčku, import všech zabalených modulů bez site-packages a spuštění `.fap.py` se simulovaným FlipCTL modulem. Navíc Debian Trixie ARM64 kontejner ověřil `python3`, SQLite 3.46.1, schema initialization a bundle imports. Ani to není kompletní Flipper OS image nebo fyzické zařízení. |
| Markdown dokumentace | Ověřeno v GitHub Actions | Run [44771202433](https://github.com/sirvan0010-alt/flipper-one-network-diagnostics/actions/runs/44771202433): interní Markdown cesty, obrázky a fragmenty nadpisů; kontrola běží offline a ignoruje fenced code blocks. Externí URL se nekontrolují. |

### Co je potřeba před označením M3 za dokončený

- CI musí projít celou podporovanou Python maticí včetně ARM64 jobu.
- Doplnit integrační testy databáze, migrací a CLI.
- Na cílovém zařízení ověřit Python Runtime, import balíčku vedle `.fap.py` skriptu, zobrazení menu, mapování kláves a zápis SQLite.
- Připravit instalaci balíčku bez vývojových závislostí.
- Po ARM64 CI ověřit runtime a spotřebu na podporované ARM64 Linux desce, později na Flipper One.
- Uzavřít rozhraní pro FlipCTL až podle skutečného upstream API; neblokovat tím přenosné jádro.
