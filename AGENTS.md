# AGENTS.md – Flipper One síťový diagnostický nástroj (návod pro AI)

Stav dokumentu: 2026-11-20. Tento soubor čti celý, než napíšeš jakýkoli kód nebo tvrzení.

## 1. Cíl projektu
Open-source diagnostická sada pro Flipper One (Linux), která funkčně nahrazuje to,
co jde softwarově z přístrojů NetAlly (LinkRunner, EtherScope, AirCheck).
Nekopírujeme jejich UI ani cloud (Link-Live, AllyCare). Reporty a data jsou lokální.

## 2. Pravidla pro AI (závazná)
1. Každé technické tvrzení o hardwaru označ: **[ověřeno: zdroj+datum]**, **[neověřeno]** nebo **[předpoklad]**.
2. Nic si nevymýšlej. Co není v dokumentaci, napiš jako neověřené a navrhni, jak to otestovat.
3. Než se spolehneš na údaj níže, zkontroluj datum aktualizace zdrojové stránky. Flipper One se vyvíjí, specifikace se mění.
4. Hardware, který na zařízení nejde, přiznej hned. Nepřekrucuj ho softwarovým "řešením".
5. Aktivní skeny (Nmap, probe, DHCP request) jen v sítích, kde je uživatel oprávněn testovat. Každá aktivní funkce musí mít "safe mode" (jen pasivní).
6. Žádné cloudové závislosti. Vše lokálně (SQLite, HTML/PDF/CSV export).
7. Do upstreamu Flipperu (GitHub/Discord) nepiš wishlisty. Piš jen konkrétní příspěvky (viz sekce 8).

