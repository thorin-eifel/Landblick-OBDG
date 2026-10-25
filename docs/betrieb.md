# Landblick - OBDG

> **Hinweis:** Diese Betriebsanleitung stammt aus Landblick-RLP. Abläufe, Befehle und Desktop-App gelten unverändert; Angaben zu Fläche, Kartengrößen und Kacheln beziehen sich noch auf Rheinland-Pfalz und werden in O2 bis O6 angepasst (`docs/obdg/plan.md`). Die Fläche kommt aus `region.yaml`.

Lagebild aus offenen Daten für die Deutschsprachige Gemeinschaft Belgiens und 20 km rundum: Warnungen, Verkehr, Pegel, Wetter. Kein Tracking, keine US-Cloud, kein Überwachungswerkzeug: gespeichert werden Orte, Zeiten und Zahlen, keine Personen. Kein amtliches Warnsystem, kein Ersatz für BE-Alert, NINA oder die Leitstelle.

## Wie es läuft (lokal, ohne Server)

Alles läuft auf dem Rechner, auf dem die App steht. Nach außen gehen nur die Abrufe laut Quellenregister:

```
Quellen → Collector → Geo-Filter → SQLite → Export → JSON-Dateien → lokaler Dienst (127.0.0.1)
                                                                          ▲
                                                           Oberfläche holt Dateien, rechnet
                                                           Zeitfenster und Alter selbst
```

Zwei Wege, dieselbe Oberfläche: die Desktop-App (`desktop/`, Tauri-Hülle um `app/desktop.py`) oder eine Installation auf einem Dauerläufer (`install.py`, Zeitplaner plus `tools/serve-local.py`). Beide brauchen Python 3.11+ und Internet. Steht der Sammelzyklus, bleibt die Oberfläche stehen und sagt es: Sie rechnet Alter und Zustand gegen die eigene Uhr und zeigt „Datenstand veraltet“, sobald der Export älter als 20 Minuten ist.

## Schnellstart

```bash
# Sammelstelle einrichten
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q && node --test tests/js/rules.test.mjs     # 60 + 4 Tests
cp .env.example .env && chmod 600 .env                         # LANDBLICK_CONTACT eintragen

# Lokal ansehen
python -m app.collect --once               # alle Quellen einmal
python -m app.export                       # schreibt web/data/*.json, manifest.json, start.json und z/<x>_<y>/ (Zellen, siehe docs/obdg/plan.md (früher r4-export.md)
python tools/serve-local.py --dir web      # → http://127.0.0.1:8080 (versteht Range, http.server nicht)

# Dauerbetrieb auf einem Rechner, der durchläuft
python install.py --kontakt mail@example.org   # Zeitplaner, lokaler Webserver, Sicherung, Gesundheitsprüfung
python tools/zyklus.py                         # ein Durchlauf von Hand: abrufen (nur Fälliges) → exportieren
```

## Aufbau

| Datei / Ordner | Inhalt |
|---|---|
| `sources.yaml` | Quellenregister. Ohne Eintrag läuft kein Collector. Speist die Seite „Quellen und Lizenzen“. |
| `app/collectors/` | `nina`, `dwd_warnungen`, `brightsky`, `pegelonline`, `autobahn`, Basisklasse `base.py` (Retry, Backoff, Circuit Breaker) |
| `app/collect.py` | Runner: `--once`, `--due` (nur Fälliges, für Cron), `--only`, `--healthcheck` |
| `app/export.py`, `app/payloads.py` | Datenbank → `meta, events, gewaesser, wetter, status, sources` als JSON |
| `web/` | Die Seite: `index.html`, `status.html`, `quellen.html`, `js/`, `css/`, `geo/`, `vendor/maplibre-gl/` |
| `web/js/rules.js` | Zeitfenster und Quellenzustand, rechnen im Browser gegen die aktuelle Uhr |
| `desktop/` | Tauri-Hülle um den lokalen Dienst `app/desktop.py` |
| `tools/` | `zyklus.py`, `serve-local.py`, `backup.py`, `build_orientation.py` (Kreisgrenzen für die Karte) |
| `tests/` | Python-Tests, `tests/js/` (Node), `fixtures/` mit echten Antworten |

Der Sammelzyklus liest aus dem Netz und schreibt in seine Datenbank und den Exportordner, sonst nichts. Der lokale Dienst liefert die Seite und die fertigen JSON-Dateien aus, an 127.0.0.1 und sonst nirgends.

## Das Quellenregister (`sources.yaml`)

Pflichtfelder je Quelle: `id, name, betreiber, url, lizenz, namensnennung, intervall, ratenlimit, auth, geo_bezug, datenschutz_risiko, aktiv, zuletzt_geprüft, collector`. Dazu `params`, `lizenz_geprueft` und optional `erstlauf` (`spaeter` für große, langsame Abfragen: die Desktop-App holt sie erst nach dem ersten Export im Hintergrund; derzeit die fünf OSM-Quellen). Steht dort `false`, wurde der Endpunkt live getestet, der Lizenztext aber noch nicht an der Primärquelle bestätigt. Die Seite „Quellen und Lizenzen“ zeigt das offen an. **Vor dem öffentlichen Start muss jede Zeile auf `true`.**

Neue Quelle: erst Nutzungsbedingungen, Lizenz und Ratenlimit klären, dann Registereintrag, dann Collector (Vorlage: `pegelonline.py`), Fixture mit echter Antwort, Test.

## Ereignisse und Messwerte

Ereignisse (Warnung, Verkehr, Verkehrslage, Flug) tragen `source_id, type, title, summary, severity, confidence, geometry, region_tag, valid_from, valid_to, fetched_at, raw_ref, ai_generated, model` und optional `attrs` (Art, Verzögerung, Tempo, Kurs; nie Kennungen). Messreihen (Pegel, Wetter) liegen in eigenen Tabellen. Schweregrade: `info, notice, warning, critical`; `critical` (rot) gibt es nur bei CAP `Severe`/`Extreme`.

Snapshot-Semantik: Ein Collector liefert die vollständige aktive Menge seiner Quelle, was fehlt, wird inaktiv. Nur bei **vollständigem** Abruf. Ein halber Abruf (eine Region oder Autobahn nicht erreichbar) schreibt, räumt aber nichts ab.

Zeitfenster („Jetzt“, 24 Std., 7 Tage): Der Export liefert die Obermenge für 7 Tage, der Browser filtert. Die Regel steht zweimal (`app/db.py`, `web/js/rules.js`), beide sind getestet.

## Betrieb

### Runbook: „Collector kaputt“

1. `https://<domain>/status.html` öffnen: Zustand, letzter Erfolg, Fehler in Folge, Fehlertext, letzte Läufe. Steht dort „Export erzeugt vor … Std.“ in Orange, liegt das Problem bei der Sammelstelle oder beim Upload, nicht bei einer Quelle.
2. Auf der Sammelstelle: `python tools/gesundheit.py` zeigt, welche Quelle in welcher Region betroffen ist. Dann `tail -n 100 /var/log/landblick-cycle.log` (systemd: `journalctl -u landblick-cycle -n 100`). Details einer Quelle: `.venv/bin/python -m app.collect --once --only <id> --log-level DEBUG`.
3. Häufige Ursachen:
   - **HTTP 4xx**: Endpunkt oder Parameter geändert. Doku des Betreibers lesen, Fixture neu aufnehmen, Collector anpassen.
   - **„Schlüssel … fehlt“ / „ohne 'features'“**: Schema geändert. Der Collector rät nicht, er meldet. Fixture ersetzen, Test rot sehen, dann fixen.
   - **Timeout, 5xx, 429**: Quelle down oder drosselt. Retry mit Backoff läuft, nach 5 Fehlläufen pausiert der Collector 15 Minuten (Circuit Breaker). Abwarten oder Intervall erhöhen.
4. Quelle vorübergehend abschalten: `aktiv: false` in `sources.yaml`.

Bei Ausfall bleibt die Seite stehen: „Quelle nicht erreichbar seit …“, die letzten guten Daten sind sichtbar und als veraltet markiert (Chaos-Test in `tests/test_payloads_export.py`).

### Gesundheitsprüfung

`python tools/gesundheit.py` fasst den Zustand in einer Zeile pro Region zusammen und endet mit einem Nagios-Exit-Code: 0 ok, 1 Warnung, 2 kritisch, 3 Prüfung selbst kaputt. Die Zustände je Quelle kommen aus derselben Regel wie die Statusseite (`app/payloads.py`, gespiegelt in `web/js/rules.js`). Region ist der `region_tag` der aktiven Ereignisse einer Quelle; Quellen ohne aktive Ereignisse stehen unter „ohne“. Kritisch ist es, wenn die Datenbank oder der Export fehlt, der Export älter als 60 Minuten ist oder mindestens die Hälfte der Quellen ausgefallen ist. `--json` liefert dasselbe maschinenlesbar, die Schwellen stehen im Kopf des Skripts. Das Skript schreibt nichts.

