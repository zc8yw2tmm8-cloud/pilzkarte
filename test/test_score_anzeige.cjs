const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../web/index.html'), 'utf8');
const namen = ['scoreGueltig', 'scoreMittel', 'scoreText', 'popupInhalt'];
const code = namen.map(name => {
  const treffer = html.match(new RegExp(`^function ${name}\\([\\s\\S]*?^}`, 'm'));
  assert.ok(treffer, name);
  return treffer[0];
}).join('\n');
const leer = () => '';
const c = vm.createContext({
  D: {arten: {test: {name: 'Testpilz'}}}, art: 'test', tag: 0,
  tagname: () => 'Heute', farbe: () => '#000', komma: String,
  trendZeile: leer, bremszeile: leer, fundknopf: leer,
  navigationsknopf: leer, wertzeile: leer, regenzeilen: leer
});
vm.runInContext(code, c);
assert.equal(c.scoreMittel([null, 80]), 80);
assert.equal(c.scoreMittel([0, 80, null]), 40);
assert.equal(c.scoreMittel([null, undefined, NaN, Infinity, -1, 101]), null);
assert.equal(c.scoreMittel([]), null);
assert.equal(c.scoreText(0), '0');
assert.equal(c.scoreText(null), 'Keine Daten');
const z = {scores: {test: [null]}, kenn: {}, titel: 'Testgebiet', id: 'test', hoehe: null, waldanteil: null};
let popup = c.popupInhalt(z);
assert.match(popup, /<b>Keine Daten<\/b>/);
assert.doesNotMatch(popup, /class="max"/);
z.scores.test[0] = 0;
popup = c.popupInhalt(z);
assert.match(popup, /<b>0<\/b><span class="max">\/100<\/span>/);
for (const script of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
  new vm.Script(script[1]);
}
console.log('OK: Mittelwerte, fehlende Werte, Nullscore, Popup und JavaScript-Syntax');
