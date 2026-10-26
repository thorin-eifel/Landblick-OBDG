// Sichtbare Texte des Frontends: keine Gebietsnamen aus Landblick-RLP mehr (die Alte Karte trug lange „Die Südeifel“ im Titelschild).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const WEB = new URL('../../web/', import.meta.url).pathname;
const RLP = /Südeifel|Hunsrück|Westerwald|Pfälzerwald|Saarland/;

function* dateien(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (name === 'vendor' || name === 'data' || name === 'tiles') continue;   // Fremdcode und erzeugte Daten
    if (statSync(p).isDirectory()) yield* dateien(p);
    else if (/\.(js|html|css)$/.test(name)) yield p;
  }
}

test('kein Gebietsname aus Landblick-RLP in web/', () => {
  const funde = [];
  for (const p of dateien(WEB)) {
    readFileSync(p, 'utf8').split('\n').forEach((z, i) => { if (RLP.test(z)) funde.push(`${p.slice(WEB.length)}:${i + 1}: ${z.trim().slice(0, 80)}`); });
  }
  assert.deepEqual(funde, []);
});

test('Titelschild der Alten Karte heißt Ostbelgien', async () => {
  const { KARTUSCHE_TITEL } = await import('../../web/js/medieval.js');
  assert.equal(KARTUSCHE_TITEL, 'Ostbelgien');
});