### Zeitplan

Den Zeitplan legt `install.py` an: Aufgabenplanung unter Windows, launchd auf dem Mac, systemd auf Linux. Kein Docker.

systemd auf Linux, einmalig (`--system` legt die Units systemweit an, sonst auf Benutzerebene):

```
sudo python install.py --kontakt mail@example.org --system
systemctl list-timers 'de.thorin.landblick-*'
journalctl -u de.thorin.landblick-zyklus -n 50
```

Der Zyklus läuft alle fünf Minuten, die Sicherung um 03:15 (mit Rückspielprobe), die Gesundheitsprüfung alle zehn Minuten. Die Units laufen ohne Rechte außer Schreiben in `data/` und `web/data`. Schlägt die Gesundheitsprüfung mit „kritisch“ an, steht die Unit in `systemctl --failed`; eine Benachrichtigung hängt man bei Bedarf per `OnFailure=` an.

### Backup

`tools/backup.py` sichert die Datenbank der Sammelstelle (Online-Backup, Integritätsprüfung, 14 Stück, täglich 03:15). Zu jeder Sicherung liegt eine `.sqlite.json` mit SHA-256, Größe und Zeilenzahl je Tabelle.

Wiederherstellungstest: `python tools/backup.py --verify` spielt die neueste Sicherung in einen Wegwerf-Ordner zurück, prüft Prüfsumme, `PRAGMA integrity_check`, die Zeilenzahlen gegen die Prüfsummendatei und ob die Anwendungsschicht die Kopie lesen kann. Der Test läuft nach jeder Sicherung mit und kippt bei jeder Abweichung. Das ersetzt nicht die Probe von Hand vor dem Livegang: einmal wirklich zurückspielen, `python -m app.export` laufen lassen, Seite ansehen.

Wiederherstellen im Ernstfall: Zyklus pausieren (Timer stoppen oder `launchctl bootout`), neueste Sicherung als `data/landblick.sqlite` zurückkopieren (alte `-wal`/`-shm`-Dateien daneben löschen), `python tools/backup.py --verify` zur Kontrolle, Zyklus wieder starten.

### Chaos-Tests

Was automatisch geprüft wird (`tests/test_betrieb.py`, `tests/test_payloads_export.py`, `tests/test_ausfall_alle_quellen.py`): eine Quelle fällt aus, die Hälfte fällt aus, alle fallen aus, das Netz antwortet mit 503, Zeitüberschreitung, HTML statt Daten oder leerem JSON; der Export bleibt lesbar, die Statusseite zeigt „down“, nichts Altes wird gelöscht. Platte voll beim Export: Temp-Dateien werden weggeräumt, Manifest und alte Dateien bleiben unverändert, der nächste Lauf heilt. Zeitumstellung (29.03. und 25.10.2026, jeweils 01:00 UTC): Zeitfenster und Alter rechnen in UTC, Python und JavaScript haben dieselben Tests.

Von Hand, vor jeder Vorführung: eine wichtige Quelle in `sources.yaml` auf `aktiv: false`, Zyklus laufen lassen, Karte ansehen. Erwartet wird die Kachel „Quelle nicht erreichbar seit …“, der Rest bleibt stehen.

### Updates

Alle Abhängigkeiten sind gepinnt (`requirements.txt`, `requirements-dev.txt`, ein Test prüft das). CI führt `pip-audit` für beide Dateien und `npm audit --audit-level=high` für `desktop/` aus. Rhythmus: einmal im Monat `pip-audit` lokal, Treffer sofort, sonst gesammelt. Ablauf pro Paket: Pin in der Datei ändern, `pytest` und `node --test tests/js/*.test.mjs` laufen lassen, Branch, Pull Request. Nie mehrere Hauptversionen auf einmal. MapLibre liegt unter `web/vendor/` (Version 6.11.2, BSD-3-Clause, Dateiendung auf `.js` geändert, siehe `README.txt` dort); Updates dort von Hand und mit Blick auf die Layer-Ausdrücke (zoom-Interpolation, siehe `web/js/lage/abfluss.js`).

### Dauerlauf (R6)

Gemessen wird nicht geschätzt: `tools/dauerlauf.py sample` hängt alle zehn Minuten eine Probe (Gesundheitszustand, Problemquellen, Exportalter) an `data/dauerlauf.jsonl` (launchd: `de.thorin.landblick-dauerlauf`). Jeder Eingriff von Hand wird mit `tools/dauerlauf.py note "…"` vermerkt, auch ein Neustart. Nach sieben Tagen erzeugt `tools/dauerlauf.py report --out docs/obdg/o6-bericht.md` den Bericht: Laufzeit, Anteile OK/Warnung/kritisch, Pausen, längste Störung je Quelle, Vermerke. Bestanden heißt: mindestens sieben Tage, keine Pause über 30 Minuten, kein Vermerk. Die Vorlage und die Reihenfolge stehen in `docs/obdg/plan.md (O6)`. Schläft der Mac, entsteht eine Pause; für den Dauerlauf Ruhezustand abschalten (`caffeinate -s` oder Energiesparen-Einstellung).

## Datenschutz und Sicherheit in Kürze

- Keine personenbezogenen Daten. Externe Texte werden beim Sammeln bereinigt (`app/sanitize.py`), das Frontend setzt sie nur per `textContent`. Ein Test prüft, dass keine Kontaktadresse oder Zugangsdaten in den Exportdateien landen.
- CSP ohne `unsafe-inline`, keine Drittanbieter-Anfragen (per Browsertest geprüft), keine Cookies, keine Speicherung der Ansicht, kein `eval`.
- Keine Zugriffsprotokolle eines Hosters: der lokale Dienst hört nur auf 127.0.0.1, zwischen Oberfläche und Daten steht niemand.
- Sammelstelle: keine Zugangsdaten im Code, `.env` mit Rechten 600 und in `.gitignore`. Für den Upload ein eigener SFTP-Zugang, der nur auf den Zielordner beschränkt ist.
- Entwürfe: `docs/dsfa-entwurf.md`; „Datenschutz“ und „Impressum“ sind Platzhalter bis zur rechtlichen Endabnahme.

## Was in Phase 1 nicht funktioniert oder offen ist

1. **Lizenzen nicht bestätigt.** Alle zwölf Quellen laufen, kein Lizenztext ist an der Primärquelle geprüft (`lizenz_geprueft: false`). NINA und Autobahn-API nennen in ihrer OpenAPI-Beschreibung keine Datenlizenz. Am heikelsten ist `hochwasser_rlp`: Die JSON-Schnittstelle der Seite hochwasser.rlp.de ist nicht als offene API dokumentiert und trägt keine Lizenzangabe. Vor jeder öffentlichen Nutzung beim Landesamt für Umwelt RLP anfragen; solange bleibt es ein interner Demo-Betrieb.
2. **DWD-Warnungen nur gegen Doku gebaut.** Am Testtag lag bundesweit keine Warnung vor, die Fixture `dwd_wfs_SYNTHETISCH_landkreise.json` ist nachgebaut. Beim ersten echten Warnfall Feldnamen prüfen und durch eine echte Aufnahme ersetzen. Verifiziert: Endpunkt, Layer, BBox-Achsenreihenfolge (lon,lat; lat,lon liefert leere Antworten).
3. **Kein Server-Push.** Die Seite holt die Dateien alle 60 Sekunden. Die Aktualität ist damit höchstens so gut wie der Zyklustakt (5 Minuten) plus Abrufintervall der Quelle.
4. **Keine Basiskarte.** Radius, Kreisgrenzen (DWD), Orte, Ereignisse. Luxemburg und Belgien haben keine Grenzen. Eigene Tiles folgen in Phase 2 (PMTiles-Datei, Teilabrufe).
5. **Pegel aus zwei Quellen.** PEGELONLINE (WSV: Mosel, Saar) und die Hochwasservorhersagezentrale RLP (Prüm, Kyll, Sauer, Our, Nebengewässer; WSA-Stellen werden dort verworfen, damit nichts doppelt steht). Eigene Hochwasserstufen gibt es nicht; angezeigt wird der Zustand laut Legende der jeweiligen Quelle. Die Luxemburger Pegel kommen nur soweit, wie die RLP-Seite sie führt.
6. **Baustellen-Zeiträume** stehen nur als Fließtext in der Autobahn-API. Der erste Termin wird per Muster gelesen, sonst bleibt der Beginn leer und der Eintrag „(geplant)“.
7. **Öffentliche Bright-Sky-Instanz** im Dauerbetrieb ist unhöflich. Eigene Instanz in Phase 2.
8. **Der Sammelzyklus ist ein Einzelpunkt.** Steht er, wird die Seite ehrlich veraltet, aber nicht aktueller. Überwachung läuft über `--healthcheck`.
9. **7-Tage-Dauerlauf** (Definition of Done) steht aus.
10. **Offene Punkte aus Abschnitt 12** der Projektanweisung (Name, Quellenpflege, Luxemburg) sind weiter offen. Hosting entfällt: die App läuft lokal. „GPU“ entfällt, solange die lokalen Modelle (Phase 3) nicht kommen.

