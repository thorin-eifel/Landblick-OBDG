"""Pegel Nordrhein-Westfalen (LANUK, Hydrologische Rohdaten „OpenHygon“ des Hochwasserportals NRW).

Quelle:     https://www.opengeodata.nrw.de/produkte/umwelt_klima/wasser/oberflaechengewaesser/hygon/
            OpenHygon-Pegel-Stationen_EPSG4326.txt (Stationen mit Informationsstufen), OpenHygon-Pegel-aktuell_CSV.zip
            (15-Minuten-Werte der letzten sieben Tage), OpenHygon_meta.zip (Gewässernamen)
Betreiber:  Landesamt für Natur, Umwelt und Klima Nordrhein-Westfalen (LANUK)
Lizenz:     Datenlizenz Deutschland – Zero – Version 2.0 (laut OpenGeodata.NRW und open.nrw, gelesen 25.10.2026): Nutzung ohne
            Bedingungen. Wir nennen die Quelle trotzdem.
Intervall:  10 800 s. Das Land erneuert die Dateien einmal täglich gegen 5 Uhr; die Werte sind also bis zu einem Tag alt. Die Seite
            zeigt das Alter je Wert. Hochwasserklassen in Echtzeit kommen weiter aus dem Länderportal (lhp_hochwasser).
Beispiel:   python -m app.collect --once --only nrw_pegel

Ablauf: Stationsliste lesen, auf die Region filtern, Messwerte der Stationen in der Region aus der Zip-Datei holen (nur die letzten
48 Stunden, mehr zeigt die Pegelansicht nicht). Zustand des letzten Werts: Informationsstufe 1 bis 3 des Landes, wenn erreicht.
Ungeprüfte Rohdaten: Lücken und Ausreißer sind möglich. Reine Messwerte, kein Personenbezug.
"""
from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

from .. import geo
from ..models import Measurement, Station, utcnow
from ..sanitize import clean_text
from .base import Collector, CollectResult, SourceError

BASE = "https://www.opengeodata.nrw.de/produkte/umwelt_klima/wasser/oberflaechengewaesser/hygon"
STATIONS_FILE = "OpenHygon-Pegel-Stationen_EPSG4326.txt"
VALUES_FILE = "OpenHygon-Pegel-aktuell_CSV.zip"
META_FILE = "OpenHygon_meta.zip"
KEEP_H = 48
PLAUSIBLE_CM = (-50.0, 2000.0)
MAX_ZIP_BYTES = 50_000_000      # Schutz gegen eine entartete Datei (heute rund 15 MB entpackt)


def _num(s: Any) -> float | None:
    """'110,0' oder '110.0' → 110.0; leer → None."""
    t = str(s or "").strip().replace(",", ".")
    try:
        return float(t) if t else None
    except ValueError:
        return None


def parse_waters(meta_zip: bytes) -> dict[str, str]:
    """Pegelname → Gewässer aus der Metadatei (OpenHygon_Pegel_EPSG25832_ASCII.txt). Fehlt sie, bleibt das Gewässer leer."""
    try:
        with zipfile.ZipFile(io.BytesIO(meta_zip)) as z:
            name = next(n for n in z.namelist() if n.startswith("OpenHygon_Pegel") and n.endswith(".txt"))
            raw = z.read(name)
    except (zipfile.BadZipFile, StopIteration, KeyError):
        return {}
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")   # Stand 2023: Windows-1252, nicht UTF-8
    out = {}
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        n, w = (row.get("Name") or "").strip(), (row.get("Gewaesser") or "").strip()
        if n and w:
            out[n] = w
    return out


