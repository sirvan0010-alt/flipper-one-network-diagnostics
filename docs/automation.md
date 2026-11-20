# CI/CD a bezpečnostní automatizace

Stav: workflow soubory jsou přidány do vývojové větve. Aktivace na výchozí větvi nastane až po schválení a sloučení PR; do té doby se ověřují běhy vyvolané pull requestem.

## Automatizace

| Workflow | Spuštění | Účel |
|---|---|---|
| `Python checks` – x86_64 | push, PR, ručně, každé pondělí | Ubuntu 24.04 x64; testy Python 3.10–3.13, Ruff, sestavení FlipCTL balíčku a uložení artefaktu |
| `Python checks` – ARM64 | stejné události | Ubuntu 24.04 ARM64; nativní testy, sestavení univerzálního wheelu, čistá offline instalace, SQLite/CLI smoke test, sestavení FlipCTL app bundle a import všech zabalených modulů bez site-packages |
| `CodeQL security analysis` | push, PR, ručně, každé pondělí | Statická analýza Pythonu a GitHub Actions, sada `security-extended` |
| `Python security checks` | push, PR, ručně, každé pondělí | `pip-audit`, Bandit pro nálezy vysoké závažnosti a kontrola kompilovatelnosti |

ARM64 job používá nativní GitHub-hosted runner `ubuntu-24.04-arm`, nikoli emulaci QEMU. Protože je repozitář veřejný, tento standardní runner je podle GitHubu dostupný pro veřejné projekty. Job ověřuje `aarch64`, spouští testy na ARM64, sestaví `py3-none-any` wheel, nainstaluje jej do čistého virtuálního prostředí bez indexu balíčků a provede read-only CLI/SQLite smoke test. Nakonec sestaví skutečný app adresář a importuje všechny jeho moduly v režimu Python `-S`, bez přístupu k vývojovému checkoutu a site-packages.

**Hranice důkazu:** úspěšný ARM64 CI job prokazuje běh na obecném Linuxu ARM64. Neprokazuje kompatibilitu s konkrétním Flipper OS image, jeho Python Runtime, ovladači, oprávněními ani fyzickým zařízením. To zůstává samostatným testem na cílovém hardware.

Všechny workflow mají explicitní minimální oprávnění `GITHUB_TOKEN`, časový limit a omezení souběžných běhů. Použité GitHub Actions jsou připnuté na konkrétní plné commit SHA; Dependabot kontroluje jejich aktualizace.

## Dependabot

`.github/dependabot.yml` sleduje:
- Python závislosti v kořeni projektu – týdně; běžné minor/patch aktualizace slučuje do jedné PR skupiny, major aktualizace ponechává samostatně.
- GitHub Actions v `.github/workflows` – týdně.

Dependabot pouze otevírá pull requesty. Žádné automatické slučování ani automatické nasazení není zapnuté. Konfigurace se začne pravidelně uplatňovat po sloučení do výchozí větve.

## Dependency Review – odloženo

První testovací běh akce Dependency Review skončil odpovědí GitHub API `403 Forbidden` při načítání rozdílu závislostí. Samotná akce ani workflow nemohou zapnout repository-level **Dependency Graph**. Abychom do PR nepřidávali trvale červenou kontrolu, workflow jsme zatím odebrali. Po zapnutí Dependency Graph v nastavení repozitáře lze Dependency Review vrátit.

## Co je potřeba zkontrolovat v nastavení repozitáře

GitHub Actions už jsou prokazatelně aktivní – repozitář má úspěšné běhy CI. Některá nastavení zabezpečení jsou ale nastavení repozitáře/účtu, ne soubory workflow; dostupné připojení k GitHubu je neumí bezpečně změnit. Po otevření **Settings → Security** zkontrolovat:

1. **Dependency graph** – zapnout; je podmínkou pro Dependency Review.
2. **Dependabot alerts** a **Dependabot security updates** – zapnout, pokud jsou dostupné.
3. **Secret scanning** a **Push protection** – zapnout, pokud jsou pro veřejný repozitář dostupné.
4. **Actions → General** – ponechat omezená oprávnění workflow; nepovolovat zápis tokenu pro pull requesty z forku.
5. **Require actions to be pinned to a full-length commit SHA** – lze zapnout až po ověření, že všechny workflow a případné další akce splňují pravidlo.

Tato nastavení nejsou v tomto commitu označena jako zapnutá, protože je nebylo možné změnit přes dostupné oprávnění/API. Samotné přidání workflow neznamená, že jsou tyto přepínače aktivní.

## Zásady

- Žádné automatické merge, release ani deploy.
- Žádné secrets v testovacích workflow.
- Žádné aktivní skenování sítě; CI pracuje jen s testy a zdrojovým kódem.
- Bezpečnostní nález má vést k opravě nebo zdokumentovanému zdůvodnění, ne k automatickému potlačení.