## Installation auf einem Dauerläufer (Windows, Linux, macOS)

Ein Skript richtet die Sammelstelle auf einem Rechner ein, der durchläuft: `install.ps1` (Windows), `install.sh` (Linux, macOS), beide rufen `install.py` auf. Voraussetzung ist Python 3.11 oder neuer (getestet: 3.11; unter Windows 3.12 empfohlen, bei 3.13 und neuer vorher prüfen, ob alle gepinnten Pakete Räder haben) und der Ordner dieses Repositorys.

```
# Windows (PowerShell, normale Rechte genügen)
powershell -ExecutionPolicy Bypass -File install.ps1 -Kontakt name@example.org -Dauerlauf -RuhezustandAus
# Linux / macOS
./install.sh --kontakt name@example.org --dauerlauf
# Zustand, Entfernen
powershell -File install.ps1 -Status          ./install.sh --status
powershell -File install.ps1 -Deinstall       ./install.sh --deinstall
```

Was passiert, der Reihe nach: `.venv` anlegen und `requirements.txt` installieren; `.env` aus der Vorlage schreiben (Kontakt-Mail für den User-Agent ist Pflicht, die Adresse aus der Vorlage wird nie übernommen); optional die Basiskarte holen (`--karte voll`, rund 1,5 GB von build.protomaps.com, die pmtiles-CLI wird nach Rückfrage geladen, der Lauf ist wiederaufnehmbar); erste Datensammlung und Export (`tools/zyklus.py --erst`: jede Quelle einmal, die langsamen kommen mit dem Zeitplan); Jobs anlegen; prüfen, ob der Webserver antwortet. Quellen mit Zugangsdaten (z. B. Tankerkönig, NASA FIRMS) bleiben ohne Schlüssel in `.env` im Zustand „ausgefallen“; das ist gewollt und steht in der Gesundheitsprüfung.

| Job | Takt | Aufgabe |
|---|---|---|
| zyklus | alle 5 Minuten | fällige Quellen abrufen, exportieren (`tools/zyklus.py`) |
| spaet | alle 30 Minuten | langsame Quellen (große Abfragen), bis 3 Stunden Laufzeit |
| backup | täglich 03:15 | Datenbank sichern, Rückspieltest (`tools/backup.py --keep 14 --verify-after`) |
| health | alle 10 Minuten | Gesundheitsprüfung (`tools/gesundheit.py`) |
| web | dauerhaft | lokaler Webserver auf `--bind`:`--port` (Standard 127.0.0.1:8080) |
| live | dauerhaft | Luftverkehr in kurzem Takt (mit `--ohne-live` aus) |
| dauerlauf | alle 10 Minuten | Probe für das R6-Protokoll (nur mit `--dauerlauf`) |

Jeder Job läuft über `tools/lauf.py`: keine Shell-Umleitung, keine Konsolenfenster unter Windows, Ausgabe nach `data/logs/<job>.log` (rotierend, 5 Dateien zu 2 MB), Umlaute stimmen. Zeitplaner: Windows-Aufgabenplanung (Ordner „Landblick“, versteckte Aufgaben, bei Absturz Neustart nach einer Minute, nie zwei Instanzen), systemd (`landblick-*.timer` und `.service`, Benutzerdienste mit `loginctl enable-linger`, mit `--system` unter `/etc/systemd/system`), launchd (`de.thorin.landblick-*`).

**Läuft es ohne Anmeldung?** Standard sind Aufgaben des angemeldeten Benutzers: Windows führt sie nur aus, solange er angemeldet ist (Sperrbildschirm genügt). Für einen echten Dauerläufer ohne Anmeldung: `-System` in einem Administrator-Fenster, die Aufgaben laufen dann als SYSTEM; unter Linux `sudo ./install.sh --system`. Unter macOS laufen LaunchAgents nur bei angemeldetem Benutzer. **Ruhezustand** stoppt jeden Zyklus: `-RuhezustandAus` stellt unter Windows den Standby im Netzbetrieb ab, anderswo nennt der Installer den Befehl.

**Netz:** Der Webserver hat keine Anmeldung. Mit `--bind 0.0.0.0` ist die Seite im lokalen Netz sichtbar, nie ohne Firewall oder Reverse-Proxy ins Internet stellen. Datenschutz und Quellenregister sind unverändert: ausgehend gehen nur die Abrufe laut `sources.yaml` und, wenn gewählt, der Kartenabruf.

### Windows-Test: Checkliste

Der Windows-Teil ist unter Linux nur durch Tests der erzeugten Aufgabendateien abgedeckt (wohlgeformtes XML, Trigger, Pfade mit Leerzeichen), nicht auf echtem Windows gelaufen. Beim ersten Test prüfen und Abweichungen notieren:

1. Installer endet mit „Fertig. Oberfläche: http://127.0.0.1:8080/“, die Seite zeigt Daten (bei `-Karte keine` nur die Weltkarte als Hintergrund).
2. Aufgabenplanung → Ordner „Landblick“ zeigt sieben Aufgaben (ohne `-Dauerlauf` sechs); „Letztes Ergebnis“ 0x0 bei zyklus, spaet, backup; health darf 0x1 (Warnung) zeigen.
3. `data\logs\zyklus.log` bekommt alle fünf Minuten einen Block „[start] … [ende] Code 0“.
4. Beim Start einer Aufgabe blitzt kein Konsolenfenster auf (`pythonw.exe` plus `CREATE_NO_WINDOW`).
5. `python tools\gesundheit.py` und `python tools\backup.py --verify` laufen durch (SQLite-Pfade mit Laufwerksbuchstaben und Leerzeichen sind abgedeckt, auf echtem Windows aber ungeprüft).
6. Nach Neustart ohne Anmeldung (nur mit `-System`) laufen `web` und `live` wieder an.
7. Windows Defender oder Firewall melden etwas: Python im Ordner `.venv` freigeben, Fund notieren (bei PyInstaller-Programmen bekannt, hier nicht zu erwarten).

Bekannte Grenzen: `lauf.py --timeout` greift nur, solange der Befehl Ausgabe schreibt; die harte Grenze setzt der Zeitplaner (ExecutionTimeLimit bzw. TimeoutStartSec). Kartenbau und Landesdaten-Werkzeuge außer `build_region_tiles.py` (Höhenmodell, Gebäude, Abfluss) gehören nicht zum Installer; ihre Ergebnisse (`web/tiles/*.pmtiles`) kopiert man vom Bau-Rechner in `web/tiles/`.

## Dauerläufer auf dem Mac (launchd)

Stand: läuft auf dem Mac des Betreibers, Python 3.11 in `.venv`, Zyklus alle 5 Minuten. Eingerichtet mit `install.py`.

```
launchctl print gui/$(id -u)/de.thorin.landblick-zyklus | grep -E 'state|last exit'
tail -f data/logs/zyklus.log
launchctl bootout gui/$(id -u)/de.thorin.landblick-zyklus      # anhalten
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/de.thorin.landblick-zyklus.plist   # starten
```

Lokale Ansicht: http://127.0.0.1:8080 (Job `de.thorin.landblick-web`, nur localhost).
Fallstricke: Schläft der Mac, steht der Zyklus; die Seite zeigt dann nach 20 Minuten
"Datenstand veraltet".

## Luftverkehr (adsb.lol) und warum keine Schiffe

