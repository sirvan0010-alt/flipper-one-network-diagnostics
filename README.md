# Flipper One Network Diagnostics

Open-source lokální diagnostická sada pro síťové funkce platformy Flipper One. Cílem je převzít softwarově realizovatelné diagnostické postupy známé z rodin NetAlly LinkRunner, EtherScope, AirCheck a CyberScope, nikoli kopírovat jejich proprietární rozhraní nebo cloudové služby.

> **Stav:** přenosný softwarový základ ve vývoji; hardwarové schopnosti a integrace s cílovým OS se ověřují samostatně.

## Závazný dokument pro AI a vývojáře

Před jakoukoli změnou kódu nebo technickým tvrzením si přečti celý [AGENTS.md](AGENTS.md). Obsahuje pravidla ověřování, bezpečnostní omezení, matici 45 funkcí F-01 až F-45 a milníky M0–M7.

## Co je připraveno

- Python balíček v `src/flipper_diag/`.
- Read-only příkaz `flipper-diag doctor` pro inventuru lokálního systému a dostupných síťových nástrojů.
- Read-only inventář rozhraní přes `iproute2` a stav Ethernet linky přes `ethtool`.
- První samostatná FlipCTL Python aplikace ovládaná displejem a fyzickými tlačítky.
- Lokální historie výsledků v SQLite a pojmenované inventory baseline.
- První pravidla pro nové/chybějící zařízení, změny IP a duplicitní IP.
- Offline CLI pro ukládání a porovnávání inventářů proti pojmenované baseline.
- Verzovaný datový model výsledků diagnostiky.
- Základní default-deny politika pro aktivní operace.
- Automatické testy pro výchozí bezpečnostní chování a read-only inventuru.

Spuštění ve vývojovém prostředí:

```bash
python -m pip install -e ".[dev]"
pytest
flipper-diag doctor
flipper-diag doctor --json
flipper-diag interfaces --json
flipper-diag routes --json
flipper-diag dns --json
flipper-diag local-check --json
# Example only: replace this TEST-NET address with one IP you are authorized to test
flipper-diag ping --target 192.0.2.1 --scope 192.0.2.1/32 --confirm-active --json
flipper-diag interfaces
flipper-diag link eth0
flipper-diag baseline save --name office --input inventory.json
flipper-diag baseline compare --name office --input current-inventory.json
python scripts/package_flipctl_app.py
flipper-diag history
flipper-diag history --json
```

## Architektura a vývoj před doručením zařízení

- [Software strategy](docs/software-strategy.md) – standalone ovládání, technologie a integrace FlipCTL.
- [FlipCTL app integration](docs/flipctl-app-integration.md) – sestavení a instalace aplikace přímo na Flipper One.
- [Upstream watch](docs/upstream-watch.md) – sledované oficiální repozitáře a funkce, které nesmíme zbytečně duplikovat.
- [Feature matrix](docs/feature-matrix.md) – rozhodnutí pro všech 45 plánovaných funkcí: reuse, integrace, vlastní vývoj nebo odklad.
- [Architecture](docs/architecture.md) – oddělení jádra, kolektorů, úložiště, API a prezentace.
- [Data model](docs/data-model.md) – lokální SQLite a verzování schématu.
- [Active test authorization](docs/active-tests.md) – Safe Mode, limity a explicitní autorizace.
- [Verification register](docs/verification.md) – evidence skutečných hardwarových testů a první instalační smoke test po doručení zařízení.
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
