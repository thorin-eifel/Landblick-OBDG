#!/usr/bin/env bash
# =============================================================================
# Landblick - OBDG — Kartenbasis in einem Lauf bauen (Phase O2)
#
# Zweck:     Baut alles, was die Karte an statischen Dateien braucht und nicht im Repository liegt:
#              1. Basiskarte (Protomaps):  web/tiles/region.pmtiles, ring.pmtiles, core.pmtiles
#              2. Prüfung der Archive:     tools/check_tiles.py (zwölf Orte, drei Zoomstufen)
#              3. Höhenkacheln:            web/tiles/dem/ (Mapzen, Zoom 6 bis 12, mit meta.json)
#              4. Geländefaktoren Wind:    web/data/terrain.png, terrain.json
#              5. Suchindex:               web/data/suche_geo.json
#              6. optional Gewässernetz:   web/data/gewaessernetz.json (braucht einen Export mit Pegeln)
#            Jeder Schritt überspringt, was schon da ist, und lässt sich wiederholen.
# Parameter: --build JJJJMMTT    Protomaps-Build (Standard: neuester)
#            --mit-gewaesser     Schritt 6 ausführen (vorher python -m app.collect --once und python -m app.export)
#            --nur-pruefen       nur Schritt 2 auf vorhandene Archive
# Umgebung:  PYTHON_TOOLS  Python der Werkzeug-venv (requirements-tools.txt), Standard .venv-tools/bin/python
#            PYTHON_APP    Python der Betriebs-venv (requirements.txt), Standard .venv/bin/python
#            PMTILES       pmtiles-CLI, Standard tools/bin/pmtiles; fehlt sie und Go ist da, wird sie gebaut
# Beispiel:  tools/kartenbasis.sh
#            PYTHON_TOOLS=~/venvs/lb-tools/bin/python tools/kartenbasis.sh --build 20261025
# Dauer:     gemessen am 25.10.2026 in einer Cloud-Sitzung: Basiskarte unter 1 Minute, Höhenkacheln rund 1 Minute,
#            Suchindex rund 20 Sekunden. Zusammen rund 205 MB (Karte 101 MB, Höhen 103 MB).
# Netz:      build.protomaps.com, s3.amazonaws.com (elevation-tiles-prod), query.wikidata.org (nur Schritt 6).
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_TOOLS="${PYTHON_TOOLS:-${ROOT}/.venv-tools/bin/python}"
PYTHON_APP="${PYTHON_APP:-${ROOT}/.venv/bin/python}"
PMTILES="${PMTILES:-${ROOT}/tools/bin/pmtiles}"
PMTILES_VERSION="v1.28.0"
BUILD=""
MIT_GEWAESSER=0
NUR_PRUEFEN=0

log()  { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }
fail() { printf '%s FEHLER: %s\n' "$(date '+%H:%M:%S')" "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --build)          BUILD="${2:?--build braucht JJJJMMTT}"; shift 2 ;;
    --mit-gewaesser)  MIT_GEWAESSER=1; shift ;;
    --nur-pruefen)    NUR_PRUEFEN=1; shift ;;
    -h|--help)        sed -n '2,25p' "$0"; exit 0 ;;
    *)                fail "unbekannter Parameter: $1" ;;
  esac
done

[ -x "${PYTHON_TOOLS}" ] || fail "Werkzeug-Python fehlt: ${PYTHON_TOOLS} (python3 -m venv .venv-tools && .venv-tools/bin/pip install -r requirements-tools.txt)"
[ -x "${PYTHON_APP}" ]   || fail "Betriebs-Python fehlt: ${PYTHON_APP} (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)"
cd "${ROOT}"
export LANDBLICK_REGION="${ROOT}/region.yaml"

pruefen() {
  log "Prüfe Kartenarchive in web/tiles"
  "${PYTHON_TOOLS}" tools/check_tiles.py --dir web/tiles --volume || fail "Kartenarchive haben Lücken"
}

if [ "${NUR_PRUEFEN}" = 1 ]; then pruefen; exit 0; fi

# --- 1. Basiskarte ------------------------------------------------------------
if [ ! -x "${PMTILES}" ]; then
  command -v go >/dev/null || fail "pmtiles-CLI fehlt (${PMTILES}) und Go ist nicht installiert: https://github.com/protomaps/go-pmtiles/releases"
  log "Baue pmtiles-CLI ${PMTILES_VERSION} mit Go"
  mkdir -p "$(dirname "${PMTILES}")"
  GOBIN="$(cd "$(dirname "${PMTILES}")" && pwd)" go install "github.com/protomaps/go-pmtiles@${PMTILES_VERSION}"
  mv "$(dirname "${PMTILES}")/go-pmtiles" "${PMTILES}"
fi
if [ -s web/tiles/region.pmtiles ] && [ -s web/tiles/ring.pmtiles ] && [ -s web/tiles/core.pmtiles ]; then
  log "Basiskarte vorhanden, übersprungen (zum Neubau web/tiles/*.pmtiles löschen)"
else
  args=(--pmtiles "${PMTILES}" --stage all --budget-s 1500 --out web/tiles)
  [ -n "${BUILD}" ] && args+=(--build "${BUILD}")
  for lauf in 1 2 3 4 5 6; do
    log "Basiskarte, Lauf ${lauf}"
    rc=0; "${PYTHON_TOOLS}" tools/build_region_tiles.py "${args[@]}" || rc=$?
    [ "${rc}" = 0 ] && break
    [ "${rc}" = 2 ] || fail "build_region_tiles.py endete mit ${rc}"
  done
  [ "${rc}" = 0 ] || fail "Basiskarte nach sechs Läufen nicht fertig; Befehl wiederholen, Fertiges bleibt liegen"
fi

# --- 2. Prüfung ---------------------------------------------------------------
pruefen

# --- 3. Höhenkacheln ----------------------------------------------------------
log "Höhenkacheln (Zoom 6 bis 12)"
"${PYTHON_APP}" tools/build_dem.py || fail "Höhenkacheln unvollständig; Befehl wiederholen"

# --- 4. Geländefaktoren -------------------------------------------------------
log "Geländefaktoren für den Wind"
"${PYTHON_TOOLS}" tools/build_terrain.py

# --- 5. Suchindex -------------------------------------------------------------
log "Suchindex aus den Kacheln"
"${PYTHON_TOOLS}" tools/build_search_index.py

# --- 6. Gewässernetz ----------------------------------------------------------
if [ "${MIT_GEWAESSER}" = 1 ]; then
  [ -s web/data/gewaesser.json ] || fail "web/data/gewaesser.json fehlt: erst python -m app.collect --once und python -m app.export"
  log "Gewässernetz aus Wikidata"
  "${PYTHON_APP}" tools/build_gewaessernetz.py --gewaesser web/data/gewaesser.json --out web/data/gewaessernetz.json
fi

log "fertig: $(du -sh web/tiles | cut -f1) in web/tiles"
