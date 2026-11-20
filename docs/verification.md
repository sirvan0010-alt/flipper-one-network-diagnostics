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


## First Flipper One application smoke test (run only after device arrival)

These are pending tests, not claims that the current build already works on the device.

| ID | Area | Procedure | Acceptance criteria | Status |
|---|---|---|---|---|
| V-11 | Python runtime | `python3 --version`; `python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'` | Python runtime and SQLite module import successfully | [neověřeno] |
| V-12 | FlipCTL runtime | Install/enable the official Python Runtime, then launch a minimal upstream Ping app | FlipCTL opens the app, displays content and delivers physical key events | [neověřeno] |
| V-13 | Our app package | Copy the CI-built Network Diagnostics folder into `~/Apps/Network Diagnostics/`; launch from FlipCTL | App is discovered, imports the sibling `flipper_diag/` package and opens the main menu | [neověřeno] |
| V-14 | Local Check | Run Local Check with no PC connected and no active test enabled | Interface, wired-port, link, route and DNS status render without network probes | [neověřeno] |
| V-15 | SQLite persistence | Run Local Check twice, close/reopen app and inspect local history | Results persist across app restart; no cloud or PC needed | [neověřeno] |
| V-16 | Offline operation | Install dependencies once, disable Wi-Fi/internet, relaunch app and view prior results | Ordinary local diagnostics and history remain usable offline | [neověřeno] |
| V-17 | Physical controls | Navigate all menu/detail/history screens using built-in controls | No external keyboard, mouse, touchscreen or PC required | [neověřeno] |
| V-18 | Display fit | Inspect 256×144 screen, scroll long findings and recommendations | Text is legible; no clipped controls; all findings reachable | [neověřeno] |
| V-19 | Wired/Wi-Fi classification | Compare `ip -j address show` with `/sys/class/net/<iface>/wireless` | Wi-Fi is never offered as a wired port; unknown medium is reported as unknown | [neověřeno] |
| V-20 | Ethernet link fallback | Compare ethtool output with `operstate`, `carrier`, `speed`, `duplex` under `/sys/class/net/<iface>/` | Link status is correct where the driver exposes it; unavailable values remain unknown | [neověřeno] |
| V-21 | Resource use | Record idle and Local Check RSS, CPU and thermal-zone values | No crash, runaway CPU or unsafe thermal rise; record measurements for later budget | [neověřeno] |
| V-22 | PC independence | Boot and complete the local workflow with no USB tether or remote frontend | Core workflow completes entirely on Flipper One | [neověřeno] |

### Suggested capture commands

Run these locally on the target and attach the raw output to the dated verification record:

```sh
uname -a
cat /etc/os-release
python3 --version
python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'
ip -j address show
ip -j route show default
ip -6 -j route show default
for iface in /sys/class/net/*; do
  name=${iface##*/}
  printf '%s wireless=' "$name"
  if [ -d "$iface/wireless" ]; then echo yes; else echo no-or-unknown; fi
  for attr in operstate carrier speed duplex; do
    [ -r "$iface/$attr" ] && printf '  %s=%s\n' "$attr" "$(cat "$iface/$attr")"
  done
done
free -h
```

The system-shell check for `flipctl` is intentionally not prescribed: the Python Runtime supplies its own FlipCTL module path when it launches a `.fap.py` app. Validate that API through the actual FlipCTL launcher, not by assuming a global Python import.
