# CI/CD a bezpečnostní automatizace

Stav: workflow soubory jsou přidány do vývojové větve `pre-device-foundation`. Aktivace na výchozí větvi nastane až po schválení a sloučení PR; do té doby se ověřují běhy vyvolané pull requestem.

## Automatizace

| Workflow | Spuštění | Účel |
|---|---|---|
| `Python checks` | push, PR, ručně, každé pondělí | Testy Python 3.10–3.13, Ruff, sestavení FlipCTL balíčku a uložení artefaktu |
| `CodeQL security analysis` | push, PR, ručně, každé pondělí | Statická analýza Pythonu a GitHub Actions, sada `security-extended` |
| `Dependency review` | PR do `main`, ručně | Kontrola nových/změněných závislostí; blokuje známé závažné (high/critical) zranitelnosti |
| `Python security checks` | push, PR, ručně, každé pondělí | `pip-audit`, Bandit pro nálezy vysoké závažnosti a kontrola kompilovatelnosti |

Všechny workflow mají explicitní minimální oprávnění `GITHUB_TOKEN`, časový limit a omezení souběžných běhů. Použité GitHub Actions jsou připnuté na konkrétní plné commit SHA; Dependabot kontroluje jejich aktualizace.

## Dependabot

`.github/dependabot.yml` sleduje:
- Python závislosti v kořeni projektu – týdně; běžné minor/patch aktualizace slučuje do jedné PR skupiny, major aktualizace ponechává samostatně.
- GitHub Actions v `.github/workflows` – týdně.

Dependabot pouze otevírá pull requesty. Žádné automatické slučování ani automatické nasazení není zapnuté.

## Co je potřeba zkontrolovat v nastavení repozitáře

GitHub Actions už jsou prokazatelně aktivní – repozitář má úspěšné běhy CI. Některá nastavení zabezpečení jsou ale nastavení repozitáře/účtu, ne soubory workflow; dostupné připojení k GitHubu je neumí bezpečně změnit. Po otevření **Settings → Security** zkontrolovat:

1. **Dependency graph** – zapnout, pokud není aktivní; Dependency Review jej potřebuje.
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