**Flugzeuge:** Quelle adsb.lol (ODbL 1.0 laut Betreiber, Ratenlimit unveröffentlicht, ein Abruf alle 15 Sekunden in der Live-Schleife, siehe „Live, Stau, Icons“). Die Abfrage sitzt auf der Landesmitte: umschließender Kreis der Region (`query_lat`, `query_lon`, `query_radius_km`, derzeit rund 113 NM, Obergrenze der API 250 NM), danach der Feinfilter auf die Region am Rand. OpenSky ist bewusst draußen: dort braucht jede kommerzielle Stelle, auch bei interner Nutzung, eine Lizenz, und bei dieser Entscheidung war das Projekt noch ein Firmenprojekt. Gespeichert wird nur Position, Höhe, Geschwindigkeit, Kurs und grobe Klasse. Hex-Code, Rufzeichen, Kennzeichen und Typ werden nie geschrieben. Die Ereignis-ID ist ein Hash mit täglich wechselndem Salz (Tabelle `kv_cache`, nicht im Export): innerhalb eines Tages überschreibt der Upsert die Position, es entsteht keine Spur, über Tage lässt sich nichts verknüpfen. Transpondercodes 7500/7600/7700 erscheinen als Hinweis mit Konfidenz 0,4, nicht als Warnung. Die Ebene ist auf der Karte standardmäßig aus. Fixture: `tests/fixtures/adsblol_point_ANONYMISIERT_SYNTHETISCH.json` (echte Struktur, Kennungen ersetzt, Positionen teils erfunden).

**Schiffe: nicht gebaut.** Für Mosel, Saar und Sauer gibt es keine offen lizenzierten Positionsdaten. Inland-AIS der WSV ist nicht öffentlich. aisstream.io nennt keine Nutzungsbedingungen, keinen Umfang für Binnengewässer und keine Zusage zu gewerblicher Nutzung (die Anfragen dazu im Issue-Tracker sind unbeantwortet); außerdem identifiziert die MMSI Schiffe, bei Sportbooten also Halter. Möglich wären: Anfrage an das WSV Trier, ein eigener AIS-Empfänger an der Mosel (dann eigene Daten, keine Lizenzfrage), oder nur Schleusen- und Pegeldaten, die schon da sind.

## Baustellen und Sperrungen RLP (Mobilitätsatlas)

Quelle: WFS `https://maps.mobilitaetsatlas.de/geoserver/ows` (Layer `mwvlw:baustelle`, `mwvlw:verlauf`), derselbe Bestand, den die Karte auf mobilitaetsatlas.de zeigt. Er umfasst Bundes-, Landes-, Kreis- und Gemeindestraßen der Verkehrsbehörden in Rheinland-Pfalz sowie Meldungen aus Luxemburg (`region_tag` LU). Aktualisierung im Dienst alle 10 Minuten, Verzug bis 20 Minuten. Abfrage mit Bounding Box, Feinfilter auf 80 km am Rand.

Entscheidungen: (1) Meldungen der Autobahn GmbH aus diesem Dienst werden verworfen, der Autobahn-Collector liefert sie. (2) Der Verlauf (Linie) ersetzt den Punkt, wo er vorhanden ist. (3) Das Feld `ansprechpartner` (Behörden-Postfächer) wird nie gelesen, im Freitext werden E-Mail-Adressen und Telefonnummern entfernt. (4) Typen: G Vollsperrung und F Fahrtrichtung gesperrt = Warnung, C halbseitig und N Lkw-Sperre = Hinweis, B Einschränkung = Info; `_GEPLANT` bekommt den Zusatz „(geplant)“ im Titel. Umleitungen (`mwvlw:umleitung`) sind noch nicht eingebaut.

Offen: Der Dienst nennt keine Lizenz (Capabilities ohne Fees/AccessConstraints, die Erläuterung ebenfalls). Anfrage an das Mobilitätsatlas-Team, Referat 8702 im Ministerium: mobilitaetsatlas@rlp.de. Der Betreiber weist selbst darauf hin, dass nicht alle Kommunen liefern.

Die Presseseite des LBM (lbm.rlp.de/service/presse-aktuelles) ist keine Datenquelle für die Karte: kein Feed, keine Koordinaten, nur Pressetext. Sie taugt später für das Modul „Meldungen“ (nur Titel, Datum, Dienststelle und Link), das ohne Kartenpunkt auskommt. Phase 2.

## Basiskarte (eigene PMTiles)

Die Karte nutzt keine Kacheln von Dritten. Drei Archive aus dem Protomaps-Basiskartenbau (OSM, ODbL), gebaut mit `tools/build_region_tiles.py` für das Polygon aus `region.yaml`:

| Datei | Inhalt | Größe (Build 20261025) |
|---|---|---|
| `web/tiles/region.pmtiles` | ganze Region, Zoom 0 bis 13 | 42 MB |
| `web/tiles/ring.pmtiles` | Zoom 14 außerhalb der Kerne (Gebäudeumrisse, Straßennamen) | 21 MB |
| `web/tiles/core.pmtiles` | Kerne aus `tools/tile_cores.yaml`, Zoom 14 und 15 (Hausnummern) | 37 MB |

Kerne: der Kasten der neun DG-Gemeinden (die DG ist klein genug, um sie ganz in Zoom 15 zu führen), dazu Aachen, Verviers und Malmedy. Der Bau läuft in Stücken und setzt nach einem Abbruch fort; Exit 2 heißt „Befehl wiederholen“. Gemessen in einer Cloud-Sitzung am 25.10.2026: alle drei Stufen in unter einer Minute. Prüfung: `python tools/check_tiles.py --dir web/tiles` (zwölf Orte, Zoom 8, 13, 14, 15; Exit 1 bei Lücke).

Alles auf einmal, samt Höhenkacheln, Geländefaktoren und Suchindex: `tools/kartenbasis.sh` (Kopf des Skripts nennt Parameter und Umgebung). Die pmtiles-CLI holt das Skript selbst, wenn Go installiert ist; sonst von github.com/protomaps/go-pmtiles in `tools/bin/` legen.

Das Frontend liest die Archive im Browser per HTTP Range (pmtiles.js, MapLibre). Fehlt eine Datei oder kann der Server keine Teilabrufe, bleibt die Karte ohne Basis benutzbar und der Kartenhinweis sagt „Basiskarte nicht verfügbar“. Lokal läuft das nur mit `tools/serve-local.py` (versteht Range), nicht mit `python -m http.server`.

Eigene Gebäudeebene (`web/tiles/gebaeude.pmtiles`): In Landblick-RLP kamen dort die amtlichen Hausumringe hinein. Für Ostbelgien gibt es sie noch nicht; Kandidat ist PICC (Wallonien), siehe `docs/obdg/quellen-kandidaten.md`. Ohne Datei zeichnet die Karte die OSM-Gebäude aus Kern und Ring.

### Rechtsklick-Auskunft

Rechtsklick auf die Karte (auf Touchgeräten: Finger lang halten) öffnet ein kleines Fenster mit Höhe (Geländemodell der Karte), Koordinaten (Dezimalgrad, Grad/Minuten/Sekunden, UTM ETRS89; die Zonengrenze 31/32 läuft bei 6° Ost durch die Region), Gebiet und Land. Gebiet heißt Gemeinde in Belgien, Luxemburg und den Niederlanden, Kreis in Deutschland. Die Flächen kommen aus `web/geo/gebiete.geojson` (`tools/build_region.py`, OSM, 226 KB), die der Browser beim ersten Rechtsklick holt. Es gibt keine Anfrage an Dritte. Code: `web/js/lage/kontext.js` und `web/js/ortsinfo.js` (getestet in `tests/js/ortsinfo.test.mjs`). Ortsteile und Teilgemeinden (Eynatten, Elsenborn) fehlen noch.

## Live, Stau, Icons

**Flüge live.** Der lokale Dienst schiebt nichts, und die Oberfläche darf keine Drittserver anfragen (CSP, Datenschutz). „Live“ heißt deshalb: Die Live-Schleife (`python -m app.live`, Job `de.thorin.landblick-live`) holt adsb.lol alle 15 Sekunden (Untergrenze 10 s) und schreibt nur `data/aircraft.json` und `data/status.json`. Die Oberfläche holt `aircraft.json` alle 15 s, solange die Ebene an und der Tab sichtbar ist, und lässt die Flugzeuge dazwischen auf Kurs und Tempo weiterrücken (`advance()` in `rules.js`, rein optisch, nichts wird gemerkt; bei „weniger Bewegung“ im System aus). Der Fünf-Minuten-Zyklus überspringt Quellen mit `params.live` (`--skip-live`; `LANDBLICK_LIVE=0` in `.env` legt sie zurück in den Zyklus). Steht die Schleife, laufen die Punkte nach 90 s ab und die Quelle zeigt „veraltet“. Ratenlimit von adsb.lol ist unveröffentlicht: vor öffentlichem Start nachfragen.

```
python -m app.live --once             # ein Durchlauf zum Testen
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/de.thorin.landblick-live.plist
tail -f data/logs/live.log
```

