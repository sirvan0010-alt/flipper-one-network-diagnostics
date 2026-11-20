# Architecture – návrh

Tento dokument je výchozí návrh, nikoli potvrzení implementace. Technická rozhodnutí označuj jako otevřená, dokud nejsou ověřena.

## Principy

1. Kolektory oddělit od UI a reportingu.
2. Každý kolektor vrací verzovaný JSON výsledek se stavem, časem, rozhraním, parametry a diagnostickými nálezy.
3. Ukládat výsledky lokálně do SQLite.
4. Zachovat pasivní safe mode jako výchozí režim; aktivní operace vyžadují explicitní povolení a omezený rozsah.
5. Žádné povinné cloudové služby.
6. Logovat původ dat, verzi nástroje a omezení měření.
7. Jádro musí jít spustit na běžném Linuxu bez Flipper One.
8. Integrace FlipCTL bude samostatný adaptér, nikoli závislost diagnostického jádra.

## Navržené vrstvy

- **Collectors:** obálky nad systémovými nástroji a vlastní parsování (např. iproute2, ethtool, tcpdump/tshark, iperf3, iw, BlueZ, SNMP).
- **Core:** plánování úloh, politika safe mode, normalizace výsledků, pravidla nálezů.
- **Storage:** SQLite, migrace schématu, baseline a historie.
- **API:** lokální JSON rozhraní mezi jádrem a UI.
- **Presentation:** FlipCTL adapter po ověření jeho rozhraní; lokální web dashboard a export HTML/PDF/CSV; malé stavové UI na zařízení podle možností displeje.

## Technologie – počáteční rozhodnutí

Pro první fázi používáme Python 3.10+ a standardní knihovnu. Důvody a hranice rozhodnutí jsou v [software-strategy.md](software-strategy.md). Cílem není záviset na konkrétním Python frameworku ani na neověřeném FlipCTL plugin API.

## Otevřená rozhodnutí

- Verze Pythonu a systémové balíčky dostupné ve finálním Flipper OS image.
- Přesné rozhraní mezi kolektory a API.
- Způsob izolace privilegovaných síťových operací.
- Model autentizace a zabezpečení lokálního web dashboardu.
- Stabilní rozhraní FlipCTL pro externí aplikace a pluginy.
- Potřeba druhého Wi-Fi adaptéru pro souběžné režimy.

## Bezpečnostní návrh

- Safe mode blokuje aktivní skeny, probe, DHCP požadavky iniciované diagnostikou a další vysílání, které není nezbytné pro pasivní příjem.
- Každá aktivní úloha musí zobrazit rozsah, cíle a typ provozu před spuštěním.
- Výchozí rozsah nesmí být automaticky celá síť bez potvrzení uživatele.
- Žádné automatické obcházení firewallů, autentizace ani přístupových kontrol.
- Před spuštěním privilegovaného příkazu se používá allowlist příkazů a argumentů; neskládat shellové řetězce z uživatelského vstupu.
