const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.join(__dirname, '..');
const wald = fs.readFileSync(path.join(root, 'web/wald.js'), 'utf8');
const konto = fs.readFileSync(path.join(root, 'web/konto.js'), 'utf8');
const ctx = vm.createContext({});
vm.runInContext(wald + '\n' + konto.match(/^function gespeicherteBaeume\([\s\S]*?^}/m)[0], ctx);
const werte = x => Array.from(x);
let auswahl = ctx.waldAuswahlWechseln([], 'kiefer');
auswahl = ctx.waldAuswahlWechseln(auswahl, 'eiche');
assert.deepEqual(werte(auswahl), ['kiefer', 'eiche']);
assert.deepEqual(werte(ctx.waldAuswahlWechseln(auswahl, 'kiefer')), ['eiche']);
auswahl = ctx.waldAuswahlWechseln(auswahl, 'gesamt');
assert.deepEqual(werte(auswahl), ['gesamt']);
assert.deepEqual(werte(ctx.waldAuswahlWechseln(auswahl, 'buche')), ['buche']);
assert.deepEqual(werte(ctx.waldAuswahlWechseln(auswahl, 'gesamt')), []);
assert.deepEqual(werte(ctx.gespeicherteBaeume({baum: 'eiche'})), ['eiche']);
assert.deepEqual(werte(ctx.gespeicherteBaeume({baum: 'eiche', baeume: []})), []);
assert.deepEqual(werte(ctx.gespeicherteBaeume({baeume: ['kiefer', 'eiche', 'kiefer']})), ['kiefer', 'eiche']);
assert.deepEqual(werte(ctx.gespeicherteBaeume({baeume: ['gesamt', 'eiche']})), ['gesamt']);
assert.deepEqual(werte(ctx.gespeicherteBaeume({baeume: [null, 1, 'x"]', 'eiche']})), ['eiche']);
new vm.Script(konto);
function element() {
  return {children: [], dataset: {}, style: {}, attrs: {}, hidden: false,
    classList: {toggle() {}}, setAttribute(k, v) {this.attrs[k] = v;},
    append(...kinder) {this.children.push(...kinder);}, replaceChildren() {this.children = [];}};
}
ctx.document = {createElement: element, createTextNode: text => text};
const layers = new Map([['beschriftung', {}]]), sources = new Map();
const map = {
  getLayer: id => layers.get(id),
  addSource(id, source) {assert.ok(!sources.has(id)); sources.set(id, source);},
  addLayer(layer) {layers.set(layer.id, layer);},
  moveLayer(id) {assert.ok(layers.has(id));},
  setLayoutProperty(id, key, value) {layers.get(id).layout[key] = value;},
  removeLayer: id => layers.delete(id), removeSource: id => sources.delete(id)
};
const manifest = {grenzen: [[52, 10], [53, 11]], version: 'test',
  ebenen: ['gesamt', 'kiefer', 'eiche'].map(s => ({schluessel: s, name: s, datei: s+'.png', kontur: s+'-k.png'}))};
const leiste = element(), legende = element();
ctx.waldEinrichten(map, manifest, leiste, legende, () => {}, ['kiefer', 'eiche']);
assert.equal(sources.size, 4);
assert.equal(legende.children.length, 2);
leiste.children[0].onclick();
assert.equal(sources.size, 2);
assert.ok(sources.has('wald_gesamt'));
assert.equal(leiste.children[1].attrs['aria-pressed'], 'false');
leiste.children[0].onclick();
assert.equal(sources.size, 0);
assert.equal(legende.hidden, true);
leiste.children[2].onclick();
assert.equal(sources.size, 2);
assert.equal(sources.get('wald_eiche').url, 'eiche.png?v=test');
console.log('Baumarten: Mehrfachauswahl, Gesamtwald und Migration der Einstellungen bestanden.');