**Stau und zähfließender Verkehr.** Kommt aus derselben Autobahn-API (`warning` mit `abnormalTrafficType`): `QUEUING_TRAFFIC` = Stau, `SLOW_TRAFFIC` = zähfließend, `STATIONARY_TRAFFIC` = Stillstand, dazu Verzögerung (Minuten) und Durchschnittstempo. Eigener Ereignistyp `congestion`, gezeichnet als Linie von Anfang bis Ende der Meldung (gerade Verbindung, nur Näherung des Straßenverlaufs). Stau ab 30 Minuten Verzögerung und Stillstand sind `warning`, gewöhnlicher Stau `notice`, zähfließend `info`. Sie erscheinen nicht im Warnband, das bleibt für NINA/DWD/Pegel. Eine eigene Stufe „Stop-and-go“ kennt die API nicht. Der Autobahn-Lauf kommt jetzt alle 3 Minuten (vorher 10). Grenzen: nur Autobahnen (A1, A48, A60, A64), keine Bundes- und Landesstraßen, kein Luxemburg. Die Kennungen tragen den Vermerk INRIX; das gehört in die Lizenzanfrage an die Autobahn GmbH. Fixture: `tests/fixtures/autobahn_A64_warning_STAU_SYNTHETISCH.json` (echte Struktur, Orte verlegt).

**Icons.** Einzige Quelle: uxwing.com. Die Lizenz erlaubt Nutzung in Websites, auch gewerblich, ohne Namensnennung, mit Änderung; verboten sind Weiterverkauf, Weiterverbreitung und Unterlizenzierung. Darum liegen die SVGs nicht im Repository (`.gitignore`), `tools/fetch_icons.sh` holt sie (Rollenname → uxwing-Name steht im Skript). Die fertige Webseite liefert sie aus, das ist Nutzung in einer Website. Nicht in ein öffentliches Repository oder Paket legen. Im HTML als CSS-Maske (`css/icons.css`, Farbe folgt dem Text), auf der Karte als Bitmap (`js/icons.js`: Plakette in Stufenfarbe, Flugzeug mit Umriss). Fehlen die Dateien, fällt die Karte auf Kreise zurück, der Text trägt die Bedeutung.

## Höhenrelief

Schummerung, Höhenfärbung, Höhenlinien (mit Beschriftung der Hauptlinien) und Höhenanzeige unter dem Zeiger. Datenbasis: Mapzen Terrain Tiles auf AWS Open Data (EU-DEM und SRTM, rund 30 m), Terrarium-Kodierung, Zoom 6 bis 12:

    .venv/bin/python tools/build_dem.py               # 945 Kacheln, 103 MB nach web/tiles/dem/, dazu README.txt und meta.json
    .venv/bin/python tools/build_dem.py --check       # nur zählen

Zoom 12 genügt: ein Bildpunkt misst in Ostbelgien rund 24 m, die Quelle ist rund 30 m fein. Höher wäre hochgerechnet und kostete das Vierfache je Stufe (Zoom 14: 12 972 Kacheln). `meta.json` meldet `maxzoom: 12`, `relief.js` vergrößert darüber selbst. Ein feineres Modell (Relief Wallonie, DGM1 NRW) käme als eigenes Werkzeug; Lizenzen sind offen (`docs/obdg/quellen-kandidaten.md`).

Geländefaktoren für die Windansicht (Talachse, Tal- und Kammstärke) rechnet `tools/build_terrain.py` aus den Höhenkacheln Zoom 10 nach `web/data/terrain.png` und `terrain.json` (zusammen 75 KB).

Die Kacheln liegen nicht im Repository (`.gitignore`). Fehlt `tiles/dem/README.txt`, bleibt die Karte ohne Relief und läuft normal. Höhenlinien rechnet `web/vendor/maplibre-contour` (BSD-3) im Browser in einem Worker; Ziffern kommen aus `web/fonts/` (Noto Sans, OFL). Namensnennung steht auf `quellen.html`. Höhenwerte sind Raster, keine Vermessung.

Die Desktop-App kennt ein Nachladepaket für höhere Reliefstufen (`PAKETE_MANIFEST` in `app/desktop.py`); für Ostbelgien ist es leer und kommt erst mit einem feineren Modell zurück.

Felswände und Hangneigung aus einem 1-m-Geländemodell gab es in Landblick-RLP (`tiles/klippen/`, `tiles/hang/`). Für Ostbelgien fehlen sie; die Karte zeigt die OSM-Klippen. Die Mechanik im Frontend bleibt, bis ein Modell da ist.

## Weitere Quellen (Umwelt)

| Quelle | Collector | Inhalt | Takt |
|---|---|---|---|
| Hochwasservorhersagezentrale RLP | `hochwasser_rlp` | Pegel (89 Messstellen im Radius), Klassen laut Quellenlegende, Ereignis ab HW-Stufe 2 | 15 min |
| BfS ODL | `bfs_odl` | Ortsdosisleistung (Sonden im Radius), Ereignis erst ab eigener Orientierungsschwelle 0,3 / 1,0 µSv/h | 30 min |
| UBA Luftdaten | `uba_luft` | Luftqualitätsindex und PM10, PM2.5, NO2, O3 (RLP/Saarland), Ereignis ab Index 3 | 30 min |
| EMSC | `emsc` | Erdbeben der letzten 7 Tage, ab M 3,0 Hinweis, ab M 4,0 Warnung; Sprengungen werden verworfen | 15 min |
| DWD Radar | `dwd_radar` | Regenradar als Bild, wird auf dem Mac geholt und mit hochgeladen (`radar.png`) | 5 min |
| MeteoLux (Findel) | `meteolux` | Minutenwerte der Station Findel (CC0): Temperatur, Feuchte, Druck, Wind; Wetter-Reiter, Tabelle „Weitere Messungen“ | 10 min |
| MET Norway | `metno` | zweites Vorhersagemodell (CC BY 4.0), 48 h, im Wetter-Diagramm gestrichelt neben DWD | 60 min |
| Sensor.Community | `sensor_community` | Temperatur und Feuchte von Bürgersensoren, nur als 0,1°-Raster-Median aus mindestens 3 Außensensoren, keine Sensor-IDs gespeichert | 10 min |

Lücken, die man wissen muss: Luxemburg und Frankreich (Cattenom) liefern weder BfS noch UBA; „keine Farbe“ im Radar heißt kein Regen ODER außerhalb der Radarreichweite. Die Sonde Biringen (UBA) liefert keine Daten. Pillow (Radarbild) steht in `requirements.txt`; nach dem Update `pip install -r requirements.txt`.
Tests: `tests/test_collectors_umwelt.py`, `tests/test_wetter_quellen.py` (echte gekürzte Antworten, Abwandlungen sind im Test mit SYNTHETISCH markiert).

## Meldungen, Luxemburg, Indizes, Spritpreise, Themenradar

| Quelle | Collector | Inhalt | Takt |
|---|---|---|---|
| Presseportal (Polizei) | `presseportal` | Überschrift, Ort (aus der Datumszeile), Zeit, Link der Dienststellen Trier und Wittlich; Text wird verworfen, Fahndungen und Vermisste nie übernommen | 10 min |
| Trierischer Volksfreund | `rss_volksfreund` | Schlagzeilen der Rubriken Region und Blaulicht, nur mit Ortsname im Radius; Titel und Link | 15 min |
| Pegel Luxemburg (AGE) | `lu_pegel` | 40 Stationen (Sauer, Our, Alzette, Mosel), CC0, im Gewässer-Reiter; keine Warnstufen der Quelle | 15 min |
| CITA Luxemburg | `cita_lu` | Verkehrsmeldungen DATEX II (Unfälle, Baustellen, Hindernisse), CC0 | 5 min |
| DWD Waldbrand/Grasland | `dwd_waldbrand` | Stationsindex Stufe 1 bis 5 (10 nächste Stationen), Ereignis ab Stufe 3, Umwelt-Reiter | 3 h |
| DWD Pollen/UV | `dwd_gesundheit` | Pollenflug Teilregionen 101/102, UV-Index Station Hahn, Umwelt-Reiter | 60 min |
| Tankerkönig | `tankerkoenig` | Spritpreise deutsche Seite (CC BY 4.0), **inaktiv, bis `TANKERKOENIG_API_KEY` in `.env` steht**, dann `aktiv: true` im Register | 15 min |
| Mastodon | `mastodon_themen` | Themenradar: Beiträge je Regions-Hashtag und begleitende Themen, nur Zählungen, Schwelle 3 verschiedene Konten | 60 min |

