// Tests für die Gebäudefarben nach Funktion (web/js/gebaeude-farben.js: BUILDING_KLASSEN, buildingFill).
import test from 'node:test';
import assert from 'node:assert/strict';

const { BUILDING, BUILDING_KLASSEN, buildingFill } = await import('../../web/js/gebaeude-farben.js');

test('jede Klasse hat Titel und Farben für hell und dunkel', () => {
  for (const [id, titel, c] of BUILDING_KLASSEN) {
    assert.ok(id && titel, id);
    assert.match(c.light, /^#[0-9a-f]{6}$/i, id);
    assert.match(c.dark, /^#[0-9a-f]{6}$/i, id);
  }
});

test('Ausdruck: match auf klasse, Standard Weinrot, Wohnen und sonst im Standard', () => {
  for (const k of ['light', 'dark']) {
    const e = buildingFill(k);
    assert.deepEqual(e.slice(0, 2), ['match', ['get', 'klasse']]);
    assert.equal(e.at(-1), BUILDING[k]);
    assert.ok(!e.includes('wohnen') && !e.includes('sonst'));
    assert.ok(e.includes('religion'));
    assert.equal((e.length - 3) % 2, 0);
  }
});
