const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const c = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/interaktion.js'), 'utf8'), c);
assert.equal(c.kompassWinkel({webkitCompassHeading: 0}), 0);
assert.equal(c.kompassWinkel({webkitCompassHeading: 350}, 90), 80);
assert.equal(c.kompassWinkel({absolute: true, alpha: 90}), 270);
assert.equal(c.kompassWinkel({alpha: 90}), null);
assert.equal(c.kompassWinkel({webkitCompassHeading: 10, webkitCompassAccuracy: -1}), null);
assert.equal(c.kompassWinkel({webkitCompassHeading: NaN}), null);
const listeners = {};
let gestoppt = 0, weitergabe = 0, verhindert = 0;
const container = {
  addEventListener(t, fn, opt) { assert.equal(opt.passive, true); listeners[t] = fn; },
  removeEventListener(t) { delete listeners[t]; }
};
const aufheben = c.popupGestenTrennen(container, {stop() { gestoppt++; }});
const popup = {dataset: {}};
for (const type of ['touchstart', 'touchmove', 'wheel']) {
  listeners[type]({type, target: {closest: () => popup},
    stopPropagation() { weitergabe++; }, preventDefault() { verhindert++; }});
}
assert.equal(weitergabe, 3);
assert.equal(gestoppt, 2);
assert.equal(verhindert, 0);
assert.equal(popup.dataset.beruehrt, '1');
listeners.touchmove({type:'touchmove', target:{closest:()=>null},
  stopPropagation() { throw Error('Normale Kartenbewegung blockiert'); }});
aufheben(); assert.equal(Object.keys(listeners).length, 0);
console.log('OK: Kompasswerte, Querformat, fehlende Sensorwerte, Popup-Gesten und normale Karteninteraktion');

(async () => {
  const events = {}, domEvents = {}, controlEvents = {}, mapEvents = {};
  const messages = [], markers = [];
  let pressed = 'true', permission = 'denied', requests = 0, observer;
  const root = {
    querySelector() { return {getAttribute: () => pressed}; },
    addEventListener(t, fn) { domEvents[t] = fn; },
    removeEventListener(t) { delete domEvents[t]; }
  };
  const w = {
    screen: {orientation: {angle: 0}},
    DeviceOrientationEvent: {requestPermission: async () => { requests++; return permission; }},
    addEventListener(t, fn) { events[t] = fn; },
    removeEventListener(t) { delete events[t]; }
  };
  const doc = {
    hidden: false,
    createElement() { return {setAttribute(){}, appendChild(){}}; },
    addEventListener(t, fn) { domEvents[t] = fn; },
    removeEventListener(t) { delete domEvents[t]; }
  };
  class Marker {
    constructor() { markers.push(this); }
    setLngLat(p) { this.position = p; return this; }
    setRotation(r) { this.rotation = r; return this; }
    addTo() { return this; }
    remove() { this.removed = true; }
  }
  Object.assign(c, {window: w, document: doc, maplibregl: {Marker},
    MutationObserver: class { constructor(fn) { observer=fn; } observe(){} disconnect(){} },
    setTimeout: () => 1, clearTimeout: () => {}});
  const map = {getContainer:()=>root, on:(t,fn)=>mapEvents[t]=fn};
  const control = {on:(t,fn)=>controlEvents[t]=fn, off:t=>delete controlEvents[t]};
  c.blickrichtungEinrichten(map, control, m=>messages.push(m));
  const click = {target:{closest:()=>true}};
  await domEvents.click(click);
  assert.equal(messages.length,1); assert.equal(events.deviceorientation,undefined);
  permission='granted'; await domEvents.click(click);
  assert.equal(requests,2);
  events.deviceorientation({webkitCompassHeading:30}); assert.equal(markers.length,0);
  controlEvents.geolocate({coords:{longitude:10,latitude:52}});
  events.deviceorientation({webkitCompassHeading:30});
  assert.equal(markers[0].rotation,30);
  events.deviceorientation({webkitCompassHeading:120}); assert.equal(markers[0].rotation,120);
  pressed='false'; observer(); assert.equal(markers[0].removed,true);
  events.deviceorientation({webkitCompassHeading:40}); assert.equal(markers.length,1);
  mapEvents.remove(); assert.equal(Object.keys(events).length,0);
  console.log('OK: Sensorfreigabe abgelehnt/erneut erlaubt, GPS-Aktivierung, Drehung, Abschalten und Listener-Abbau');
})().catch(e=>{console.error(e);process.exitCode=1;});
