# Architecture – návrh

Tento dokument je výchozí návrh, nikoli potvrzení implementace. Technická rozhodnutí označuj jako otevřená, dokud nejsou ověřena.

## Principy

1. Kolektory oddělit od UI a reportingu.
2. Každý kolektor vrací verzovaný JSON výsledek se stavem, časem, rozhraním, parametry a diagnostickými nálezy.
3. Ukládat výsledky lokálně do SQLite.
4. Zachovat pasivní safe mode jako výchozí režim; aktivní operace vyžadují explicitní povolení.
5. Žádné povinné cloudové služby.
6. Logovat původ dat, verzi nástroje a omezení měření.

## Navržené vrstvy

- **Collectors:** obálky nad systémovými nástroji a vlastní parsování (např. iproute2, ethtool, tcpdump/tshark, iperf3, iw, BlueZ, SNMP).
- **Core:** plánování úloh, politika safe mode, normalizace výsledků, pravidla nálezů.
- **Storage:** SQLite, migrace schématu, baseline a historie.
- **API:** lokální JSON rozhraní mezi jádrem a UI.
- **Presentation:** lokální web dashboard, export HTML/PDF/CSV; malé stavové UI na zařízení podle možností displeje.

## Otevřená rozhodnutí

- Jazyk jádra: Python pro rychlé obalení CLI nástrojů, nebo C#/.NET pro linux-arm64.
- Konkrétní vývojová deska a cílový obraz OS.
- Přesné rozhraní mezi kolektory a API.
- Způsob izolace privilegovaných síťových operací.
- Model autentizace a zabezpečení lokálního web dashboardu.

## Bezpečnostní návrh

- Safe mode blokuje aktivní skeny, probe, DHCP požadavky iniciované diagnostikou a další vysílání, které není nezbytné pro pasivní příjem.
- Každá aktivní úloha musí zobrazit rozsah, cíle a typ provozu před spuštěním.
- Výchozí rozsah nesmí být automaticky celá síť bez potvrzení uživatele.
- Žádné automatické obcházení firewallů, autentizace ani přístupových kontrol.
