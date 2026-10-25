#!/usr/bin/env bash
# Zweck:    Legt die mitgelieferten Kachelpakete als Tauri-Ressource ab (desktop/src-tauri/pakete), bevor `npx tauri build` läuft.
# Aufruf:   desktop/stage-pakete.sh [--pakete DIR] [--dem DIR]     z. B. --pakete dist/pakete --dem dist/pakete2
# Inhalt:   tiles/dem.pmtiles, tiles/{region,core,ring}.pmtiles (Basiskarte, für Ostbelgien rund 100 MB) und data/suche_geo.json;
#           tiles/{klippen,hang,gebaeude}.pmtiles nur, wenn vorhanden (für Ostbelgien noch nicht gebaut).
# Option:   --ohne-karte  Basiskarte weglassen (die App lädt sie dann beim ersten Start).
# Grenze:   NSIS-Installer höchstens 2 GB; das Skript bricht ab, wenn die Summe darüber liegt.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/desktop/src-tauri/pakete"
PAK="${ROOT}/dist/pakete"; DEM="${ROOT}/dist/pakete2"
KARTE=1
while [[ $# -gt 0 ]]; do case "$1" in --ohne-karte) KARTE=0; shift ;; --pakete) PAK="$2"; shift 2 ;; --dem) DEM="$2"; shift 2 ;; *) echo "unbekannt: $1" >&2; exit 2 ;; esac; done
die() { echo "FEHLER: $*" >&2; exit 1; }
rm -rf "${OUT}"; mkdir -p "${OUT}/tiles" "${OUT}/data"
need() { [[ -f "$1" ]] || die "fehlt: $1"; }
need "${DEM}/dem.pmtiles";           cp "${DEM}/dem.pmtiles" "${OUT}/tiles/"
for opt in "${PAK}/klippen.pmtiles" "${PAK}/hang.pmtiles" "${ROOT}/web/tiles/gebaeude.pmtiles"; do
  if [[ -f "${opt}" ]]; then cp "${opt}" "${OUT}/tiles/"; else echo "ohne $(basename "${opt}") (nicht gebaut)"; fi
done
need "${ROOT}/web/data/suche_geo.json";    cp "${ROOT}/web/data/suche_geo.json" "${OUT}/data/"
# Basiskarte: in Landblick-RLP rund 1,5 GB und darum Download beim ersten Start; für Ostbelgien klein genug für den Installer
if (( KARTE )); then for n in region core ring; do need "${ROOT}/web/tiles/${n}.pmtiles"; cp "${ROOT}/web/tiles/${n}.pmtiles" "${OUT}/tiles/"; done; fi
BYTES="$(du -sk "${OUT}" | cut -f1)"; BYTES=$((BYTES * 1024))
echo "Ressourcen: $((BYTES / 1000000)) MB in ${OUT}"
(( BYTES < 1900000000 )) || die "über 1,9 GB: der NSIS-Installer verträgt höchstens 2 GB (Region/Kern/Ring weglassen oder auslagern)"
