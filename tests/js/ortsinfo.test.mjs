// Tests für web/js/ortsinfo.js (Auskunft zu einem Kartenpunkt).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { dezimalGrad, entfernung, findeGebiet, gradMinutenSekunden, imGeoJson, imRing, utm } from '../../web/js/ortsinfo.js';

const quadrat = (x0, y0, s) => [x0, y0, x0 + s, y0, x0 + s, y0 + s, x0, y0 + s];

test('Punkt im Ring, auch im Loch des GeoJSON', () => {
  assert.ok(imRing(quadrat(0, 0, 10), 5, 5));
  assert.ok(!imRing(quadrat(0, 0, 10), 11, 5));
  const geom = { type: 'Polygon', coordinates: [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]] };
  assert.ok(imGeoJson(geom, 1, 1));
  assert.ok(!imGeoJson(geom, 5, 5));
});

test('UTM in Eupen (Zone 32, westlich von 6° schon Zone 31)', () => {
  const u = utm(50.6295, 6.0353);
  assert.equal(u.zone, 32); assert.equal(u.band, 'U');
  assert.ok(Math.abs(u.east - 290334) < 15 && Math.abs(u.north - 5612820) < 15, u.text);   // Referenz: pyproj, EPSG:25832
  assert.equal(utm(50.6, 5.95).zone, 31);   // Baelen, Hohes Venn: Zonengrenze läuft durch die Region
});

test('UTM am Zonenrand und Rechenfall Greenwich/Äquator', () => {
  const m = utm(0, 9);              // Mittelmeridian der Zone 32
  assert.equal(m.east, 500000); assert.equal(m.north, 0);
});

test('Koordinaten lesbar', () => {
  assert.equal(dezimalGrad(49.85, 6.45), '49,85000° N, 6,45000° O');
  assert.equal(gradMinutenSekunden(49.85, 'N', 'S'), '49° 51′ 00,0″ N');
  assert.ok(Math.abs(entfernung(6.45, 49.85, 6.46, 49.85) - 716) < 5);
});

const gebiete = { attribution: 'test', features: [
  { properties: { name: 'Eupen', land: 'BE-DG', ebene: 'Gemeinde' }, geometry: { type: 'Polygon', coordinates: [[[6.0, 50.6], [6.1, 50.6], [6.1, 50.7], [6.0, 50.7], [6.0, 50.6]]] } },
  { properties: { name: 'Städteregion Aachen', land: 'DE-NW', ebene: 'Kreis' }, geometry: { type: 'MultiPolygon', coordinates: [[[[6.1, 50.6], [6.3, 50.6], [6.3, 50.8], [6.1, 50.8], [6.1, 50.6]]]] } },
] };

test('Gebiet, Ebene und Land unter dem Zeiger', () => {
  assert.deepEqual(findeGebiet(gebiete, 6.03, 50.63), { gebiet: 'Eupen', ebene: 'Gemeinde', land: 'Deutschsprachige Gemeinschaft' });
  assert.deepEqual(findeGebiet(gebiete, 6.2, 50.7), { gebiet: 'Städteregion Aachen', ebene: 'Kreis', land: 'Nordrhein-Westfalen' });
});

test('außerhalb oder ohne Datei: alles leer', () => {
  assert.deepEqual(findeGebiet(gebiete, 5.0, 50.0), { gebiet: null, ebene: null, land: null });
  assert.deepEqual(findeGebiet(null, 6.03, 50.63), { gebiet: null, ebene: null, land: null });
});

test('echte Datei (wenn gebaut): Eupen liegt in Eupen, DG', { skip: !existsSync(new URL('../../web/geo/gebiete.geojson', import.meta.url)) }, () => {
  const d = JSON.parse(readFileSync(new URL('../../web/geo/gebiete.geojson', import.meta.url)));
  assert.deepEqual(findeGebiet(d, 6.0353, 50.6295), { gebiet: 'Eupen', ebene: 'Gemeinde', land: 'Deutschsprachige Gemeinschaft' });
  assert.equal(findeGebiet(d, 6.0839, 50.7753).land, 'Nordrhein-Westfalen');   // Aachen
  assert.equal(findeGebiet(d, 6.1389, 50.1972).gebiet, 'Burg-Reuland');
});

test('echte Datei (wenn gebaut): zweite Sprachform hinter dem amtlichen Namen', { skip: !existsSync(new URL('../../web/geo/gebiete.geojson', import.meta.url)) }, () => {
  const d = JSON.parse(readFileSync(new URL('../../web/geo/gebiete.geojson', import.meta.url)));
  assert.equal(findeGebiet(d, 6.1105, 50.4148).gebiet, 'Waimes (dt. Weismes)');
  assert.equal(findeGebiet(d, 6.0976, 50.3533).gebiet, 'Amel (frz. Amblève)');
  assert.equal(findeGebiet(d, 6.0287, 50.4255).gebiet, 'Malmedy');   // keine abweichende Form in OSM
});