Ortszuordnung ohne externen Geocoder: `app/geoparse.py` nutzt das Ortsverzeichnis `app/data/orte.json` (OSM, ODbL, gebaut mit `tools/build_gazetteer.py`). Meldungen ohne erkennbaren Ort im Radius werden verworfen, nicht auf einen Kreismittelpunkt geraten. Neue Ausgabedateien: `indizes.json`, `kraftstoff.json`, `themen.json`.

Bewusst nicht eingebunden: Wort.lu (behält sich Text- und Data-Mining ausdrücklich vor), Bluesky (öffentliche Suche verlangt Anmeldung), Telegram (Projektanweisung), Luxemburger Luftqualität und Spritpreise je Tankstelle (kein offener Datensatz gefunden), Copernicus EMS (nur bei konkretem Einsatz). Lizenz von Presseportal, Volksfreund, DWD Pollen/UV und Mastodon ist im Register mit `lizenz_geprueft: false` vermerkt und vor dem öffentlichen Start zu klären.
Tests: `tests/test_quellen_batch2.py`.

## Ostbelgien, Wallonie, Grand Est

| Quelle | Collector | Inhalt | Takt |
|---|---|---|---|
| Hub'eau Hydrométrie | `hubeau_pegel` | Wasserstände Nordlothringen (Mosel, Nied, Orne, Seille), mm zu cm, im Gewässer-Reiter; keine Warnstufen der Quelle; Lizenz nicht gegengelesen | 15 min |
| BRF Ostbelgien | `rss_brf` | Rubrik Regional, nur mit Ort im Radius (Schlagzeile oder Schlagwort); Titel und Link | 15 min |
| MeteoAlarm | `meteoalarm` | Wetterwarnungen BE, FR, LU als Fläche je NUTS-Gebiet (`app/data/nuts_meteoalarm.json`, gebaut mit `tools/build_nuts.py`); nur Stufe, Art, Gebiet, Zeit, Link; Auflagen der Quelle nicht gelesen | 10 min |

Der Radius von 120 km reicht nach Süden bis Metz und Thionville, nach Westen bis Bastogne, Namur bleibt draußen, nach Norden bis Eupen und Aachen, nach Osten bis Koblenz und Bad Kreuznach. Noch nicht eingebunden: SPW Wallonie Hydrometrie, IRCELINE, ATMO Grand Est, IRSN Téléray, Vigicrues (Endpunkte und Lizenzen nicht geprüft). Tests: `tests/test_quellen_batch3.py`.

## Kultur und Geschichte

Der Landmarken-Collector `osm_natur` (Overpass, wöchentlich) liefert neben der Natur jetzt Burgen und Schlösser (`historic=castle|fort|manor`), Ruinen, archäologische Stätten, Klöster sowie historische Gebäude, Stadttore und Türme. Nur benannte Objekte; Gedenkorte (`memorial`, Stolpersteine) fehlen absichtlich, weil sie oft Personen nennen. Auf der Karte gibt es eine eigene Ebene „Kultur und Geschichte" (Zeichen aus Maki, CC0, geholt mit `tools/fetch_icons.sh`). Nach dem Update einmal `tools/fetch_icons.sh` und `python -m app.collect --once --only osm_natur` ausführen.

## Große Bildschirme

Ab 1800 px Breite skaliert die Oberfläche über die Schriftgröße der Wurzel (`app.css`, Abschnitt „Große Bildschirme“): Inhalt in einem Rahmen (`--frame`), Kartenhöhe aus `--map-h`. Geprüft bei 1440 und 3440 px Breite.

## Karte: Aufbau, Straßen, Radar-Sweep

**Layout.** Ab 1001 px Breite füllt die Karte den ganzen Rahmen. Zeitraum, Darstellung, Ereignisse und Geographie (links, einklappbar) und die Liste (rechts) schweben darüber; darunter stehen die Teile untereinander. Kartensteuerung und Höhenlegende weichen den schwebenden Karten aus (`app.css`, letzter Abschnitt).

**Grenzen.** Alle Verwaltungsgrenzen der Kacheln (Staat, Land, Kreis, Gemeinde; `BOUNDS` in `stil.js`) sehen gleich aus: Punktlinie in einer Farbe je Ansicht, Schalter wie bisher je Ebene. Die Grenze der Deutschsprachigen Gemeinschaft ist die einzige Ausnahme: rote Linie, 2 px, darunter fünf graue Linien (je 1 px, Abstand 1,5 bis 5,5 px nach außen, Deckkraft fallend) als Verlauf. Die Kacheln tragen keine Eigenschaft, die die DG von Wallonien trennt; die Linie kommt aus `web/geo/kern.geojson` (OSM-Relation 2425209, auf 20 m vereinfacht, `tools/build_region.py`). Quelle `kern-grenze`, Schalter „Landesgrenzen“. Fehlt die Datei, bleibt die Karte ohne rote Linie.

**Vignette.** Die schwarze Vignette folgt der Grenze der DG: klar bis 20 km außerhalb, danach über 10 km stufenlos (Smoothstep) auf Schwarz. Gebaut mit `python tools/build_vignette.py` aus `web/geo/kern.geojson` (`web/geo/vignette.png` plus `vignette.json`, zusammen rund 20 KB). Die Seite liest daraus auch die Ausblendung für Wind und Regenwellen (`lage/vignette.js`). Fehlt eine der beiden Dateien, nimmt die Karte einen Kreis um `meta.radius_km`.

**Straßen.** Autobahnen, Bundes-/Landstraßen und Anschlüsse (auch Brücken, Tunnel) sind gelborange (`#f6a81c`) mit 1 px schwarzer Kontur. Die Umstellung passiert beim Aufbau des Basiskartenstils (`mainRoad` in `web/js/lage/stil.js`); Grenzlinien des Stils (`boundaries*`) werden nicht gezeichnet.

**Radius und Sweep.** Der 120-km-Kreis ist grün (Fläche 1 % Deckkraft, Rand 2 px voll). Ist die Luftverkehr-Ebene an und mindestens ein Flugzeug aktiv, läuft ein Radarstrahl (6 s je Umlauf, Zeichnung auf einer eigenen Canvas, `web/js/sweep.js`); überstreicht er ein Flugzeug, sendet es einen Ping. Ohne aktive Flugzeuge, bei ausgeblendeter Ebene, verstecktem Tab oder „weniger Bewegung“ im System steht alles still.

**Schweife.** Jedes Flugzeug zieht 200 px Schweif entlang der beobachteten Bahn, nach hinten schwächer. Die Bahn besteht nur aus Positionen, die der Browser in dieser Sitzung gesehen hat (Arbeitsspeicher, höchstens 30 Minuten); sie wird nie gespeichert oder hochgeladen. Neu geladene Seite = Schweife beginnen von vorn.

**Flugzeugklassen.** Der Collector speichert `klass`: `civil`, `mil` (Militär-Kennzeichen der adsb.lol-Datenbank, `dbFlags` Bit 0), `heli` (Kategorie A7) oder `milheli`. Kennzeichen, Hex-Code und Typ bleiben draußen, gespeichert wird nur die Klasse. Darstellung: zivil = dunkles Flugzeug, militärisch = violett im Ring, Hubschrauber = eigenes Symbol (uxwing „helicopter“, Seitenansicht, dreht sich nicht). Die Klasse ist so gut wie die Datenbank von adsb.lol: nicht gemeldete oder nicht erfasste Militärflugzeuge erscheinen als zivil.

### Mitgelieferte Pakete im Installer
`desktop/stage-pakete.sh` kopiert `dem.pmtiles` und `suche_geo.json`, dazu `klippen`, `hang` und `gebaeude`, soweit vorhanden, nach `desktop/src-tauri/pakete/` (nicht im Git). `tauri.conf.json` nimmt den Ordner als Ressource auf, `main.rs` übergibt ihn dem Dienst als `--pack-dir`. Reihenfolge der Suche für `/tiles/`: Datenordner, Installer-Ressource, `web/tiles`. Erlaubt ist so nur Lesen; `/data/` kommt weiter nur aus dem Datenordner, außer `suche_geo.json`. Gesamtgröße ohne Basiskarte für Ostbelgien rund 100 MB (nur Relief und Suchindex). Ablauf: `desktop/build-sidecar.sh` → `desktop/stage-pakete.sh` → `cd desktop && npx tauri build`. Ungetestet auf Windows (Installer wurde noch nicht gebaut).

### Gebäude, Straßenschilder, Beschriftung, Verkehrsfarben

