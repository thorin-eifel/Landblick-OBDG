"""Pegel NRW (OpenHygon des LANUK) gegen gekürzte echte Dateien vom 25.10.2026.

Echte Fixtures: nrw_pegel_stationen_real_gekuerzt.txt (sechs Stationen der landesweiten Liste), nrw_pegel_messwerte_real_gekuerzt.zip
(Werte dieser Stationen ab 23.10.), nrw_pegel_meta_real_gekuerzt.zip (Gewässernamen, Windows-1252 wie das Original).
SYNTHETISCH sind die im Test markierten Abwandlungen. Die Tests laufen auf der Prüffläche um Irrel (conftest); Lippstadt liegt draußen.
"""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone

import httpx
import pytest

from app.collectors import load_collector_class, nrw_pegel
from app.collectors.base import SourceError
from conftest import FIX, make_client

NOW = datetime(2026, 10, 25, 5, 0, tzinfo=timezone.utc)


def _stations():
    waters = nrw_pegel.parse_waters((FIX / "nrw_pegel_meta_real_gekuerzt.zip").read_bytes())
    return nrw_pegel.parse_stations((FIX / "nrw_pegel_stationen_real_gekuerzt.txt").read_text(encoding="utf-8"), waters)


def test_stations_in_region_with_water_and_levels():
    st = _stations()
    names = {s.name for s in st.values()}
    assert {"Monschau", "KornelimuensterW", "Mulartshuette"} <= names and "Lippstadt2" not in names
    mon = next(s for s in st.values() if s.name == "Monschau")
    assert mon.water == "Rur" and mon.meta["infostufen_cm"] == [120.0, 145.0, 170.0] and mon.meta["land"] == "DE-NW"


def test_meta_file_is_windows_1252():
    waters = nrw_pegel.parse_waters((FIX / "nrw_pegel_meta_real_gekuerzt.zip").read_bytes())
    assert waters["Fiestel"] == "Große Aue (Aue)"          # ß kommt richtig an, nicht als Ersatzzeichen


def test_values_last_48h_utc_and_state_only_on_last_value():
    st = _stations()
    meas = nrw_pegel.parse_values((FIX / "nrw_pegel_messwerte_real_gekuerzt.zip").read_bytes(), st, NOW)
    assert meas and all(m.unit == "cm" and m.parameter == "W" and m.ts.tzinfo == timezone.utc for m in meas)
    assert all((NOW - m.ts).total_seconds() <= 48 * 3600 for m in meas)
    assert {m.station_id for m in meas} <= set(st)
    per = {}
    for m in meas:
        per.setdefault(m.station_id, []).append(m)
    for ms in per.values():
        last = max(ms, key=lambda m: m.ts)
        assert all(m.state is None for m in ms if m is not last)


def test_stufe_thresholds():
    assert nrw_pegel.stufe(119.9, [120.0, 145.0, 170.0]) is None
    assert nrw_pegel.stufe(150.0, [120.0, 145.0, 170.0]) == "Informationsstufe 2"
    assert nrw_pegel.stufe(500.0, [None, None, None]) is None


def test_schema_change_fails_loudly_SYNTHETISCH():
    with pytest.raises(SourceError):
        nrw_pegel.parse_stations("name;lat\nX;1\n", {})
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("messwerte.txt", "nummer;zeit;wert\n1;2;3\n")
    with pytest.raises(SourceError):
        nrw_pegel.parse_values(b.getvalue(), _stations(), NOW)
    with pytest.raises(SourceError):
        nrw_pegel.parse_values(b"kein zip", _stations(), NOW)


async def test_collector_end_to_end_and_gewaesser_payload(registry, storage, settings, monkeypatch):
    from app import payloads
    files = {nrw_pegel.STATIONS_FILE: (FIX / "nrw_pegel_stationen_real_gekuerzt.txt").read_bytes(),
             nrw_pegel.VALUES_FILE: (FIX / "nrw_pegel_messwerte_real_gekuerzt.zip").read_bytes(),
             nrw_pegel.META_FILE: (FIX / "nrw_pegel_meta_real_gekuerzt.zip").read_bytes()}
    monkeypatch.setattr(nrw_pegel, "utcnow", lambda: NOW)
    client, router = make_client(lambda req: httpx.Response(200, content=files[req.url.path.rsplit("/", 1)[-1]]))
    entry = registry.get("nrw_pegel")
    c = load_collector_class(entry.collector)(entry, storage, client, settings, backoff_base_s=0.0)
    ok = await c.run_once()
    await client.aclose()
    assert ok and len(router.calls) == 3
    rows = storage._query("SELECT name, water FROM stations WHERE source_id='nrw_pegel'")  # noqa: SLF001
    assert ("Monschau", "Rur") in {(r["name"], r["water"]) for r in rows}
    assert "nrw_pegel" in [s["id"] for s in payloads.gewaesser_payload(storage, registry)["sources"]]


async def test_collector_meta_down_keeps_values_SYNTHETISCH(registry, storage, settings, monkeypatch):
    def h(req):
        name = req.url.path.rsplit("/", 1)[-1]
        if name == nrw_pegel.META_FILE:
            return httpx.Response(503)
        return httpx.Response(200, content=(FIX / ("nrw_pegel_stationen_real_gekuerzt.txt" if name == nrw_pegel.STATIONS_FILE
                                                   else "nrw_pegel_messwerte_real_gekuerzt.zip")).read_bytes())
    monkeypatch.setattr(nrw_pegel, "utcnow", lambda: NOW)
    client, _ = make_client(h)
    entry = registry.get("nrw_pegel")
    c = load_collector_class(entry.collector)(entry, storage, client, settings, backoff_base_s=0.0)
    assert await c.run_once()
    await client.aclose()
    assert storage._query("SELECT 1 FROM stations WHERE source_id='nrw_pegel' AND water IS NULL")  # noqa: SLF001
