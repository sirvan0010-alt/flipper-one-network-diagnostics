# Roadmap

Podrobný backlog F-01 až F-45 a závazné podmínky jsou v kořenovém [AGENTS.md](../AGENTS.md). Tento soubor shrnuje milníky.

| Milník | Cíl | Výstup / exit criteria |
|---|---|---|
| M0 – Příprava | Projít oficiální dokumentaci a připravit vývojovou platformu | Zaznamenané verze zdrojů, vybraná deska a ověřený seznam periferií |
| M1 – Systém | Instalovat OS a ověřit základní rozhraní | Záznam `uname -a`, `iw list`, `ethtool`, síťových rozhraní a logů |
| M2 – Ověření rizik | Ověřit monitor mode, pásma, radiotap, injection, STA+AP a možnosti PHY | Vyplněné `docs/verification.md`; žádný předpoklad nesmí být prezentován jako ověřený |
| M3 – Jádro | Navrhnout kolektory, SQLite a jednotný JSON kontrakt | Architektura, schéma DB, testy parserů a safe-mode policy |
| M4 – Drátové MVP | Discovery, baseline, profily AutoTest, Ping/TCP, capture, iperf3 a reporty | Funkční testy na cílové platformě a lokální export |
| M5 – Wi-Fi/Bluetooth | Wi-Fi testy, mapa kanálů, roaming, Locate, capture, BLE | Ověřené limity rádia, regulační doména a druhý adaptér podle potřeby |
| M6 – Bezpečnost a dashboard | Problémový engine, Nmap, monitoring, reporty a dashboard | Aktivní testy chráněné safe mode a lokální přístup zabezpečený |
| M7 – Volitelné | Reflector/LANBERT, Proxmark5, vlastní HW | Samostatně ověřené prototypy; nesmí blokovat MVP |

## Pravidlo postupu

Milník se nepovažuje za dokončený jen proto, že existuje kód. Musí mít reprodukovatelné testy, zdokumentovaná omezení a důkaz běhu na cílové platformě.

## Aktuální stav implementace (2026-11-20; aktualizováno po CI běhu)

Detailní rozhodnutí pro všech 45 funkcí F-01 až F-45 je v [feature matrix](feature-matrix.md); upstream změny se evidují v [upstream watch](upstream-watch.md).

Tento stav je softwarové ověření na GitHub CI a běžném Linuxu, nikoli potvrzení běhu na Flipper One.

| Oblast | Stav | Důkaz / omezení |
|---|---|---|
| Přenosný Python balíček a CLI | Implementováno | Instalace přes `pip install -e .`; běh v CI |
| Read-only doctor | Implementováno | Inventura OS, rozhraní a dostupných nástrojů; negeneruje síťové pakety |
| FlipCTL Python app | Prototyp implementován | `apps/network-diagnostics.fap.py` + package builder; cílový běh na Flipperu zatím neověřen |
| Výsledkový JSON kontrakt | Implementováno v1 | `DiagnosticResult` a `Finding` |
| Safe Mode základ | Implementováno jako policy API | Zatím není napojen na aktivní síťové kolektory |
| SQLite výsledky a historie | Implementováno v1 | Migrace schématu, ukládání výsledků, `history` |
| SQLite inventory baseline | Implementováno v2 | Pojmenované baseline, ukládání/načítání |
| Linux interface inventory | Implementováno | Read-only `ip -j address show`; ověřeno parserem a mock testy |
| Ethernet link status | Implementováno | Read-only `ethtool <interface>`; ověřeno parserem a mock testy; nástroj nemusí být v rootfs |
| IPv4/IPv6 default-route inventory | Implementováno | Read-only `ip -j route show default` a `ip -6 -j route show default`; mock testy |
| Local DNS resolver configuration | Implementováno | Read-only parser `/etc/resolv.conf`; žádné DNS dotazy; mock testy |
| Local readiness check | Implementováno | Aggregates interface, Ethernet link, default route and DNS configuration; no active probes; unit/UI/CLI tests |
| Inventory diff | Implementováno | Nová/chybějící zařízení, změna IP, duplicitní IP; vstupní pozorování musí dodat collector/import |
| DHCP/DNS/gateway AutoTest | Částečně připraveno | Local Check combines local config; DHCP lease/offer, DNS resolution and gateway reachability are not yet tested |
| LLDP/CDP/VLAN a SNMP | Nezahájeno | Je nutné nejprve ověřit nativní Flipper discovery a dostupné nástroje |
| FlipCTL integrace | Python app prototyp | `.fap.py` kontrakt dokumentovaný v `flipctl-slint`; statické/mock testy a balení v CI, cílový běh neověřen |
| Flipper One runtime/hardware | Neověřeno | Zařízení zatím není k dispozici; app API je ověřené proti zdrojům upstream, nikoli na fyzickém zařízení |

### Co je potřeba před označením M3 za dokončený

- CI musí projít celou podporovanou Python maticí.
- Doplnit integrační testy databáze, migrací a CLI.
- Na cílovém zařízení ověřit Python Runtime, import balíčku vedle `.fap.py` skriptu, zobrazení menu, mapování kláves a zápis SQLite.
- Připravit instalaci balíčku bez vývojových závislostí.
- Ověřit runtime a spotřebu na podporované ARM64 Linux desce, později na Flipper One.
- Uzavřít rozhraní pro FlipCTL až podle skutečného upstream API; neblokovat tím přenosné jádro.
