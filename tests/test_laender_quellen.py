"""Tests der Länder-Quellen: LHP (Pegel, Hochwasserwarnungen), MobiData BW (Baustellen, Verkehrsmeldungen)."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app import geo, region
from app.collectors import load_collector_class
from app.collectors.base import Collector, SourceError
from conftest import FIX, fixture, make_client

ROOT = Path(__file__).resolve().parent.parent


def _make(registry, storage, settings, name, handler, keep_all=True, monkeypatch=None):
    if keep_all and monkeypatch is not None:
        monkeypatch.setattr(Collector, "keep", staticmethod(lambda g: True))
    client, router = make_client(handler)
    entry = registry.get(name)
    c = load_collector_class(entry.collector)(entry, storage, client, settings, backoff_base_s=0.0)
    return c, client, router


def _lhp(stations=None, alerts=None, alerts_status=200):
    def h(req: httpx.Request):
        if req.url.path.endswith("/stations"):
            return stations if stations is not None else fixture("lhp_stations_real_KLASSEN_SYNTHETISCH.json")
        return httpx.Response(alerts_status, json=alerts if alerts is not None else fixture("lhp_alerts_SYNTHETISCH.json"))
    return h


# ------------------------------------------------------------------ LHP
async def test_lhp_pegelklassen_und_warnungen(registry, storage, settings, monkeypatch):
    c, client, router = _make(registry, storage, settings, "lhp_hochwasser", _lhp(), monkeypatch=monkeypatch)
    res = await c.collect()
    await client.aclose()
    q = router.calls[0].url.params
    assert q["format"] == "geojson" and q["states"] == "NW"
    assert router.calls[0].headers["accept"] == "application/geo+json"     # mit application/json liefert der Server eine andere Struktur
    ev = {e.id: e for e in res.events}
    # Pegel: Klasse 0 ergibt kein Ereignis; 1 notice, 2 warning, 3 und 4 critical
    assert {k for k in ev if k.startswith("lhp:")} == {"lhp:BW_105", "lhp:NW_2710080", "lhp:NW_2721390000100", "lhp:HE_23940359"}
    assert ev["lhp:NW_2721390000100"].severity == "notice" and ev["lhp:BW_105"].severity == "warning"
    assert ev["lhp:NW_2710080"].severity == "critical" and ev["lhp:HE_23940359"].severity == "critical"
    p = ev["lhp:BW_105"]
    assert p.type == "flood" and p.region_tag == "DE-BW" and p.geometry["type"] == "Point"
    assert "Datenquelle: www.hochwasserzentralen.de" in p.summary and "Stand 12.10.2026" in p.summary
    assert p.valid_from.isoformat().startswith("2026-10-12T07:00")        # 09:00 Ortszeit (MESZ) = 07:00 UTC
    assert p.raw_ref.startswith("https://www.hvz.baden-wuerttemberg.de")
    # Warnungen: Entwarnung (Klasse 1) ohne Ereignis, Vorwarnung notice, Hochwasser warning, Fläche
    assert {k for k in ev if k.startswith("lhpwarn:")} == {"lhpwarn:BW_901", "lhpwarn:NW_903"}
    assert ev["lhpwarn:BW_901"].severity == "warning" and ev["lhpwarn:NW_903"].severity == "notice"
    assert ev["lhpwarn:BW_901"].geometry["type"] == "Polygon" and ev["lhpwarn:BW_901"].attrs["kind"] == "hochwasserwarnung"
    assert res.complete is True


async def test_lhp_unsichere_felder_werden_bereinigt(registry, storage, settings, monkeypatch):
    c, client, _ = _make(registry, storage, settings, "lhp_hochwasser", _lhp(), monkeypatch=monkeypatch)
    res = await c.collect()
    await client.aclose()
    w = next(e for e in res.events if e.id == "lhpwarn:NW_903")
    assert "<" not in w.title and "javascript" not in (w.raw_ref or "")      # HTML raus, nur https-Links
    assert w.raw_ref.startswith("https://")


async def test_lhp_warnungen_ausfall_laesst_pegel_stehen(registry, storage, settings, monkeypatch):
    c, client, _ = _make(registry, storage, settings, "lhp_hochwasser", _lhp(alerts_status=503), monkeypatch=monkeypatch)
    res = await c.collect()
    await client.aclose()
    assert any(e.id.startswith("lhp:") for e in res.events) and not any(e.id.startswith("lhpwarn:") for e in res.events)
    assert res.complete is False and "Warnungen" in res.note


async def test_lhp_schemaaenderung_ist_fehler(registry, storage, settings, monkeypatch):
    c, client, _ = _make(registry, storage, settings, "lhp_hochwasser", _lhp(stations={"foo": 1}), monkeypatch=monkeypatch)
    with pytest.raises(SourceError):
        await c.collect()
    await client.aclose()


# ------------------------------------------------------------------ BW Baustellen


# ------------------------------------------------------------------ BW Verkehrsmeldungen


def test_register_eintraege_vollstaendig(registry):
    for sid in ("lhp_hochwasser",):
        e = registry.get(sid)
        assert e.aktiv if hasattr(e, "aktiv") else True
        assert e.lizenz_geprueft is False and e.url.startswith("https://") and e.auth == "keine"
