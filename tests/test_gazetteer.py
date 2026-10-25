"""Tests für tools/build_gazetteer.py: Namensformen zweisprachiger Orte und Zuschnitt auf die Region."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("build_gazetteer", ROOT / "tools" / "build_gazetteer.py")
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)


def test_namen_teilt_zusammengesetzte_und_ergaenzt_deutsche_formen():
    assert bg.namen("Kelmis - La Calamine") == ["Kelmis - La Calamine", "Kelmis", "La Calamine"]
    assert bg.namen("Waimes") == ["Waimes", "Weismes"]
    assert bg.namen("Eupen", "Eupen") == ["Eupen"]                 # keine Dopplung
    assert bg.namen("Liège", "Lüttich") == ["Liège", "Lüttich"]    # name:de aus OSM


def test_overpass_antwort_mit_name_de_ergibt_zwei_eintraege():
    data = {"elements": [{"lat": 50.6295, "lon": 6.0353, "tags": {"name": "Eupen", "place": "town"}},
                         {"lat": 50.4149, "lon": 6.1118, "tags": {"name": "Waimes", "name:de": "Weismes", "place": "village"}}]}
    orte = bg.build(data)
    assert sorted(o["n"] for o in orte) == ["Eupen", "Waimes", "Weismes"]


def test_zuschnitt_behaelt_nur_orte_in_der_region():
    alt = [{"n": "Eupen", "lat": 50.6295, "lon": 6.0353, "k": 2}, {"n": "Plombières", "lat": 50.7377, "lon": 5.9611, "k": 3},
           {"n": "Mainz", "lat": 49.9929, "lon": 8.2473, "k": 1}]
    # Die Tests laufen auf der Prüffläche um Irrel; Mainz liegt dort draußen, Eupen und Plombières knapp drin
    namen = {o["n"] for o in bg.zuschnitt(alt)}
    assert "Mainz" not in namen and {"Plombières", "Bleiberg"} <= namen