## 3. Ověřená fakta o zařízení
Zdroj: https://docs.flipper.net/one/general/tech-specs (aktualizováno 11. 8. 2026)
- SoC Rockchip RK3576 (4× A72 + 4× A53), 8 GB RAM, 64 GB UFS, NPU 6 TOPS
- Wi-Fi/BT: MT7921AUN, Wi-Fi 6E 2×2, USB 3.0; open-source driver, **monitor mode podporován** (https://docs.flipper.net/one/hardware/wifi-bluetooth, 1. 7. 2026). **Injection: [neověřeno]**
- Ethernet: 2× RJ45 1G, PHY RTL8211F. **Diagnostické/TDR registry: [neověřeno]**, zjistit z datasheetu a `ethtool --cable-test`
- Porty: USB-C1 (3.1, DP, PD), USB-C2, USB-A (vše 5 Gbps host), HDMI 2.1
- M.2 Key B: PCIe 2.1 x1 / USB 3.1 / USB 2.0 / SATA / UART / I2C
- GPIO: 3,3 V a 5 V po 2 A, I2C/SPI/UART/CAN, USB 2.0 D+/D-
- Displej 256×144 mono, ovládání tlačítky a touchpadem. Složité UI patří na HDMI/web.
- **Zařízení NENÍ v prodeji.** Existuje jen prototyp F0B0C1 (https://docs.flipper.net/one/cpu-software/supported-boards, 9. 10. 2026).
- OS: Flipper OS, Debian + profily (mj. "Network sniffer"). https://docs.flipper.net/one/cpu-software/flipper-os (16. 7. 2026)
- Vlastní funkce Flipperu, které se překrývají s námi: LAN discovery (pasivní/aktivní), Ethernet MitM sniffer, VLAN detekce (https://docs.flipper.net/one/general/features). Navazuj, nedělej duplicitu.

## 4. Co NEJDE bez vlastní elektroniky (přiznáno)
Wiremap, TDR/délka kabelu, toning, PoE analyzér a zátěž (až 90 W), měření SNR Multi-Gig, SFP/optika,
rozpoznání NBASE-T/10G linky (porty jsou jen 1G), reálná spektrální analýza a detekce ne-Wi-Fi rušení
(NetAlly používá externí adaptér NXT-2000). RJ45 porty Flipperu jdou přes PHY a magnetiku, takže jednotlivé
páry nezměříme. 10G je omezeno PCIe 2.1 x1 a USB 5 Gbps (realisticky 2,5G až 5G).
Tyto věci řešit jen jako samostatný hardwarový projekt (GPIO/USB/M.2 modul) mimo MVP.
Rozdíl proti NetAlly: AirCheck/CyberScope mají 2 Wi-Fi rádia (testovací 2×2 tri-band + řídicí 1×1). Flipper One má jedno
vestavěné, takže souběh "měřím + vzdálené ovládání" nebo "aktivní + pasivní survey" vyžaduje druhý USB adaptér **[ověřit]**.

## 5. Zdrojová zařízení a matice funkcí
Prošlá zařízení (zdroje: netally.com, cyberscope.netally.com, datasheety, k 20. 11. 2026):
LinkRunner AT 4000 (https://www.netally.com/products/linkrunner-4000/), LinkRunner 10G, EtherScope nXG (zkratka EXG v kódech modelů),
AirCheck G3 Pro (https://www.netally.com/products/aircheckg3), AirCheck G2 (NETSCOUT/NetAlly, starší 802.11ac),
CyberScope CE/XRF (https://cyberscope.netally.com/products/cyberscope), CyberScope Air (https://cyberscope.netally.com/products/cyberscope-air; prodej modelů X2 končí 30. 9. 2026).
CyberScope = EtherScope nXG + Nmap/security. CyberScope Air = AirCheck G3 Pro + Nmap/security.
Funkce vázané na placený AllyCare/Link-Live (cloudová topologie, InSites, web remote control) nepřejímáme, nahrazujeme lokálně.

Legenda: ANO = softwarově proveditelné, ČÁSTEČNĚ = s omezením, NE = vyžaduje vlastní HW, NEPŘEJÍMÁME = cloud/služba.
Zdroj: LR = LinkRunner, ES = EtherScope nXG, AC = AirCheck G2/G3, CS = CyberScope.

### 5.1 Drátová síť
| Funkce (zdroj) | Stav | Poznámka |
|---|---|---|
| AutoTest + profily + skupiny profilů (LR, ES, CS) | ANO | 8 kroků: link, DHCP, DNS, gateway, rychlost, odezva služeb. Skupina profilů = jedno tlačítko pro všechny VLAN. AutoTest = ověření konektivity |
| Periodic AutoTest (1 min až 24 h) (LR, ES, AC) | ANO | lokální plánovač + SQLite |
| Switch test: CDP/LLDP/EDP, název a port switche, VLAN a Voice VLAN z provozu (LR, AC G2) | ANO | lldpd + vlastní parser |
| Link speed/duplex 10/100/1G (LR) | ANO | `ethtool` |
| Multi-Gig/NBASE-T detekce (LR 10G) | NE | porty 1G |
| PoE: nabízený výkon podle switche (LLDP Power-via-MDI) | ČÁSTEČNĚ | čtení LLDP TLV ano, měření pod zátěží NE |
| Ping/TCP test, MTU (DF bit), 24h trend, ztrátovost (LR, ES) | ANO | |
| HTTP/FTP response time (LR, ES) | ANO | |
| Discovery: zařízení, typy, adresy, VLAN, switch/port, SNMP agenti, VoIP, tiskárny, hypervizory/VM, Wi-Fi kontrolery (ES, LR) | ANO | net-snmp + fingerprinting |
| Problémový engine: duplicitní IP, přetížený port, lost DHCP lease, half-duplex, STP change, SNMPv3 agent odpovídá na v1/v2… (LR, ES, AC) | ANO | pravidla lokálně, bez InSites cloudu |
| Path Analysis L2/L3 přes SNMP (chyby rozhraní, vytížení) (LR, ES, AC) | ANO | traceroute + SNMP |
| Topologická mapa (Link-Live) | ČÁSTEČNĚ | lokální graf z LLDP/SNMP dat, bez cloudu |
| Packet capture 1G, PCAP, filtr, slicing (LR, ES) | ANO | tcpdump/tshark |
| iPerf (LR, ES, AC) | ANO | iperf3 |
| Performance až 8 proudů, reflector s prohazováním MAC/IP (LR, ES) | ČÁSTEČNĚ | vlastní reflector+controller pro 2 jednotky. Kompatibilita s NetAlly **[předpoklad: ne]** |
| LANBERT (soak test média, 2 jednotky nebo loopback) (LR) | ČÁSTEČNĚ | generátor rámců + čítače `ethtool -S` **[neověřeno]**; reálná kvalifikace kabeláže závisí na PHY |
| Cable test, WireView, toning, fiber (LR) | NE | viz sekce 4 |

### 5.2 Wi-Fi a Bluetooth
| Funkce (zdroj) | Stav | Poznámka |
|---|---|---|
| Wi-Fi AutoTest profil "Wireless Network Test": síla signálu, rychlost, 802.1X, vytížení kanálu, info o AP, DHCP/DNS/GW, neomezené cíle ping/TCP/HTTP/FTP, pass/fail prahy (AC, ES, CS) | ANO | wpa_supplicant (WPA3, 802.1X) |
| Air Quality Test (vytížení + co-channel/adjacent interference) (AC) | ČÁSTEČNĚ | jen 802.11 provoz; ne-Wi-Fi rušení NE |
| Mapa kanálů: počet AP/klientů, retry %, historie 60 s (AC, ES) | ANO | monitor mode |
| Seznam AP/klientů, detail, autorizace (pojmenování, známé/neznámé) (AC, ES, CS) | ANO | |
| Roaming test s vyznačením roamu v grafu (AC G2/G3) | ANO | |
| Locate: hledání AP/klienta podle RSSI (AC, CS) | ANO | směrová anténa jen s externím adaptérem **[ověřit]** |
| Wi-Fi security audit: špatný protokol, open auth, client isolation, podezřelé broadcasty, rogue AP, zlomyslné beacony (CS, AC) | ANO | |
| Wi-Fi packet capture 2,4/5/6 GHz, filtr, slicing (AC, ES) | ANO | MT7921AUN; 6 GHz jen pasivně **[ověřit]** |
| Wi-Fi 7 viditelnost (MLO, 320 MHz, RNR, PSC, multi-BSSID, WPA3) (AC G3, CS) | ČÁSTEČNĚ | čip je Wi-Fi 6E; parsování IE z beaconů v monitor módu **[předpoklad, ověřit]**; aktivní Wi-Fi 7 spojení NE |
| AirMapper site survey Wi-Fi + BLE, heat mapy, aktivní i pasivní (AC, ES, CS) | ČÁSTEČNĚ | pasivní ano; souběh aktivní+pasivní potřebuje 2. rádio; UI na telefonu/webu |
| BLE discovery a BLE survey | ANO | BlueZ |
| Spektrum (NXT-2000) (AC, ES, CS) | NE | externí HW |
| Průběžný ping během chůzí po budově (AC G2) | ANO | |

### 5.3 Bezpečnost (CyberScope)
| Funkce | Stav | Poznámka |
|---|---|---|
| Discovery IT/IoT/OT/ICS zařízení | ANO | |
| Nmap integrovaný do AutoTestu jedním tlačítkem | ANO | + NSE (např. vulners) |
| Hledání CVE, otevřených "zadních vrátek", špatně nastavených firewallů | ČÁSTEČNĚ | Nmap/NSE, ne náhrada profesionálního vulnerability scanneru |
| Discovery Monitoring: nová/chybějící/změněná zařízení proti baseline, bezpečnostní snapshoty | ANO | SQLite + diff |
| Rogue AP hledání s direkční anténou | ČÁSTEČNĚ | viz Locate |
| Reporty s mapováním na CIS Controls a NIS2 (jen jako podpora, ne certifikace) | ANO | šablony HTML/PDF |
| Link-Live Cyber (dashboardy, trendy) | NEPŘEJÍMÁME | volitelně lokální web dashboard |

### 5.4 Ostatní
| Funkce | Stav |
|---|---|
| Lokální vzdálené ovládání (VNC/web) | ANO |
| Link-Live, AllyCare, InSites, web remote control | NEPŘEJÍMÁME |
| Reporty CSV/PDF/HTML lokálně | ANO |
| Proxmark5 integrace přes USB/Wi-Fi/BLE | **[neověřeno: ověřit konkrétní PM5+BWM firmware, transport a zabezpečení]** |

## 6. Plán funkcí (backlog k implementaci)
Jen funkce, které Flipper One hardwarově zvládne (ANO) nebo zvládne s omezením (ČÁSTEČNĚ). Hardwarové věci jsou v sekci 4.
Fáze odkazují na milníky v sekci 7. Zkratky zdrojů: LR = LinkRunner AT 4000/10G, ES = EtherScope nXG, AC = AirCheck G2/G3,
CS = CyberScope (CE/Air), F1 = vlastní funkce Flipper One, vlastní = naše doplnění.

### 6.1 Drátová síť
| ID | Funkce | Co dělá | Převzato z | Stav | Fáze |
|---|---|---|---|---|---|
| F-01 | Wired AutoTest | Jedním tlačítkem ověří link, DHCP, DNS, gateway, rychlost a odezvu služeb, výsledek pass/fail | LR, ES, CS | ANO | M4 |
| F-02 | Profily a cíle testů | Uložené konfigurace testů a opakovaně použitelné cíle. Skupina profilů otestuje všechny VLAN najednou | LR, AC | ANO | M4 |
| F-03 | Periodic AutoTest | Spouští profily v intervalu 1 min až 24 h a ukládá výsledky pro dlouhodobé sledování přerušovaných poruch | LR, ES, AC | ANO | M6 |
| F-04 | Switch test (xDP) | Z CDP/LLDP/EDP přečte název switche, port, VLAN a Voice VLAN | LR, AC G2 | ANO | M4 |
| F-05 | Detekce VLAN | Z přijatého provozu vypíše VLAN ID na portu a rozložení provozu mezi ně | LR | ANO | M4 |
| F-06 | Rychlost a duplex linky | Ověří 10/100/1000 a duplex, odhalí slevení rychlosti (downshift) | LR | ANO | M4 |
| F-07 | Nabízený PoE výkon | Z LLDP (Power-via-MDI) přečte, co switch nabízí. Měření pod zátěží NE | LR | ČÁSTEČNĚ | M4 |
| F-08 | Ping / TCP Connect | ICMP a TCP test cíle, test MTU (DF bit), 24h trend a ztrátovost | LR, ES, AC | ANO | M4 |
| F-09 | HTTP / FTP response time | Měří odezvu webu a FTP serveru | LR, ES, AC | ANO | M4 |
| F-10 | Wired Discovery | Inventář zařízení: typ, jméno, adresa, VLAN, switch a port. Zná SNMP agenty, VoIP, tiskárny, hypervizory, Wi-Fi kontrolery | ES, LR | ANO | M4 |
| F-11 | LAN discovery po vrstvách | Nejdřív čistě pasivně (ARP, IPv6 ND), pak ručně zapíná aktivní kroky (DHCP, VLAN, probe služeb) | F1 | ANO | M4 |
| F-12 | Problémový engine | Pravidla pro problémy: duplicitní IP, přetížený port, ztráta DHCP lease, half-duplex, změna STP, SNMPv3 agent odpovídající na v1/v2. Ke každému příčina a doporučení | LR, ES, AC | ANO | M6 |
| F-13 | Path Analysis | Trasa L2/L3 k cíli včetně mezilehlých zařízení, přes SNMP chyby rozhraní a vytížení | LR, ES, AC | ANO | M4 |
| F-14 | Topologická mapa | Lokální graf sítě z LLDP/SNMP dat (náhrada za cloudovou mapu) | LR, ES | ČÁSTEČNĚ | M6 |
| F-15 | Packet capture 1G | Zachytává provoz do PCAP, s filtrem a ořezem paketů | LR, ES | ANO | M4 |
| F-16 | Ethernet MitM sniffer | Zařízení vložené mezi dva porty jako neviditelný most, ukládá PCAP nebo zrcadlí do PC | F1 | ANO | M5 |
| F-17 | iPerf | Měření TCP/UDP propustnosti a ztrát přes iperf3 | LR, ES, AC | ANO | M4 |
| F-18 | Reflector + controller | Test propustnosti mezi dvěma jednotkami s prohazováním MAC/IP. Jen naše jednotky, s NetAlly nekompatibilní **[předpoklad]** | LR, ES | ČÁSTEČNĚ | M7 |
| F-19 | Soak test média (LANBERT) | Dlouhý test chybovosti kabeláže mezi dvěma jednotkami nebo s loopbackem, čítače `ethtool -S` **[neověřeno]** | LR | ČÁSTEČNĚ | M7 |

### 6.2 Wi-Fi a Bluetooth
| ID | Funkce | Co dělá | Převzato z | Stav | Fáze |
|---|---|---|---|---|---|
| F-20 | Wi-Fi AutoTest | Připojí se k SSID (včetně 802.1X) a změří signál, rychlost, vytížení kanálu, DHCP/DNS/gateway a cíle ping/TCP/HTTP/FTP s pass/fail prahy | AC, ES, CS | ANO | M5 |
| F-21 | Air Quality Test | Rychlé měření vytížení kanálů a rušení sousedními kanály. Jen 802.11, ne-Wi-Fi rušení NE | AC | ČÁSTEČNĚ | M5 |
| F-22 | Mapa kanálů | Počet AP a klientů, retry % a historie 60 s pro každý kanál 2,4/5/6 GHz | AC, ES | ANO | M5 |
| F-23 | Seznam AP a klientů | Detail každého AP a klienta, možnost pojmenovat a označit jako autorizované | AC, ES, CS | ANO | M5 |
| F-24 | Roaming test | Sleduje přechody mezi AP a v grafu je spojí se signálem a logem připojení | AC | ANO | M5 |
| F-25 | Locate | Hledání konkrétního AP nebo klienta podle síly signálu. Směrová anténa jen s externím adaptérem **[ověřit]** | AC, CS | ANO | M5 |
| F-26 | Wi-Fi security audit | Odhalí otevřenou autentizaci, slabé šifrování, chybějící client isolation, podezřelé broadcasty, rogue AP a zlomyslné beacony | CS, AC | ANO | M6 |
| F-27 | Wi-Fi packet capture | PCAP bezdrátového provozu na 2,4/5/6 GHz s filtrem a ořezem | AC, ES | ANO | M5 |
| F-28 | Wi-Fi 7 viditelnost | Z beaconů čte MLO, šířky kanálů, RNR, PSC, multi-BSSID, WPA3. Čip je Wi-Fi 6E, jen pasivně **[ověřit]** | AC G3, CS | ČÁSTEČNĚ | M5 |
| F-29 | Site survey | Měření signálu v bodech na půdorysu a heat mapy. Pasivní ano, souběh s aktivním potřebuje 2. rádio | AC, ES, CS | ČÁSTEČNĚ | M5 |
| F-30 | BLE discovery a survey | Najde Bluetooth LE zařízení a mapuje je na půdorysu | AC G3, ES, CS | ANO | M5 |
| F-31 | Ping při chůzi | Neustálý ping vybraného cíle se statistikou při pohybu po budově | AC G2 | ANO | M5 |
| F-32 | Nastavení regulační domény | Volba země omezí vysílání na povolené kanály, 6 GHz podle země | AC G2/G3 | ANO | M5 |

### 6.3 Bezpečnost
| ID | Funkce | Co dělá | Převzato z | Stav | Fáze |
|---|---|---|---|---|---|
| F-33 | Discovery IoT/OT/ICS | Najde a zařazuje zařízení mimo klasické IT (senzory, průmyslové řídicí systémy) | CS | ANO | M6 |
| F-34 | Nmap v AutoTestu | Port scan a detekce služeb a OS spuštěné spolu s testem konektivity | CS | ANO | M6 |
| F-35 | Hledání CVE | NSE skripty (např. vulners) hledají známé zranitelnosti. Není náhrada profesionálního scanneru | CS | ČÁSTEČNĚ | M6 |
| F-36 | Discovery Monitoring | Bezpečnostní snapshoty a porovnání s baseline: nová, chybějící a změněná zařízení | CS, ES, AC | ANO | M4 |
| F-37 | Batch autorizace | Hromadné označení zařízení jako známé nebo neznámé pro audit "kdo je v mé síti" | ES, AC, CS | ANO | M6 |
| F-38 | Reporty CIS / NIS2 | Šablony reportů s mapováním nálezů na kontroly CIS a NIS2. Jen podpora, ne certifikace | CS | ANO | M6 |

### 6.4 Platforma
| ID | Funkce | Co dělá | Převzato z | Stav | Fáze |
|---|---|---|---|---|---|
| F-39 | Lokální reporty | Export výsledků do HTML, PDF a CSV | LR, ES, AC, CS | ANO | M4 |
| F-40 | Trendové grafy | Grafy výsledků v čase (ping, capture, propustnost, Wi-Fi) | ES | ANO | M6 |
| F-41 | Lokální web dashboard | Přehled výsledků a topologie přes vlastní web, náhrada Link-Live | vlastní | ANO | M6 |
| F-42 | Vzdálené ovládání | Ovládání zařízení přes VNC nebo web v lokální síti | LR, ES, AC | ANO | M6 |
| F-43 | Export a import nastavení | Záloha a přenos profilů, cílů a prahů mezi jednotkami | ES | ANO | M5 |
| F-44 | Safe mode | Přepínač, který povolí jen pasivní funkce (pro produkční sítě) | vlastní | ANO | M3 |
| F-45 | Proxmark5 integrace | Společné ovládání přes USB jako základ; volitelně Wi-Fi/BLE přes BWM, pouze po ověření firmware/transportu/zabezpečení | vlastní | ČÁSTEČNĚ | M7 |

## 7. Postup od nuly
**M0 – Příprava.** Přečti dokumentaci Flipper One: How to join, Tech specs, Wi-Fi & Bluetooth, Flipper OS, Testing → Network.
Opatři vývojovou desku: Armsom Sige5 / Banana Pi BPI-M5 Pro (doporučená Flipperem), a USB Wi-Fi adaptér s čipem MT7921AU **[ověřit konkrétní model]**.
**M1 – Systém.** Nainstaluj Flipper OS dle "How to build / install a Linux image" (MaskROM). Ověř `uname -a`, `iw list`, `ethtool`.
**M2 – Ověření rizik (dřív než cokoli programovat).** Monitor mode na MT7921, zachycení radiotap rámců na 2,4/5/6 GHz, test injection, souběh STA+AP, `ethtool --cable-test` na RTL8211F. Výsledky zapiš do `docs/verification.md` se značkami z pravidla 1.
**M3 – Jádro.** Repozitář: `core/` (kolektory), `tests/`, `reports/`, `docs/`. SQLite schéma, jednotné JSON rozhraní mezi kolektory a UI. Jazyk: **otevřené rozhodnutí vlastníka** (Python pro obalení CLI nástrojů, nebo C# .NET na linux-arm64).
**M4 – MVP funkce:** Discovery + baseline, AutoTest profily, Ping/TCP, capture, iperf3, reporty.
**M5 – Wi-Fi:** Wi-Fi AutoTest profily, mapa kanálů, roaming, Locate, security audit, site survey, BLE. Pořiď druhý USB Wi-Fi adaptér.
**M6 – Problémový engine, Nmap v AutoTestu, Discovery Monitoring, CIS/NIS2 šablony reportů, periodický běh.**
**M7 – (volitelné)** Reflector/LANBERT pro 2 jednotky, Proxmark5 přes USB, vlastní HW moduly.

## 8. Kontrolní seznam před každým commitem
- Je každé hardwarové tvrzení označené (pravidlo 1)?
- Má aktivní funkce safe mode?
- Běží to bez internetu?
- Je matice v sekci 5 a plán funkcí v sekci 6 aktuální?

## 9. Spolupráce s Flipperem
Vstup: https://docs.flipper.net/one/how-to-join, task trackery https://github.com/orgs/flipperdevices/projects, repozitáře https://github.com/flipperdevices, Discord https://discord.com/invite/flipper.
Pravidla: komentuj jen úkoly s labelem `help wanted`, a to konkrétním příspěvkem (kód, test, měření). Nejvhodnější sekce: Testing → Network.

### 6.5 Povinné rozhodnutí: upstream reuse vs. vlastní implementace

Tato tabulka má přednost před původním plánem, pokud se funkce překrývá s oficiálním Flipper OS/FlipCTL. Před implementací vždy ověř skutečný stav upstreamu podle `docs/upstream-watch.md`.

| Naše ID | Oficiální schopnost / rozhraní | Rozhodnutí projektu |
|---|---|---|
| F-08 | `flipctl-slint` obsahuje `apps/ping.fap.py` a Python Runtime app | Nepřepisovat samostatný ping UI; pro AutoTest použít systémový ICMP nástroj nebo ověřený wrapper a přidat korelaci/práh v našem jádře |
| F-11 | Oficiálně popsané pasivní/aktivní LAN Discovery | Nepřepisovat discovery engine bez důkazu mezery; integrovat výsledky a doplnit vrstvenou diagnostiku |
| F-13 | FlipCTL wrapper pro traceroute | Reuse traceroute; vlastní bude korelace trasy se SNMP/LLDP a vysvětlení problémů |
| F-15 | Flipper OS Network Sniffer profil a systémové nástroje | Znovu použít dostupný capture stack; vlastní bude diagnostické filtrování, souhrny a vazba na nálezy |
| F-16 | Oficiálně popsaný Ethernet MitM Sniffer | Nevytvářet druhý transparentní bridge/capture engine; ověřit nativní implementaci a navázat analýzou PCAP |
| F-34 | FlipCTL wrapper pro Nmap | Použít oficiální wrapper, pokud je v cílovém systému dostupný; vlastní bude bezpečná autorizace, profil a interpretace výsledků |
| F-41/F-42 | `flipctl-slint` dokumentuje Python/JS `.fap.py` aplikace, AppImage bundles a vestavěné ovládání displejem/klávesami | Naši aplikaci dodat jako FlipCTL hosted app; nevyvíjet vlastní HMI ani remote-control framework |
| F-05 | Publikovaná produktová specifikace zmiňuje VLAN detekci | Nejdříve ověřit, co skutečně poskytuje Flipper OS; naši část omezit na normalizaci, evidenci a diagnostické vyhodnocení |

První integrační cíl je `flipctl-slint/docs/apps.md` a Python Runtime (`provides = "py"`). Jeho `.fap.py` API je veřejně dokumentované, ale větev `dev` se mění; před releasem ověřit konkrétní commit. `apps/Test Tools/ethernet-tester.fap.py` je experimentální test nástroj s nedokumentovanými RTL8211F registry a známou kolizí s kernel MII pollingem; nekopírovat jej ani nepovažovat za bezpečný kabelový tester.

Stavy upstream funkce se vždy zapisují jednou z kategorií: **zdokumentovaný záměr**, **prototyp**, **sloučený kód**, **ověřeno na cílovém HW**, **vydáno**. Pouhé uvedení na produktové stránce neznamená hotovou funkci.


### 6.6 Rozšíření funkčního plánu: Proxmark5 a volitelný CAN modul

Podrobné UX, datové kontrakty, závislosti, bezpečnost a akceptační kritéria jsou v [docs/functional-specification.md](docs/functional-specification.md). Rozšíření nemění prioritu drátového MVP.

| ID | Funkce | Rozsah | Fáze / stav |
|---|---|---|---|
| F-45 | Proxmark5 connection/orchestration | USB jako základ; volitelné Wi-Fi/BLE transporty přes oficiální Iceman client a BWM | M7 / Verify first |
| F-46 | PM5 Wi-Fi transport | BWM STA + TCP klient; izolovaná důvěryhodná síť, bez WAN vystavení | M7 / Verify first |
| F-47 | PM5 BLE transport | BWM BLE GATT; ověřit passkey/bonding a nativní Linux transport nebo bridge | M7 / Verify first |
| F-48 | PM5 status/battery | Read-only firmware, BWM, baterie, napájení a wireless status | M7 / Build after transport |
| F-49 | Authorized LF/HF workflow | Identifikace/čtení vlastních a laboratorních tagů; UHF až po ověření | M7 / Verify first |
| F-50 | RFID capture/analysis/export | Časově a velikostně omezený capture a lokální analýza; citlivé dumpy chráněné | M7 / Verify first |
| F-51 | Test-tag write/verify/emulation | Pouze prázdná/testovací média; vypnuto do samostatné bezpečnostní a HW validace | M7 / Deferred |
| F-52 | Read-only automotive CAN capture | Samostatný experiment s externím transceiverem, pouze RX a black-box evidence | M7 / Deferred |

**PM5 bezdrátová omezení:** oficiální Iceman dokumentace popisuje BWM, Wi-Fi STA/TCP a BLE. V dokumentaci je však rozdíl v popisu BLE zabezpečení: usage guide uvádí plaintext/no bonding, zatímco aktuální command reference uvádí BLE pairing/passkey příkazy. Do ověření konkrétní verze je bezdrátové ovládání označeno Verify first. Wi-Fi TCP se nesmí vystavit do internetu; vyžaduje izolovanou LAN/VLAN a firewall. Nikdy automaticky neflashovat PM5/BWM firmware z naší aplikace.

**Tesla CAN inspirace:** z repozitáře flipper-tesla-fsd přebírat pouze principy read-only capture, timestampingu, capability detection, test fixture a black-box evidence. Nezařazovat FSD unlock, nag suppression, frame injection/replay, změny řízení/pohonu ani zápisy do ECU. F-52 je oddělený M7 experiment a není součástí síťového MVP.
