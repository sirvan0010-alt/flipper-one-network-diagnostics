# Verification register

Tento dokument eviduje ověření předpokladů na konkrétním hardwaru a softwarovém obrazu. Nezaměňovat plán testu za výsledek testu.

## Pravidla evidence

Každý záznam musí obsahovat:
- datum a čas,
- přesný model desky, revizi a připojené periferie,
- verzi OS, kernelu, firmware a ovladačů,
- příkaz nebo reprodukovatelný postup,
- surový výstup / odkaz na artefakt,
- výsledek a omezení,
- stav: **[ověřeno: zdroj+datum]**, **[neověřeno]** nebo **[předpoklad]**.

## M2 – plán ověření

Zatím jde o plán. Výsledky doplnit až po provedení na odpovídajícím zařízení.

| ID | Oblast | Test / příkaz | Kritérium úspěchu | Stav |
|---|---|---|---|---|
| V-01 | Platforma | `uname -a`, `cat /etc/os-release` | Zaznamenána verze kernelu a OS | [neověřeno] |
| V-02 | Wi-Fi schopnosti | `iw list` | Výstup potvrzuje podporované pásma, šířky a režimy | [neověřeno] |
| V-03 | Monitor mode | Nastavit monitor interface a ověřit příjem radiotap rámců | Stabilní příjem na každém podporovaném pásmu; uložit PCAP | [neověřeno] |
| V-04 | 6 GHz | Ověřit dostupné kanály a příjem beacon/probe rámců v povolené regulační doméně | Zaznamenat skutečně dostupné kanály a omezení | [neověřeno] |
| V-05 | Injection | Pouze v izolované testovací laboratoři ověřit, zda ovladač a firmware funkci podporují | Jednoznačný reprodukovatelný výsledek; žádné testování cizích sítí | [neověřeno] |
| V-06 | STA + AP | `iw list` a následný souběžný test rozhraní | Zjistit, zda kombinace režimů funguje současně a s jakými omezeními | [neověřeno] |
| V-07 | Ethernet | `ethtool <interface>`, `ethtool -i <interface>` | Zaznamenána PHY, driver, rychlost a duplex | [neověřeno] |
| V-08 | Cable diagnostics | `ethtool --cable-test <interface>` (jen pokud driver/PHY podporuje) | Výsledek potvrzuje nebo vyvrací dostupnost diagnostiky; nepředpokládat TDR | [neověřeno] |
| V-09 | Ethernet čítače | `ethtool -S <interface>` | Identifikovat dostupné chybové čítače a jejich význam | [neověřeno] |
| V-10 | USB Wi-Fi adaptér | Ověřit přesný model, USB ID, chipset, driver a firmware | Kompletní identifikace a funkční monitor mode | [neověřeno] |

## Záznamy měření

Zatím nejsou vložena žádná fyzická měření. Po testu přidej datumovaný záznam, neupravuj zpětně surové výstupy a citlivé údaje (SSID, MAC, veřejné IP) před publikací anonymizuj.
