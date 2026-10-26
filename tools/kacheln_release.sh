#!/usr/bin/env bash
# =============================================================================
# Landblick - OBDG — Kachelpakete für den Windows-Installer als GitHub-Release
#
# Zweck:     Packt die Höhenkacheln zu dem.pmtiles, legt sie mit der Basiskarte (region, ring, core) und dem Suchindex nach
#            build/<Tag>/, schreibt SHA256SUMS im Format, das .github/workflows/windows-installer.yml prüft
#            ("<sha256> *<Datei>"), und eine Release-Notiz mit Größen, Datenstand und Quellen. Mit --github legt es das
#            Release an. Der Workflow kacheln-release.yml ruft genau dieses Skript auf.
# Aufruf:    tools/kacheln_release.sh kacheln-1              nur zusammenstellen und prüfen
#            tools/kacheln_release.sh kacheln-1 --github     zusätzlich Release anlegen (Tag auf origin/main)
# Voraus:    tools/kartenbasis.sh ist gelaufen (web/tiles/*.pmtiles, web/tiles/dem/, web/data/suche_geo.json).
# Umgebung:  PYTHON_TOOLS  Python mit pmtiles (requirements-tools.txt), Standard .venv-tools/bin/python
# Regeln:    Ein vorhandenes Release wird nie überschrieben: der Windows-Lauf prüft gegen die Prüfsummen, eine stille
#            Änderung unter demselben Tag würde ältere Installer-Läufe unprüfbar machen. Neuer Stand heißt neuer Tag.
#            Das Release ist kein Programm-Release und wird nicht als "neueste Version" markiert.
# Exit:      0 = gut, 1 = Fehler
# =============================================================================
set -euo pipefail

TAG="${1:?Tag angeben, z. B. kacheln-1}"
MODE="${2:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_TOOLS="${PYTHON_TOOLS:-${ROOT}/.venv-tools/bin/python}"
OUT="${ROOT}/build/${TAG}"
NOTES="${ROOT}/build/${TAG}-notiz.md"
FILES=(dem.pmtiles region.pmtiles ring.pmtiles core.pmtiles suche_geo.json)

log()  { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*" >&2; }
fail() { log "FEHLER: $*"; exit 1; }

[[ "${TAG}" =~ ^kacheln-[0-9]+$ ]] || fail "Tag muss kacheln-<Zahl> heißen, nicht ${TAG}"
[ -x "${PYTHON_TOOLS}" ] || fail "Werkzeug-Python fehlt: ${PYTHON_TOOLS}"
cd "${ROOT}"
for f in web/tiles/region.pmtiles web/tiles/ring.pmtiles web/tiles/core.pmtiles web/tiles/dem/meta.json web/data/suche_geo.json; do
  [ -s "${f}" ] || fail "fehlt: ${f} (erst tools/kartenbasis.sh)"
done
if [ "${MODE}" = "--github" ]; then
  command -v gh >/dev/null || fail "gh (GitHub-CLI) fehlt"
  if gh release view "${TAG}" >/dev/null 2>&1; then fail "Release ${TAG} gibt es schon; für einen neuen Stand den nächsten Tag nehmen"; fi
fi

rm -rf "${OUT}" && mkdir -p "${OUT}"
log "Höhenkacheln packen"
"${PYTHON_TOOLS}" tools/pack_tiles.py --src web/tiles/dem --out "${OUT}/dem.pmtiles" --meta web/tiles/dem/meta.json --max-zoom 12
cp web/tiles/region.pmtiles web/tiles/ring.pmtiles web/tiles/core.pmtiles web/data/suche_geo.json "${OUT}/"
( cd "${OUT}" && sha256sum -b "${FILES[@]}" > SHA256SUMS && sha256sum -c --quiet SHA256SUMS ) || fail "Prüfsummen stimmen nicht"
[ "$(grep -cE '^[0-9a-f]{64} \*.+$' "${OUT}/SHA256SUMS")" = "${#FILES[@]}" ] || fail "SHA256SUMS hat nicht das Format des Windows-Laufs"

log "Release-Notiz"
"${PYTHON_TOOLS}" - "${OUT}" "${NOTES}" <<'EOF'
import json, sys
from pathlib import Path
from pmtiles.reader import MmapSource, Reader

out, notes = Path(sys.argv[1]), Path(sys.argv[2])
def info(name):
    with open(out / name, "rb") as f:
        r = Reader(MmapSource(f))
        return r.header(), r.metadata()
mb = lambda name: f"{(out / name).stat().st_size / 1e6:.0f} MB"
rows, osm = [], ""
for name, inhalt in [("region.pmtiles", "Basiskarte der ganzen Fläche"), ("ring.pmtiles", "Straßen und Gebäude im Umkreis"),
                     ("core.pmtiles", "Straßen, Gebäude, Hausnummern in den Kernen"), ("dem.pmtiles", "Höhen (Terrarium)")]:
    h, m = info(name)
    osm = osm or str(m.get("planetiler:osm:osmosisreplicationtime", ""))[:10]
    zoom = str(h["min_zoom"]) if h["min_zoom"] == h["max_zoom"] else f"{h['min_zoom']}–{h['max_zoom']}"
    rows.append(f"| `{name}` | {inhalt} | {zoom} | {mb(name)} |")
n_such = len(json.loads((out / "suche_geo.json").read_text(encoding="utf-8")).get("e", []))
anzahl = f"{n_such:,}".replace(",", " ")
groesse = f"{(out / 'suche_geo.json').stat().st_size / 1e6:.1f}".replace(".", ",")
rows.append(f"| `suche_geo.json` | Suchindex, {anzahl} Einträge | – | {groesse} MB |")
dem_attr = json.loads(Path("web/tiles/dem/meta.json").read_text(encoding="utf-8")).get("attribution", "")
notes.write_text("\n".join([
    "Kachelpakete für Landblick-OBDG: Ostbelgien (Deutschsprachige Gemeinschaft) und 20 km Umkreis. Der Workflow **windows-installer** "
    "lädt diese Dateien (Eingabe `kacheln_tag`), prüft sie gegen `SHA256SUMS` und packt sie in den Installer. Programmcode enthält dieses Release nicht.",
    "", "| Datei | Inhalt | Zoom | Größe |", "|---|---|---|---|", *rows, "",
    f"Stand der OpenStreetMap-Daten: {osm or 'unbekannt'}. Gebaut mit `tools/kartenbasis.sh` und `tools/kacheln_release.sh`.",
    "", "**Quellen und Lizenzen**",
    "- Basiskarte und Suchindex: © OpenStreetMap-Mitwirkende, ODbL 1.0, über den Protomaps-Build (build.protomaps.com).",
    f"- {dem_attr or 'Höhen: Mapzen Terrain Tiles'}.",
    "", "Wer die Dateien weitergibt oder daraus Karten zeigt, nennt diese Quellen.", ""]), encoding="utf-8")
EOF
log "Dateien in ${OUT}:"; ls -l "${OUT}" >&2

if [ "${MODE}" = "--github" ]; then
  gh release create "${TAG}" --target main --latest=false --title "Kachelpakete ${TAG#kacheln-} (Ostbelgien)" \
    --notes-file "${NOTES}" "${OUT}/SHA256SUMS" "${OUT}"/*.json "${OUT}"/*.pmtiles
  log "Release ${TAG} angelegt."
fi
