// Tests für web/js/gebiet.js: Filterregel, Auswahllisten, Land/Kreis-Abgleich.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gebietPasst, gebietAktiv, gebietName, laenderListe, kreiseListe, landWaehlen, kreisWaehlen, GEBIET_LEER } from '../../web/js/gebiet.js';

const kreise = [
  { ars: 'BE-63023', name: 'Eupen', land: 'BE-DG' },
  { ars: 'BE-63001', name: 'Amel', name_fr: 'Amblève', land: 'BE-DG' },
  { ars: 'DE-05334', name: 'Städteregion Aachen', land: 'DE-NW' },
];

test('ohne Filter passt alles, auch Einträge ohne Angaben', () => {
  assert.ok(gebietPasst({}, GEBIET_LEER));
  assert.ok(!gebietAktiv(GEBIET_LEER));
});

test('Kreis zählt über ars, Land über land; Einträge ohne Angabe fallen bei gesetztem Filter heraus', () => {
  assert.ok(gebietPasst({ ars: 'BE-63023', land: 'BE-DG' }, { land: '', ars: 'BE-63023' }));
  assert.ok(!gebietPasst({ ars: 'BE-63001', land: 'BE-DG' }, { land: 'BE-DG', ars: 'BE-63023' }));
  assert.ok(gebietPasst({ ars: null, land: 'LU' }, { land: 'LU', ars: '' }));
  assert.ok(!gebietPasst({}, { land: 'BE-DG', ars: '' }));
});

test('Auswahllisten: Länder der Gliederung plus Belgien, Luxemburg, Niederlande; Kreise nach Land und Name', () => {
  const l = laenderListe(kreise).map((x) => x[0]);
  assert.deepEqual(l.sort(), ['BE', 'BE-DG', 'DE-NW', 'LU', 'NL']);
  assert.ok(!l.includes('FR'), 'Frankreich liegt nicht in der Region');
  assert.deepEqual(kreiseListe(kreise, 'BE-DG').map((x) => x[1]), ['Amel (frz. Amblève)', 'Eupen']);
  assert.equal(kreiseListe(kreise, '').length, 3);
});

test('Land wechseln verwirft unpassenden Kreis, Kreis wählen setzt das Land', () => {
  assert.deepEqual(landWaehlen({ land: 'BE-DG', ars: 'BE-63023' }, 'DE-NW', kreise), { land: 'DE-NW', ars: '' });
  assert.deepEqual(landWaehlen({ land: 'BE-DG', ars: 'BE-63023' }, 'BE-DG', kreise), { land: 'BE-DG', ars: 'BE-63023' });
  assert.deepEqual(kreisWaehlen(GEBIET_LEER, 'DE-05334', kreise), { land: 'DE-NW', ars: 'DE-05334' });
  assert.deepEqual(kreisWaehlen({ land: 'DE-NW', ars: 'DE-05334' }, '', kreise), { land: 'DE-NW', ars: '' });
});

test('gebietAusEinheit: Kreis- und Landschlüssel der Übersichtszahlen', async () => {
  const { gebietAusEinheit } = await import('../../web/js/gebiet.js');
  const kreise = [{ ars: '07232', name: 'Eifelkreis Bitburg-Prüm', land: 'DE-RP' }];
  assert.deepEqual(gebietAusEinheit('kreis:07232', kreise), { land: 'DE-RP', ars: '07232' });
  assert.deepEqual(gebietAusEinheit('land:LU', kreise), { land: 'LU', ars: '' });
  assert.equal(gebietAusEinheit('kreis:99999', kreise), null);
  assert.equal(gebietAusEinheit('quatsch', kreise), null);
  assert.equal(gebietAusEinheit(undefined, kreise), null);
});

test('gebietName: amtlicher Name, dahinter die andere Sprachform', () => {
  assert.equal(gebietName({ name: 'Waimes', name_de: 'Weismes' }), 'Waimes (dt. Weismes)');
  assert.equal(gebietName({ name: 'Amel', name_fr: 'Amblève' }), 'Amel (frz. Amblève)');
  assert.equal(gebietName({ name: 'Eupen' }), 'Eupen');
  assert.equal(gebietName(null), '');
});

test('kreiseListe zeigt beide Formen, sortiert nach dem amtlichen Namen', () => {
  const k = [{ ars: 'BE-63080', name: 'Waimes', name_de: 'Weismes', land: 'BE-WAL' }, { ars: 'BE-63049', name: 'Malmedy', land: 'BE-WAL' }];
  assert.deepEqual(kreiseListe(k, 'BE-WAL'), [['BE-63049', 'Malmedy'], ['BE-63080', 'Waimes (dt. Weismes)']]);
});
