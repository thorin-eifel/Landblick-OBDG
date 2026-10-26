// Auskunft zu einem Punkt der Karte (Rechtsklick): Koordinaten, UTM, Gebiet und Land. Reine Funktionen, kein DOM.
//
// Zweck:  Aus geo/gebiete.geojson (tools/build_region.py: Gemeinden in Belgien, Luxemburg und den Niederlanden, Kreise in Deutschland)
//         den Namen unter dem Zeiger bestimmen. Alles läuft im Browser, es gibt keine Abfrage an Dritte.
// Grenzen: Punkt in Fläche ist auf rund 50 m genau (Vereinfachung beim Bau); direkt an einer Grenze kann die Nachbarin treffen.
//          Ortsteile und Teilgemeinden (Eynatten, Hergenrath …) fehlen noch.
// Test:   tests/js/ortsinfo.test.mjs

import { gebietName } from './gebiet.js';

/** Punkt (x, y) in Ring [x0, y0, x1, y1, ...]? Gerade-ungerade-Regel. */
export function imRing(ring, x, y) {
  let drin = false;
  for (let i = 0, j = ring.length - 2; i < ring.length; j = i, i += 2) {
    const xi = ring[i], yi = ring[i + 1], xj = ring[j], yj = ring[j + 1];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) drin = !drin;
  }
  return drin;
}

/** Entfernung in Metern (flache Näherung, auf Ortsebene genau genug). */
export function entfernung(lon1, lat1, lon2, lat2) {
  const k = Math.PI / 180, dx = (lon2 - lon1) * k * Math.cos(((lat1 + lat2) / 2) * k), dy = (lat2 - lat1) * k;
  return Math.hypot(dx, dy) * 6371008.8;
}

/** MultiPolygon/Polygon-Geometrie (GeoJSON) enthält den Punkt? Löcher werden beachtet. */
export function imGeoJson(geom, lng, lat) {
  const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.type === 'MultiPolygon' ? geom.coordinates : [];
  for (const p of polys) {
    const flach = (r) => r.flatMap((c) => [c[0], c[1]]);
    if (imRing(flach(p[0]), lng, lat) && !p.slice(1).some((h) => imRing(flach(h), lng, lat))) return true;
  }
  return false;
}

/** Landeskürzel → Name für die Auskunft (Kürzel wie in app/data/region/gebiete.json). */
export const LAENDER = {
  'BE-DG': 'Deutschsprachige Gemeinschaft', 'BE-WAL': 'Wallonien', 'BE-VLG': 'Flandern',
  'DE-NW': 'Nordrhein-Westfalen', 'DE-RP': 'Rheinland-Pfalz', 'LU': 'Luxemburg', 'NL-LI': 'Niederlande (Limburg)',
};

/**
 * Was liegt unter (lng, lat)? { gebiet, ebene, land } mit null für Unbekanntes.
 * `gebiete` ist geo/gebiete.geojson (oder null, wenn die Datei fehlt).
 */
export function findeGebiet(gebiete, lng, lat) {
  const f = gebiete?.features?.find((x) => imGeoJson(x.geometry, lng, lat));
  if (!f) return { gebiet: null, ebene: null, land: null };
  const p = f.properties ?? {};
  return { gebiet: gebietName(p) || null, ebene: p.ebene ?? null, land: LAENDER[p.land] ?? p.land ?? null };
}

const fmt = new Intl.NumberFormat('de-DE', { minimumFractionDigits: 5, maximumFractionDigits: 5 });
/** "50,62950° N, 6,03530° O" */
export function dezimalGrad(lat, lng) {
  return `${fmt.format(Math.abs(lat))}° ${lat >= 0 ? 'N' : 'S'}, ${fmt.format(Math.abs(lng))}° ${lng >= 0 ? 'O' : 'W'}`;
}

/** Grad Minuten Sekunden: 49° 51′ 00,4″ N */
export function gradMinutenSekunden(wert, pos, neg) {
  const a = Math.abs(wert), g = Math.floor(a), mf = (a - g) * 60, m = Math.floor(mf), s = (mf - m) * 60;
  return `${g}° ${String(m).padStart(2, '0')}′ ${s.toFixed(1).replace('.', ',').padStart(4, '0')}″ ${wert >= 0 ? pos : neg}`;
}

/** UTM nach ETRS89/GRS80 (Krüger-Reihe). Zone aus der Länge, Streifen als Buchstabe; "32U 317140 5524685". */
export function utm(lat, lng) {
  const a = 6378137, f = 1 / 298.257222101, k0 = 0.9996;
  const zone = Math.floor((lng + 180) / 6) + 1, lon0 = (zone * 6 - 183) * Math.PI / 180;
  const n = f / (2 - f), A = (a / (1 + n)) * (1 + n * n / 4 + n ** 4 / 64);
  const al = [n / 2 - 2 * n * n / 3 + 5 * n ** 3 / 16, 13 * n * n / 48 - 3 * n ** 3 / 5, 61 * n ** 3 / 240];
  const phi = lat * Math.PI / 180, lam = lng * Math.PI / 180 - lon0;
  const t = Math.sinh(Math.atanh(Math.sin(phi)) - (2 * Math.sqrt(n) / (1 + n)) * Math.atanh((2 * Math.sqrt(n) / (1 + n)) * Math.sin(phi)));
  const xi = Math.atan2(t, Math.cos(lam)), eta = Math.atanh(Math.sin(lam) / Math.sqrt(1 + t * t));
  let E = eta, N = xi;
  al.forEach((c, i) => { const j = i + 1; E += c * Math.cos(2 * j * xi) * Math.sinh(2 * j * eta); N += c * Math.sin(2 * j * xi) * Math.cosh(2 * j * eta); });
  const band = 'CDEFGHJKLMNPQRSTUVWX'[Math.max(0, Math.min(19, Math.floor((lat + 80) / 8)))];
  const east = Math.round(500000 + k0 * A * E), north = Math.round(k0 * A * N + (lat < 0 ? 10000000 : 0));
  return { zone, band, east, north, text: `${zone}${band} ${east} ${north}` };
}
