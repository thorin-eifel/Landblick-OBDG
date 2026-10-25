// Gebietsfilter: Land und Gebiet (rein, ohne DOM).
//
// Zweck:  Die Zellen tragen je Ereignis und Messstelle `ars` (Gebietsschlüssel mit Landespräfix: BE-63023 Eupen, DE-05334 Städteregion
//         Aachen, NL-GM0981 Vaals, LU-…; siehe tools/build_region.py) und `land` ('BE-DG', 'BE-WAL', 'DE-NW', 'DE-RP', 'LU', 'NL-LI').
//         Dieses Modul entscheidet, ob ein Eintrag zum gewählten Gebiet gehört, und baut die Auswahllisten aus der Gebietsliste des
//         Startpakets (start.json → kreise; der Name ist historisch).
// Regel:  Ist ein Gebiet gewählt, zählt nur `ars`. Ist nur ein Land gewählt, zählt `land`. Einträge ohne Angabe (ältere Daten, Punkte
//         außerhalb der Gliederung) fallen bei gesetztem Filter heraus, ohne Filter bleiben sie.
// Test:   tests/js/gebiet.test.mjs

export const LAND_NAMEN = {
  'BE-DG': 'Deutschsprachige Gemeinschaft', 'BE-WAL': 'Wallonien', 'BE-VLG': 'Flandern',
  'DE-NW': 'Nordrhein-Westfalen', 'DE-RP': 'Rheinland-Pfalz', LU: 'Luxemburg', 'NL-LI': 'Niederlande (Limburg)',
  BE: 'Belgien', DE: 'Deutschland', NL: 'Niederlande',
};
export const GEBIET_LEER = Object.freeze({ land: '', ars: '' });

export const gebietAktiv = (g) => !!(g && (g.land || g.ars));

export function gebietPasst(p, g) {
  if (!gebietAktiv(g)) return true;
  if (g.ars) return p.ars === g.ars;
  return p.land === g.land;
}

/** Gebiet zu einer Übersichtszahl (start.json einheiten[].key): „kreis:<ARS>“ oder „land:<Kürzel>“. Unbekannter Schlüssel → null. */
export function gebietAusEinheit(key, kreise) {
  const [art, wert] = String(key ?? '').split(':');
  if (!wert) return null;
  if (art === 'kreis') {
    const k = (kreise ?? []).find((x) => x.ars === wert);
    return k ? { land: k.land, ars: k.ars } : null;
  }
  if (art === 'land') return { land: wert, ars: '' };
  return null;
}

/** Länder für die Auswahl: alle, die in der Kreisliste vorkommen, dazu die Nachbarländer. */
export function laenderListe(kreise) {
  const set = new Set((kreise ?? []).map((k) => k.land));
  for (const l of ['LU', 'BE', 'FR']) set.add(l);
  return [...set].sort((a, b) => (LAND_NAMEN[a] ?? a).localeCompare(LAND_NAMEN[b] ?? b, 'de')).map((l) => [l, LAND_NAMEN[l] ?? l]);
}

/** Kreise eines Landes (alle, wenn kein Land gewählt), nach Namen sortiert. */
export function kreiseListe(kreise, land) {
  return (kreise ?? []).filter((k) => !land || k.land === land).sort((a, b) => a.name.localeCompare(b.name, 'de')).map((k) => [k.ars, k.name]);
}

/** Setzt ein Land; ein gewählter Kreis, der nicht dazu passt, wird verworfen. */
export function landWaehlen(g, land, kreise) {
  const k = (kreise ?? []).find((x) => x.ars === g.ars);
  return { land, ars: k && land && k.land !== land ? '' : g.ars };
}

/** Setzt einen Kreis und zieht das Land nach (der Kreis gehört zu genau einem Land). */
export function kreisWaehlen(g, ars, kreise) {
  const k = (kreise ?? []).find((x) => x.ars === ars);
  return { land: k ? k.land : g.land, ars: ars || '' };
}
