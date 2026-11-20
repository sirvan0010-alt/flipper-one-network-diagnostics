# Flipper One Network Diagnostics

Open-source lokální diagnostická sada pro síťové funkce platformy Flipper One. Cílem je převzít softwarově realizovatelné diagnostické postupy známé z rodin NetAlly LinkRunner, EtherScope, AirCheck a CyberScope, nikoli kopírovat jejich proprietární rozhraní nebo cloudové služby.

> **Stav:** plánování a ověřování hardwarových předpokladů. Flipper One / vývojová platforma a konkrétní periferie musí být před implementací ověřeny na reálném hardwaru.

## Závazný dokument pro AI a vývojáře

Před jakoukoli změnou kódu nebo technickým tvrzením si přečti celý [AGENTS.md](AGENTS.md). Obsahuje pravidla ověřování, bezpečnostní omezení, matici 45 funkcí F-01 až F-45 a milníky M0–M7.

## Cíle projektu

- Lokální provoz bez cloudových závislostí.
- Pasivní diagnostika jako výchozí režim.
- Aktivní testy pouze v sítích, kde má uživatel oprávnění testovat.
- Jednotné výstupy kolektorů, ukládání do SQLite a export HTML/PDF/CSV.
- Jasné oddělení funkcí proveditelných softwarem od funkcí vyžadujících vlastní elektroniku.

## Struktura

- `AGENTS.md` – závazné pokyny, funkční matice a plán.
- `docs/verification.md` – evidence hardwarových a softwarových ověření.
- `docs/architecture.md` – návrh architektury a otevřená rozhodnutí.
- `docs/roadmap.md` – přehled milníků.

Adresáře `core/`, `tests/` a `reports/` se založí při zahájení implementace.

## Milníky

| Milník | Obsah |
|---|---|
| M0 | Příprava a dokumentace platformy |
| M1 | Instalace OS a základní kontrola rozhraní |
| M2 | Ověření rizik a hardwarových předpokladů |
| M3 | Jádro, SQLite a jednotné JSON rozhraní |
| M4 | Drátové MVP |
| M5 | Wi-Fi a Bluetooth |
| M6 | Bezpečnostní analýza, monitoring a dashboard |
| M7 | Volitelné rozšíření: reflector, LANBERT, Proxmark5 a vlastní HW |

## Bezpečnost

Projekt není určen k neoprávněnému skenování sítí. Každá aktivní funkce musí respektovat safe mode a oprávnění provozovatele sítě. Podrobnosti jsou v [AGENTS.md](AGENTS.md).

## Licence

Licence zatím není zvolena. Před zveřejněním implementace ji vlastník projektu výslovně vybere.