- **Gebäude** bordeaux (`#800020` hell, `#9c2a4b` dunkel), Deckkraft nach Zoom: 40 % bis Zoom 14, linear bis 75 % bei Zoom 17 (`BUILDING_OPACITY` in `web/js/lage/stil.js`). Standardmäßig an. Die Ebene beginnt bei Zoom 13 (nur große Gebäude, die Kacheln führen darunter nicht mehr). Alle Gebäude gibt es ab Kartenzoom 14: der Kern wird mit `tileSize: 256` eingebunden, dadurch gelten die Zoom-15-Kacheln eine Stufe früher. Weiter vorzuziehen (Zoom 13) würde viermal so viele Kacheln je Bild laden; dafür bräuchte es eigene Gebäudekacheln.
- **Autobahnen** blau mit schwarzer Kontur; auf der Strecke Schilder mit der OSM-Nummer (`ref`): A blau/weiß, B gelb, L und K weiß. Nur Nummern bis 8 Zeichen ohne Semikolon; Anschlussstellen tragen kein Schild.
- **Straßennamen** ab Zoom 14 (aus `core.pmtiles` und `ring.pmtiles`; die Region-Kacheln bis Zoom 13 tragen Namen nur an größeren Straßen), **Hausnummern** ab Zoom 16 (Kacheln bis Zoom 15, darüber wird vergrößert). Es sind Kartenbeschriftungen aus OSM, keine Adresssuche und kein Geocoding; die Daten liegen in den Kacheln, nicht in der Datenbank. Wo OSM keine Namen oder Nummern kennt (kleine Weiler), bleibt die Karte leer.
- **Verkehrsmeldungen** in vier Stufen (`trafficLevel` in `rules.js`): gelb Baustelle, orange Behinderung oder Stau, rot langer Stau (ab 30 Min.) oder eine Richtung gesperrt, schwarz Vollsperrung. Die Stufe folgt aus `type`, `severity` und `attrs.sperr` (`voll`/`richtung`, gesetzt von den Collectoren `lbm_baustellen` und `autobahn`); die Liste rechts zeigt weiter die Stufe der Quelle. Schwarze Linien bekommen einen weißen Saum.
- **Detailfeld** rechts lässt sich mit dem Knopf „Details ausblenden“ einklappen; Ebenen, Höhenlegende und Detailfeld haben dasselbe Material (Deckkraft, Unschärfe, Rand, Schatten).
- **Prüfzugang:** mit `#debug` in der Adresse reagiert die Seite auf das Ereignis `landblick-debug` (Auftrag als JSON in `data-debug-in`, Zählwerte in `data-debug-out`). Nur zum Testen, nichts geht nach außen.

## Region neu bauen

Die Fläche steht in `region.yaml` und entsteht aus OpenStreetMap (`tools/fetch_osm_grenzen.py`, dann `tools/build_region.py`, siehe README). Nach einer Änderung der Fläche oder des Puffers neu bauen, in dieser Reihenfolge: `tools/build_vignette.py`, `tools/build_tank_grid.py`, `tools/kartenbasis.sh` (Basiskarte, Höhen, Gelände, Suchindex; vorher `web/tiles/*.pmtiles` löschen), `tools/build_gazetteer.py` (Ortsverzeichnis), `tools/build_nuts.py` (MeteoAlarm-Flächen), danach `tools/check_range.py <URL>` gegen den Server, wenn ausgeliefert wird.

## Suche über alle Namen

Suchfeld oben links in der Karte (Taste `/` oder Strg+K). Alles läuft im Browser, keine Anfrage nach außen. Der Index wird erst beim ersten Fokus geladen.

- `web/data/suche_geo.json` (statisch, 636 KB, 16 409 Einträge, davon 11 648 Straßen): Orte, Straßen, Bäche, Gipfel, Wälder, Schutzgebiete aus unseren Kartenkacheln. Bauen: `python tools/build_search_index.py --rescan` (liest `web/tiles/region.pmtiles` und `core.pmtiles`, Zwischenstand in `data/search_raw.json.gz`; ohne `--rescan` wird der Zwischenstand benutzt). Nach jedem Kachel-Neubau wiederholen.
- `web/data/suche.json` (dynamisch, ca. 1,3 MB): Schulen, Kirchen, Feuerwachen, Brücken, Landmarken, Haltestellen, Routen, Pegel. Entsteht bei `python -m app.export`.
- Format `{"v":1,"t":[Typen],"o":[Orte],"e":[[Name,Typ,Breite*1e4,Länge*1e4,Ort]]}`; `TYPES` in `app/search.py` nur anhängen, nie umsortieren.
- Datenschutz: keine Hausnummern, keine Adressen, keine Personennamen. Reine Zahlennamen werden verworfen. Lizenz: © OpenStreetMap-Mitwirkende (ODbL).
- Test: `python -m pytest tests/test_search.py && node --test tests/js/suche.test.mjs`

Die Karte im Stil des 15. Jahrhunderts hat keine Papiertextur mehr (Foto und Überlagerung entfernt); Farben, Schrift, Windrose und Zeichen bleiben.

## Vegetation und Wasserbewegung

**Vegetation:** `web/js/lage/stil.js` (`LAND`, `LAND_KINDS`) zeichnet 13 Klassen nach Naturfarben (Wald, Wiese, Rasen/Park, Busch, Heide, Acker, Obst, Wein, Kleingarten, Moor, Fels, Sand, Friedhof). Ab Zoom 12 liegen feine Signaturen darüber (`icons.js`, `registerLandPatterns`). Schutzgebiete haben eine gestrichelte grüne Kante. Die Kacheln tragen keinen Blatttyp, Laub-, Nadel- und Mischwald sind daher nicht trennbar (dafür wäre ein OSM-Collector für `leaf_type` nötig).

**Wasserbewegung** (Ebene „Wasserbewegung“, standardmäßig aus, `web/js/fluss.js`): Striche und Pfeile entlang der Gewässerlinien zeigen die Fließrichtung (Digitalisierungsrichtung der OSM-Linien, geprüft an Mosel, Saar, Our, Sûre, Kyll, Prüm, Nims, Alzette, Lieser, Ruwer). Tempo ist eine Klasse (Bach, Fluss, gestaut), kein gemessener Abfluss. `IMPOUNDED` (Mosel, Saar) bewegt sich kaum: staugeregelt. Seen, Teiche und Becken zeigen Wellenzeichen, die mit dem Modellwind (ICON-D2, Kartenmitte) ziehen; bei Flaute oder ohne Windmodell bleibt das Wasser glatt. Flächen ohne Gewässerart gelten als Stillgewässer. Bei `prefers-reduced-motion` stehen die Zeichen still. Tests: `node tests/js/fluss.test.mjs`. Prüfhilfe: `#debug` schreibt Seitenfehler nach `data-debug-err` am `<html>`.

## Licht am Zeiger

Ebene „Licht am Zeiger“ (aus, unter Kartengrundlage; braucht Höhenrelief). `web/js/licht.js` rechnet im Fragment-Shader (WebGL2): Höhenmosaik aus den sichtbaren Terrarium-Kacheln (höchstens 48, Zoom 6 bis 12), Hangneigung per Sobel, Punktlicht über dem Zeiger (Höhe einstellbar), Schatten durch Strahlverfolgung mit weichem Rand (48 Schritte). Ohne Maus gilt die Bildmitte bzw. der letzte Tippunkt. Gilt nur bei Nordausrichtung ohne Neigung. Prüfzugang: `licht:{on,lon,lat,hoehe}` im `#debug`-Auftrag.

## Desktop-App (Tauri, lokal, GPU)

Dieselbe Oberfläche als App für Windows 10+, Linux und macOS. Gezeichnet wird mit dem System-WebView (WebView2, WebKitGTK, WKWebView), WebGL läuft dort auf der GPU. Daten und Karte liegen lokal, es gibt keinen Server und keine US-Cloud.

```
Tauri-Hülle (Rust) ──startet──▶ landblick-core (Python, Sidecar) ──▶ 127.0.0.1:<Port>
                                  ├─ liefert web/ (mit Teilabrufen für PMTiles)
                                  ├─ erster Start: Karte für das ganze Gebiet laden (tools/build_region_tiles.py, pmtiles-CLI)
                                  └─ Sammelzyklus alle 5 Min: app.collect → app.export → <Datenordner>/data
```

Es gibt keine Auswahl eines Mittelpunkts: Das Gebiet steht fest in `region.yaml` (Ostbelgien plus 20 km). Beim ersten Start zeigt `einrichtung.html` nur den Fortschritt, die App lädt die Karte für die ganze Fläche (rund 200 MB mit Höhenmodell, einmalig, wiederaufnehmbar: Stücke in `tiles-work/chunks`, jeder Lauf macht dort weiter) und beginnt zu sammeln. Der Sidecar braucht dafür `shapely` und `pmtiles` (Python) sowie die pmtiles-CLI; ob das gebündelte Programm sie enthält, ist nicht geprüft.

