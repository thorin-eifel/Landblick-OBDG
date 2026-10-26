// Höhenabfrage (Rechtsklick, Legende): Kachelzoom folgt der Ablage aus tiles/dem/meta.json.
import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.window ??= globalThis;
const { abfrageZoom } = await import('../../web/js/relief.js');

test('Ablage bis Zoom 12 (Ostbelgien): Abfrage auf 12, nicht auf 14', () => {
  assert.equal(abfrageZoom(12), 12);
});

test('vollständige Ablage oder feinere Kacheln: Abfrage bleibt bei 14', () => {
  assert.equal(abfrageZoom(14), 14);
  assert.equal(abfrageZoom(16), 14);
});