def parse_stations(text: str, waters: dict[str, str]) -> dict[str, Station]:
    """Stationsliste → Stationen in der Region, mit Informationsstufen in meta. Reine Funktion."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    need = {"station_latitude", "station_longitude", "station_name", "station_no"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise SourceError("OpenHygon: Stationsliste ohne Pflichtfelder (Schemawechsel?)")
    out: dict[str, Station] = {}
    for row in reader:
        lat, lon = _num(row["station_latitude"]), _num(row["station_longitude"])
        no = (row["station_no"] or "").strip()
        if lat is None or lon is None or not no or not geo.in_region(lat, lon):
            continue
        raw_name = clean_text(row["station_name"], 80) or no
        stufen = [v for v in (_num(row.get(f"LANUV_Info_{i}")) for i in (1, 2, 3))]
        catchment = clean_text(row.get("catchment_name"), 80) or None
        out[no] = Station(source_id="nrw_pegel", station_id=no, name=raw_name.replace("_", " "),
                          water=waters.get(raw_name) or None, lat=round(lat, 5), lon=round(lon, 5),
                          meta={"land": "DE-NW", "einzugsgebiet": catchment, "infostufen_cm": stufen,
                                "mw_cm": _num(row.get("LANUV_MW")), "mhw_cm": _num(row.get("LANUV_MHW"))})
    return out


def stufe(value: float, stufen: list[float | None]) -> str | None:
    """Höchste erreichte Informationsstufe des Landes als Text, sonst None."""
    hit = None
    for i, s in enumerate(stufen, 1):
        if s is not None and value >= s:
            hit = i
    return f"Informationsstufe {hit}" if hit else None


def parse_values(values_zip: bytes, stations: dict[str, Station], now: datetime) -> list[Measurement]:
    """Messwerte der Stationen in der Region aus der Zip-Datei, nur die letzten KEEP_H Stunden. Reine Funktion."""
    try:
        with zipfile.ZipFile(io.BytesIO(values_zip)) as z:
            info = next((i for i in z.infolist() if i.filename.endswith(".txt")), None)
            if info is None:
                raise SourceError("OpenHygon: Messwertdatei fehlt im Archiv")
            if info.file_size > MAX_ZIP_BYTES:
                raise SourceError(f"OpenHygon: Messwertdatei unerwartet groß ({info.file_size} Bytes)")
            text = z.read(info).decode("utf-8-sig", errors="replace")
    except zipfile.BadZipFile as exc:
        raise SourceError("OpenHygon: Archiv beschädigt") from exc
    reader = csv.reader(io.StringIO(text), delimiter=";")
    head = next(reader, None)
    if not head or [h.strip() for h in head[:3]] != ["station_no", "time", "value(cm)"]:
        raise SourceError("OpenHygon: Messwertdatei hat nicht die Spalten station_no;time;value(cm) (Schemawechsel?)")
    since = now - timedelta(hours=KEEP_H)
    last: dict[str, datetime] = {}
    meas: list[Measurement] = []
    for row in reader:
        if len(row) < 3 or row[0] not in stations:
            continue
        try:
            ts = datetime.fromisoformat(row[1]).astimezone(timezone.utc)
            cm = round(float(row[2]), 1)
        except ValueError:
            continue
        if ts < since or not PLAUSIBLE_CM[0] <= cm <= PLAUSIBLE_CM[1]:
            continue
        meas.append(Measurement(source_id="nrw_pegel", station_id=row[0], parameter="W", ts=ts, value=cm, unit="cm"))
        if row[0] not in last or ts > last[row[0]]:
            last[row[0]] = ts
    for m in meas:   # Zustand nur am jeweils letzten Wert, wie bei den anderen Pegelquellen
        if m.ts == last.get(m.station_id):
            m.state = stufe(m.value, stations[m.station_id].meta.get("infostufen_cm") or [])
    return meas


class NrwPegelCollector(Collector):
    async def collect(self) -> CollectResult:
        text = (await self.fetch_bytes(f"{BASE}/{STATIONS_FILE}", timeout=60.0)).decode("utf-8", errors="replace")
        try:
            waters = parse_waters(await self.fetch_bytes(f"{BASE}/{META_FILE}", timeout=60.0))
        except SourceError as exc:
            self.log.warning("Gewässernamen nicht erreichbar: %s", exc)
            waters = {}
        stations = parse_stations(text, waters)
        if not stations:
            raise SourceError("OpenHygon: keine Station in der Region (Schemawechsel oder Region falsch?)")
        meas = parse_values(await self.fetch_bytes(f"{BASE}/{VALUES_FILE}", timeout=120.0), stations, utcnow())
        if not meas:
            raise SourceError("OpenHygon: keine Werte der letzten 48 Stunden für die Region")
        used = {m.station_id for m in meas}
        newest = max(m.ts for m in meas)
        note = f"{len(used)} von {len(stations)} Stationen, {len(meas)} Werte, neuester {newest:%d.%m. %H:%M} UTC (Tagesdatei)"
        return CollectResult(stations=[s for k, s in stations.items() if k in used], measurements=meas, note=note, writes_events=False)


COLLECTOR = NrwPegelCollector