Zugangsdaten in der App: Quellen, die einen Schlüssel oder ein Login brauchen, tragen im Register ein Feld `zugang` (Name der Umgebungsvariable, Art: `schluessel`, `benutzername` oder `passwort`, Bezeichnung). Die Seite „Quellen und Lizenzen“ zeigt in der Desktop-App und auf dem lokalen Webserver (`tools/serve-local.py`, nur auf Loopback) je Quelle Eingabefelder. Die Werte liegen in `zugang.json` im Datenordner (Rechte 600, Klartext, nicht im Schlüsselbund). Die Desktop-App reicht sie als Umgebungsvariable an die Sammler-Kindprozesse; beim lokalen Webserver liegt die Datei in `data/zugang.json` und `app/config.py` liest sie nach der `.env` (`.env` und Shell gehen vor). Langlaufende Prozesse (Livemodul) lesen sie erst nach einem Neustart. Angenommen werden nur Variablen, die im Register stehen. Die Oberfläche erfährt nie einen Wert, nur „gesetzt“. Neue Quelle mit Schlüssel: `zugang` im Register eintragen, der Collector liest die Variable wie bisher. Gilt ab dem nächsten Abruf der Quelle.

Ablauf in der App: Als Hintergrund der Einrichtungsseite dient die mitgelieferte Weltkarte `web/basis/welt.pmtiles` (Zoom 0 bis 5, rund 15 MB, Herkunft in `web/basis/README.txt`). Der Balken zeigt beim Kartenabruf die fertigen Stücke, beim Sammeln „n von m abgerufen, läuft noch: <Name>" (`.collect-progress.json` im Datenordner, nur Quellennamen). Der erste Lauf überspringt die Quellen mit `erstlauf: spaeter`; sobald der erste Export steht, zeigt die App „Bereit", die langsamen Quellen laufen im Hintergrund (`--due`) und erscheinen mit dem nächsten Export (alle 5 Minuten). Spätere Zyklen holen nur noch fällige Quellen (`--due`), nicht mehr jede Quelle bei jedem Zyklus.

```bash
# Dienst allein ausprobieren (ohne Hülle)
python -m app.desktop --data-dir /tmp/landblick-demo --pmtiles tools/bin/pmtiles     # → "LANDBLICK_READY port=N", dann http://127.0.0.1:N/

# App bauen (je Betriebssystem auf diesem System; CI: .github/workflows/desktop.yml)
desktop/build-sidecar.sh && cd desktop && npm install --include=dev && npx tauri build
```

### Windows-Installer

Der Installer (NSIS, eine `Landblick - OBDG_<Version>_x64-setup.exe`, rund 1,8 GB mit Basiskarte, Relief, Hangneigung und Felswänden) wird auf einem Windows-Runner gebaut, nicht lokal: GitHub → Actions → **windows-installer** → *Run workflow*. Die Kachelpakete lädt der Lauf vom Release `kacheln-1` (Eingabe `kacheln_tag`; `keine` baut einen Installer ohne Kacheln, rund 50 MB, der die Karte beim ersten Start holt). Nach der Bauzeit steht er im Lauf unter *Artifacts* (`landblick-windows-installer`, Zip mit der Setup.exe). Ein Tag `windows-v*` startet den Lauf ebenfalls. Lokal auf Windows: `powershell -File desktop\build-sidecar.ps1`, danach `cd desktop; npm install --include=dev; npx tauri build --bundles nsis` (Python 3.11+, Node 24, Rust und die Visual-Studio-Build-Tools nötig).

- **Installation:** pro Benutzer (`currentUser`, ohne Administratorrechte), Deutsch, Eintrag im Startmenü und Deinstallation über „Apps“. Der Installer holt bei Bedarf WebView2 nach (Windows 11 hat es, Windows 10 braucht eine Internetverbindung dafür).
- **Erster Start:** Die App öffnet die Einrichtungsseite, lädt die Karte für das ganze Gebiet (rund 1,5 GB, einmalig, wiederaufnehmbar) und beginnt zu sammeln. Daten und Zugangsdaten liegen in `%APPDATA%\de.thorin.landblick`; Deinstallieren lässt sie stehen (zum Zurücksetzen den Ordner löschen).
- **Wenn etwas klemmt:** `%APPDATA%\de.thorin.landblick\logs\dienst.log` (rotierend, 5 Dateien zu 2 MB). Dort steht die Startzeile mit Version, System und Datenordner, dazu alles, was der Dienst und seine Kindprozesse (`app.collect`, `app.export`) melden. Die App hat unter Windows keine Konsole; ohne diese Datei wäre nichts davon zu sehen. Was einzelne Quellen angeht, steht auch auf der Seite „Status“.
- **Nicht signiert:** Windows SmartScreen meldet „Der Computer wurde durch Windows geschützt“. *Weitere Informationen → Trotzdem ausführen*. Ein Code-Signing-Zertifikat ist offen.
- **Nicht getestet auf echter Hardware:** Der Bau läuft durch, der Rauchtest des Sidecars (`app.region` im gebündelten Programm) ist Teil des Baus; der Lauf der App unter Windows ist beim ersten Test auf dem PC zu prüfen (Windows-Firewall-Abfrage für den lokalen Dienst, Pfade, Antivirus-Fehlalarme bei PyInstaller-Programmen).


Grenzen der ersten Fassung: Suchindex, Gewässernetz, Höhenkacheln und Routen (`web/geo`, `web/tiles/dem`, `tools/build_*.py`) werden über die Werkzeuge in `tools/` für die Landesfläche gebaut, nicht von der App. Quellen für Luxemburg, Rheinland-Pfalz und Ostbelgien liefern nur dort Daten; bundesweite (DWD, NINA, Autobahn, Bright Sky) funktionieren überall in Deutschland. Das Bündeln mit PyInstaller und die Installer sind hier nicht gebaut worden (Sandbox ohne WebKit, nur Linux): erster Build auf Mac, Windows und Linux steht aus.

## Frontend: Zellenbetrieb (ab R5)

Die Seite lädt `data/manifest.json` und `data/start.json` und holt danach nur die Zellen im Bildausschnitt (`data/z/<x>_<y>/<art>.json`, Raster 0,5 Grad). Fehlt das Manifest, läuft sie wie bisher aus den Flachdateien. Code: `web/js/zellen.js` (rein, getestet), `web/js/lage/zellenlauf.js` (Anbindung an Karte und Zustand).

- **Stufen.** Unter Zoom 8 keine Zellen: die Karte zeigt je Rasterzelle eine Zahl (Dichte-Ebene aus `start.json`), das Warnband und die Tabelle stammen aus dem Warnband des Startpakets. Ab Zoom 8 Ereignisse, Pegel und Umweltstationen, ab 9 Kraftstoff, ab 10 Haltestellen, Landmarken und Routen, ab 11 Infrastruktur und Anbau (`KIND_MIN_ZOOM`). Unter Zoom 9 werden nur Meldungen ab Stufe „Hinweis“ gezeichnet, höchstens 1500 (`ebenenBudget`).
- **Rand und Obergrenze.** Ab Zoom 9 wird eine Zelle Rand mitgeladen, höchstens 60 Zellen gleichzeitig, die Bildmitte hat Vorrang. Zellen außerhalb werden verworfen.
- **Änderungen.** Das Manifest trägt je Datei eine Prüfsumme; eine Datei wird nur neu geholt, wenn sie sich geändert hat. Ein Fehler in einer Zelle lässt die übrigen stehen, die Statuszeile neben „Lagekarte“ nennt die Zahl der nicht erreichbaren Dateien (Einzelheiten als Tooltip), nach 30 Sekunden folgt ein neuer Versuch.
- **Alter.** Zellen tragen keine Abrufzeit. `fetched_at`, `source_status` und `age_s` setzt das Frontend beim Zusammenführen aus dem Quellenzustand des Startpakets (`anreichern`).
- **Gebiet.** Land und Landkreis stehen im Ereignisfilter („Filter“). Das Backend schreibt `ars` und `land` an Ereignisse und Messstellen (VG250, `app/export_cells.py`); außerhalb Deutschlands kommt `land` aus dem `region_tag` des Sammlers, ein deutsches Kürzel ohne Kreis bleibt „unbekannt“.
- **Prüfzugang.** `#debug` kennt den Befehl `zellen` (gehaltene Dateien, Fehler, Bytes, Ereignisse) und wartet auf laufende Abrufe.

