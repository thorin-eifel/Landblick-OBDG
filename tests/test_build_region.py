"""tools/build_region.py: zweite Sprachform der Gebiete (andere_namen, gebiet_meta) und ihr Weg ins Startpaket."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("shapely")
pytest.importorskip("pyproj")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import build_region as b  # noqa: E402


def test_german_form_outside_dg():
    assert b.andere_namen("Waimes", {"name:de": "Weismes", "name:fr": "Waimes"}, "BE-WAL") == {"name_de": "Weismes"}
    assert b.andere_namen("Clervaux", {"name:de": "Clerf"}, "LU") == {"name_de": "Clerf"}


def test_french_form_inside_dg():
    assert b.andere_namen("Amel", {"name:de": "Amel", "name:fr": "Amblève"}, "BE-DG") == {"name_fr": "Amblève"}


def test_no_second_form_when_equal_or_contained():
    assert b.andere_namen("Bütgenbach", {"name:fr": "Butgenbach"}, "BE-DG") == {}         # nur der Umlaut fehlt
    assert b.andere_namen("Putscheid", {"name:de": "Pütscheid"}, "LU") == {}
    assert b.andere_namen("Kelmis - La Calamine", {"name:de": "Kelmis"}, "BE-WAL") == {}   # steckt schon im Namen
    assert b.andere_namen("Malmedy", {}, "BE-WAL") == {}
    assert b.andere_namen("Städteregion Aachen", {"name:fr": "Aix-la-Chapelle"}, "DE-NW") == {}   # Deutschland: nie


def test_gebiet_meta_carries_namedetails():
    feat = {"properties": {"osm_id": 1, "name": "Waimes", "address": {"country_code": "be"},
                           "extratags": {"ref:INS": "63080"}, "namedetails": {"name:de": "Weismes"}}}
    assert b.gebiet_meta(feat) == {"ars": "BE-63080", "name": "Waimes", "land": "BE-WAL", "ebene": "Gemeinde", "name_de": "Weismes"}
    feat["properties"].pop("namedetails")
    assert "name_de" not in b.gebiet_meta(feat)                                          # älterer Abruf ohne Namen


def test_dg_keeps_german_official_name_and_gets_french():
    feat = {"properties": {"osm_id": 2, "name": "Kelmis - La Calamine", "address": {"country_code": "be"},
                           "extratags": {"ref:INS": "63040"}, "namedetails": {"name:fr": "La Calamine"}}}
    assert b.gebiet_meta(feat) == {"ars": "BE-63040", "name": "Kelmis", "land": "BE-DG", "ebene": "Gemeinde", "name_fr": "La Calamine"}
