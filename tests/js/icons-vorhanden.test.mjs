// Jedes Symbol, das Oberfläche und Karte anfordern, liegt im Repository (sonst fehlt es in der Desktop-App, die nur
// mitbringt, was versioniert ist). UXWing-Dateien dürfen nicht weitergegeben werden und haben hier nichts zu suchen.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

globalThis.window ??= globalThis;
const ICONS = new URL('../../web/icons/', import.meta.url);
const css = readFileSync(new URL('../../web/css/icons.css', import.meta.url), 'utf8');
const { CHIP_ICONS, NATURE_CHIP } = await import('../../web/js/icons.js');

const angefordert = new Set([
  ...[...css.matchAll(/url\(\.\.\/icons\/([\w-]+)\.svg\)/g)].map((m) => m[1]),
  ...CHIP_ICONS, 'flug', 'hubschrauber', 'tanken', ...Object.values(NATURE_CHIP).map(([g]) => g),
]);

test('jedes angeforderte Symbol hat eine Datei', () => {
  const fehlt = [...angefordert].filter((n) => !existsSync(new URL(`${n}.svg`, ICONS)));
  assert.deepEqual(fehlt, []);
});

test('alle Symbole sind versioniert (nicht durch .gitignore ausgeschlossen)', () => {
  const pfade = [...angefordert].map((n) => `web/icons/${n}.svg`);
  // check-ignore endet mit 1, wenn nichts ignoriert wird; maßgeblich ist nur die Ausgabe
  const r = spawnSync('git', ['check-ignore', '--no-index', ...pfade], { cwd: new URL('../../', import.meta.url), encoding: 'utf8' });
  assert.equal(r.stdout.trim(), '');
});

test('kein Symbol stammt von UXWing', () => {
  const uxwing = readdirSync(ICONS).filter((f) => f.endsWith('.svg')).filter((f) => /uxwing|id="Layer_1"/i.test(readFileSync(new URL(f, ICONS), 'utf8')));
  assert.deepEqual(uxwing, []);
});
