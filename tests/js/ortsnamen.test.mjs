// Übersichtskarte: Ortsnamen in der Deutschsprachigen Gemeinschaft alle, außerhalb nur Städte ab FREMD_MIN_EINWOHNER.
import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.window ??= globalThis;
globalThis.devicePixelRatio ??= 1;
const { ortsnamenUebersicht, FREMD_MIN_EINWOHNER } = await import('../../web/js/lage/stil.js');
const { KERN_UMRISS } = await import('../../web/js/lage/kern-umriss.js');

const basis = { id: 'places_locality', type: 'symbol', source: 'basemap', 'source-layer': 'places', filter: ['==', ['get', 'kind'], 'locality'], layout: {}, paint: {} };

test('places_locality wird zu Detailebene ab Zoom 9 und Übersichtsebene Zoom 5 bis 9', () => {
  const [detail, ov] = ortsnamenUebersicht(basis);
  assert.equal(detail.id, 'places_locality');
  assert.equal(detail.minzoom, 9);
  assert.equal(detail.filter, basis.filter, 'ab Zoom 9 kein Unterschied, kein Irrel-Ausschluss');
  assert.equal(ov.id, 'places_locality_ov');
  assert.equal(ov.minzoom, 5);
  assert.equal(ov.maxzoom, 9);
  const any = ov.filter[2];
  assert.deepEqual(ov.filter[1], ['==', ['get', 'kind'], 'locality'], 'Ausdruckssyntax, keine alte Filtersyntax mischen');
  assert.equal(any[0], 'any');
  assert.equal(any[1][0], 'within');
  assert.equal(any[1][1], KERN_UMRISS);
  assert.equal(any[2][2] !== undefined && any[2][2], FREMD_MIN_EINWOHNER);
});

test('andere Ebenen bleiben unverändert', () => {
  const x = { id: 'roads_labels_major' };
  assert.deepEqual(ortsnamenUebersicht(x), [x]);
});

test('Umriss: die DG-Orte liegen darin, Malmedy, Aachen, Verviers und Lüttich nicht', () => {
  const inside = (lon, lat) => KERN_UMRISS.coordinates.some(([ring]) => {
    let c = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) c = !c;
    }
    return c;
  });
  for (const [n, lon, lat] of [['Eupen', 6.035, 50.63], ['Kelmis', 6.0, 50.717], ['Sankt Vith', 6.127, 50.283], ['Burg-Reuland', 6.139, 50.197]]) assert.ok(inside(lon, lat), n);
  for (const [n, lon, lat] of [['Malmedy', 6.028, 50.426], ['Aachen', 6.084, 50.775], ['Verviers', 5.862, 50.589], ['Lüttich', 5.58, 50.633]]) assert.ok(!inside(lon, lat), n);
});

test('Klippen: mit Geländemodell zweiter Satz aus der Quelle klippen, OSM-Klippen entfallen dann', async () => {
  const { cliffLayers } = await import('../../web/js/lage/stil.js');
  const ohne = cliffLayers('light', false, true, false);
  assert.deepEqual(ohne.map((l) => l.id), ['land-cliff-band', 'land-cliff', 'land-cliff-teeth']);
  assert.ok(ohne.every((l) => l.source === 'basemap'));
  const mit = cliffLayers('light', false, true, true);
  const dgm = mit.filter((l) => l.id.endsWith('-dgm'));
  assert.deepEqual(dgm.map((l) => l.id), ['land-cliff-wand-dgm', 'land-cliff-schraffur-dgm', 'land-cliff-dgm']);
  assert.ok(dgm.every((l) => l.source === 'klippen'));
  assert.deepEqual(dgm.map((l) => l['source-layer']), ['wand', 'schraffur', 'kante']);
  assert.equal(dgm[0].type, 'fill');                  // Wandfläche liegt unter Schraffur und Oberkante
  const osm = mit.find((l) => l.id === 'land-cliff');
  assert.deepEqual(osm.filter, ['==', 'kind', '__keine__']);   // nicht doppelt zeichnen: mit Wandkacheln keine OSM-Klippen
});

test('Ansicht aus der Adresse: gültige Werte, sonst null', async () => {
  const { ansichtAusAdresse } = await import('../../web/js/ansicht.js');
  assert.deepEqual(ansichtAusAdresse('#15/49.861/6.448'), { zoom: 15, lat: 49.861, lon: 6.448 });
  assert.deepEqual(ansichtAusAdresse('#14.5/49/6'), { zoom: 14.5, lat: 49, lon: 6 });
  for (const bad of ['#debug', '', undefined, '#99/49/6', '#12/95/6', '#12/49/200', '#12/49', '#12/a/b', '#12/49/6/1']) assert.equal(ansichtAusAdresse(bad), null, String(bad));
});
