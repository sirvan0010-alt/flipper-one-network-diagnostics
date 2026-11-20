# Architecture – návrh

Tento dokument je výchozí návrh, nikoli potvrzení implementace. Technická rozhodnutí označuj jako otevřená, dokud nejsou ověřena.

## Cílové použití

Běžné testy musí být možné spustit a vyhodnotit přímo na Flipper One bez připojeného PC. Integrovaný displej a ovládací prvky jsou primární UI. Web/desktop/SSH jsou volitelné rozšířené ovládací a analytické frontendy, nikoli runtime podmínka.

## Principy

1. Kolektory oddělit od UI a reportingu.
2. Každý kolektor vrací verzovaný JSON výsledek se stavem, časem, rozhraním, parametry a diagnostickými nálezy.
3. Ukládat výsledky lokálně do SQLite.
4. Zachovat pasivní safe mode jako výchozí režim; aktivní operace vyžadují explicitní povolení a omezený rozsah.
5. Žádné povinné cloudové služby.
6. Logovat původ dat, verzi nástroje a omezení měření.
7. Jádro musí jít spustit na běžném Linuxu bez Flipper One.
8. Integrace FlipCTL bude samostatný adaptér, nikoli závislost diagnostického jádra.
9. Využívat nativní Flipper OS/FlipCTL funkce místo jejich duplikace.

## Navržené vrstvy

- **Collectors:** obálky nad systémovými nástroji a vlastní parsování (např. iproute2, ethtool, tcpdump/tshark, iperf3, iw, BlueZ, SNMP).
- **Core:** plánování úloh, politika safe mode, normalizace výsledků, pravidla nálezů.
- **Storage:** SQLite, migrace schématu, baseline a historie; aktuální návrh je v [data-model.md](data-model.md).
- **CLI/API:** přenositelné rozhraní mezi jádrem a prezentační vrstvou; lokální JSON výsledky.
- **Presentation:** tenký FlipCTL app wrapper po ověření upstream API; primární ovládání na displeji Flipper One. Volitelně lokální web dashboard, TUI a export HTML/PDF/CSV.

## Technologie – počáteční rozhodnutí

Pro první fázi používáme Python 3.10+ a standardní knihovnu. Důvody a hranice rozhodnutí jsou v [software-strategy.md](software-strategy.md).

Python je zatím rozhodnutí pro přenositelné jádro a testy, nikoli potvrzená volba finálního běhového prostředí Flipper OS. Před integrací ověříme Python runtime, paměť, start aplikace, balíčkování a spotřebu. Těžký trvale běžící server není předpokladem.

## Otevřená rozhodnutí

- Verze Pythonu a systémové balíčky dostupné ve finálním Flipper OS image.
- Přesné rozhraní mezi kolektory a prezentační vrstvou.
- Způsob izolace privilegovaných síťových operací.
- Model autentizace a zabezpečení volitelného lokálního web dashboardu.
- Stabilní rozhraní FlipCTL pro externí aplikace a pluginy.
- Potřeba druhého Wi-Fi adaptéru pro souběžné režimy.
- Které oficiální síťové funkce Flipper OS budou dostupné jako nástroje/služby a které bude nutné doplnit.

## Bezpečnostní návrh

- Safe mode blokuje aktivní skeny, probe, DHCP požadavky iniciované diagnostikou a další vysílání, které není nezbytné pro pasivní příjem.
- Každá aktivní úloha musí zobrazit rozsah, cíle a typ provozu před spuštěním.
- Autorizační policy vyžaduje explicitní IP/CIDR rozsah, potvrzené cílové IP adresy uvnitř tohoto rozsahu a limit 256 cílů na jednu operaci; hostname nejsou povoleny.
- Aktivní kolektory musí spouštět pevně sestavené argumentové seznamy bez shell interpolace a s timeoutem.
- Výchozí rozsah nesmí být automaticky celá síť bez potvrzení uživatele.
- Žádné automatické obcházení firewallů, autentizace ani přístupových kontrol.
- Před spuštěním privilegovaného příkazu se používá allowlist příkazů a argumentů; neskládat shellové řetězce z uživatelského vstupu.

## Kontrola upstream závislostí

Před návrhem nové funkce projít [upstream-watch.md](upstream-watch.md). Rozlišovat dokumentovaný záměr, prototyp, sloučenou implementaci, ověření na cílovém HW a vydanou funkci.
