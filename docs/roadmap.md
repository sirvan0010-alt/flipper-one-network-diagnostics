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
