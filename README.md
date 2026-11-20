# Flipper One Network Diagnostics

Open-source lokální diagnostická sada pro síťové funkce platformy Flipper One. Cílem je převzít softwarově realizovatelné diagnostické postupy známé z rodin NetAlly LinkRunner, EtherScope, AirCheck a CyberScope, nikoli kopírovat jejich proprietární rozhraní nebo cloudové služby.

> **Stav:** přenosný softwarový základ ve vývoji; hardwarové schopnosti a integrace s cílovým OS se ověřují samostatně.

## Závazný dokument pro AI a vývojáře

Před jakoukoli změnou kódu nebo technickým tvrzením si přečti celý [AGENTS.md](AGENTS.md). Obsahuje pravidla ověřování, bezpečnostní omezení, matici 45 funkcí F-01 až F-45 a milníky M0–M7.

## Co je připraveno

- Python balíček v `src/flipper_diag/`.
- Read-only příkaz `flipper-diag doctor` pro inventuru lokálního systému a dostupných síťových nástrojů; negeneruje síťový provoz.
- Verzovaný datový model výsledků diagnostiky.
- Základní default-deny politika pro aktivní operace.
- Automatické testy pro výchozí bezpečnostní chování a read-only inventuru.

Spuštění ve vývojovém prostředí:

```bash
python -m pip install -e ".[dev]"
pytest
flipper-diag doctor
flipper-diag doctor --json
```

## Architektura a vývoj před doručením zařízení

- [Software strategy](docs/software-strategy.md) – co lze vyvíjet bez Flipper One, rozhodnutí o Pythonu a plán integrace FlipCTL.
- [Architecture](docs/architecture.md) – oddělení jádra, kolektorů, úložiště, API a prezentace.
- [Verification register](docs/verification.md) – evidence skutečných hardwarových testů.
- [Roadmap](docs/roadmap.md) – milníky M0–M7.
- [AGENTS.md](AGENTS.md) – úplný backlog F-01 až F-45 a závazná pravidla.

## Cíle

- Lokální provoz bez cloudových závislostí.
- Pasivní diagnostika jako výchozí režim.
- Aktivní testy pouze v sítích, kde má uživatel oprávnění testovat.
- Jednotné výstupy kolektorů, ukládání do SQLite a export HTML/PDF/CSV.
- Jasné oddělení funkcí proveditelných softwarem od funkcí vyžadujících vlastní elektroniku.

## Bezpečnost

Projekt není určen k neoprávněnému skenování sítí. Každá aktivní funkce musí respektovat Safe Mode a oprávnění provozovatele sítě. Základní politika je fail-closed; před připojením skutečných aktivních kolektorů bude rozšířena o allowlist příkazů, validaci rozsahů a auditní log.

## Licence

Licence zatím není zvolena. Před zveřejněním implementace ji vlastník projektu výslovně vybere.
