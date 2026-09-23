// Rechenteile der Suchgaenge in web/konto.js, ohne Browser und Backend
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const speicher = new Map();
const localStorage = {
  getItem: k => (speicher.has(k) ? speicher.get(k) : null),
  setItem: (k, v) => { speicher.set(k, String(v)); },
  removeItem: k => { speicher.delete(k); }
};
const c = vm.createContext({ crypto: globalThis.crypto, TextEncoder, Intl, console,
                             localStorage });
vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/konto.js'), 'utf8'), c);
const run = code => vm.runInContext(code, c);

const arten = {
  stein: { name: 'Steinpilz', saison: 0.8, saison_jahr: [0, 1], baender: { bf07: [[0.2, 0.3, 40]] } },
  pfiff: { name: 'Pfifferling', saison: 0.5, saison_jahr: [1, 0], baender: {} }
};
const daten = {
  stand: '2026-09-23', arten,
  tage: [{ datum: '2026-09-23' }, { datum: '2026-09-24' }],
  zellen: [
    { id: 'A', lat: 52.40, lon: 10.70, scores: { stein: [80, 60], pfiff: [12, 'x'] } },
    { id: 'B', lat: 52.50, lon: 10.90, scores: { stein: [5, 6], pfiff: [7, 8] } }
  ]
};
const BEGINN = new Date('2026-09-23T08:00:00Z');
const spalten = [...run('SUCHGANG_SPALTEN')];

(async () => {
  // Sortierte Schluessel: Reihenfolge egal
  assert.equal(c.stabilesJson({ b: 1, a: [2, { d: 3, c: null }] }),
               c.stabilesJson({ a: [2, { c: null, d: 3 }], b: 1 }));

  // Konfigurationshash: 12 Hex-Stellen, taeglicher Saisonwert egal, Baender nicht
  const h1 = await c.configHashAus(arten);
  assert.match(h1, /^[0-9a-f]{12}$/);
  const andererTag = structuredClone(arten);
  andererTag.stein.saison = 0.1;
  assert.equal(await c.configHashAus(andererTag), h1);
  assert.equal(await c.configHashAus({ pfiff: arten.pfiff, stein: arten.stein }), h1);
  const neueSchwelle = structuredClone(arten);
  neueSchwelle.stein.baender.bf07[0][2] = 41;
  assert.notEqual(await c.configHashAus(neueSchwelle), h1);
  assert.equal(await c.configHashAus(null), null);

  // Momentaufnahme am Startpunkt: naechste Zelle, Tag, ungueltig -> null
  const b = c.angezeigteBewertung(daten, ['stein', 'pfiff'], 52.401, 10.701, '2026-09-24');
  assert.equal(b.startzelle, 'A');
  assert.equal(b.bereich, 'startpunkt');
  assert.equal(b.datenstand, '2026-09-23');
  assert.equal(b.zellen.A.stein, 60);
  assert.equal(b.zellen.A.pfiff, null);
  assert.ok(b.abstand_km < 0.2);
  assert.equal(c.angezeigteBewertung(daten, ['stein'], 52.4, 10.7, '2026-09-20'), null);
  assert.equal(c.angezeigteBewertung(daten, ['stein'], 48.0, 11.0, '2026-09-23'), null);
  assert.equal(c.naechsteZelle({}, 52, 10), null);

  // Kalendertag in Berlin, auch ueber Mitternacht und Jahreswechsel
  assert.equal(c.berlinDatum('2026-09-19T23:30:00Z'), '2026-09-20');
  assert.equal(c.berlinDatum('2026-12-31T23:30:00Z'), '2027-01-01');
  assert.equal(c.berlinDatum('2026-03-29T21:59:00Z'), '2026-03-29');

  // Aufgezeichneter Gang: Datum, Hash statt Modellversion, alle Arten offen
  const sg = c.suchgangNeu({ arten: ['stein'], einwilligung: true, daten, beginn: BEGINN });
  await sg.versionBereit;
  assert.equal(sg.datum, '2026-09-23');
  assert.equal(sg.beginn, BEGINN.toISOString());
  assert.equal(sg.config_hash, h1);
  assert.equal(sg.modellversion, null);
  assert.equal(sg.versionsstatus, 'legacy');
  assert.equal(sg.datenstand, '2026-09-23');
  assert.deepEqual({ ...sg.ergebnisse }, { stein: 'offen' });
  assert.equal(sg.auswertung_erlaubt, true);
  assert.equal(sg.einwilligung_version, run('EINWILLIGUNG_VERSION'));
  assert.ok(!Number.isNaN(Date.parse(sg.einwilligung_zeit)));
  const ohne = c.suchgangNeu({ arten: ['stein'], daten, beginn: BEGINN });
  assert.equal(ohne.auswertung_erlaubt, false);
  assert.equal(ohne.einwilligung_version, null);
  assert.equal(ohne.einwilligung_zeit, null);

  // Startort setzt Zelle, erste besuchte Zelle und Momentaufnahme
  c.suchgangOrt(sg, 52.4000004, 10.7, 12.4, daten);
  assert.equal(sg.zelle, 'A');
  assert.equal(sg.genauigkeit_m, 12);
  assert.equal(sg.lat, 52.4);
  assert.deepEqual([...sg.besuchte_zellen], ['A']);
  assert.equal(sg.raeumlich_gemischt, false);
  assert.deepEqual({ ...sg.angezeigt.zellen.A }, { stein: 80 });
  assert.equal(c.startwert(sg, 'stein'), 80);

  // Weg durch eine zweite Zelle: festgehalten, raeumlich gemischt
  assert.equal(c.suchgangZelleMerken(sg, 52.5, 10.9, daten), true);
  assert.deepEqual([...sg.besuchte_zellen], ['A', 'B']);
  assert.equal(sg.raeumlich_gemischt, true);
  assert.equal(sg.angezeigt.bereich, 'besuchte_zellen');
  assert.deepEqual({ ...sg.angezeigt.zellen.B }, { stein: 5 });
  assert.equal(c.startwert(sg, 'stein'), 80, 'Startwert bleibt der des Startpunkts');
  assert.equal(c.suchgangZelleMerken(sg, 52.5, 10.9, daten), false, 'keine Dublette');
  assert.equal(c.suchgangZelleMerken(sg, 48.0, 11.0, daten), false, 'ausserhalb der Karte');
  // Neuer Datenstand unterwegs: Zelle ja, Wert nein
  const spaeter = { ...daten, stand: '2026-09-24',
    zellen: [...daten.zellen, { id: 'C', lat: 52.6, lon: 11.0, scores: { stein: [1, 2] } }] };
  assert.equal(c.suchgangZelleMerken(sg, 52.6, 11.0, spaeter), true);
  assert.ok(sg.besuchte_zellen.includes('C'));
  assert.equal(sg.angezeigt.zellen.C, undefined);

  // Ohne Karte: kein Ort, keine Zelle, Anzeige unbekannt
  const fern = c.suchgangNeu({ arten: ['stein'], daten });
  c.suchgangOrt(fern, 48.1, 11.5, NaN, daten);
  assert.equal(fern.zelle, null);
  assert.equal(fern.angezeigt, null);
  assert.equal(fern.genauigkeit_m, null);
  assert.deepEqual([...fern.besuchte_zellen], []);

  // Nachtrag: nur Datum, keine Kartenwerte, kein Hash
  const nach = c.suchgangNeu({ arten: ['stein'], quelle: 'nachtrag', datum: '2026-09-20', daten });
  await nach.versionBereit;
  c.suchgangOrt(nach, 52.4, 10.7, null, daten);
  assert.equal(nach.datum, '2026-09-20');
  assert.equal(nach.beginn, null);
  assert.equal(nach.angezeigt, null);
  assert.equal(nach.datenstand, null);
  assert.equal(nach.config_hash, null);
  assert.equal(nach.zelle, 'A');

  // Ende hoechstens 24 Stunden nach Beginn
  assert.equal(c.endeBegrenzt(sg, new Date(BEGINN.getTime() + 30 * 3600000)),
               new Date(BEGINN.getTime() + 24 * 3600000).toISOString());
  assert.equal(c.endeBegrenzt(sg, new Date(BEGINN.getTime() + 3600000)),
               new Date(BEGINN.getTime() + 3600000).toISOString());

  // Sichern: erst auf dem Geraet, dann upsert mit genau den Tabellenspalten
  const anfragen = [];
  let fehler = null;
  run('benutzer = { id: "u1" }');
  c.falschesBackend = {
    from(tabelle) {
      return { upsert(zeilen, optionen) {
        anfragen.push({ tabelle, zeilen: structuredClone(zeilen), optionen,
                        lokal: speicher.get('pilzkarte_suchgang_offen') });
        return Promise.resolve({ error: fehler });
      } };
    }
  };
  run('sb = falschesBackend');
  c.laufenderGang = sg;
  run('aufzeichnung = { beginn: new Date("2026-09-23T08:00:00Z"), km: 1.5,'
    + ' punkte: [{ lat: 52.4, lon: 10.7, t: 0 }], suchgang: laufenderGang }');
  assert.equal(await c.suchgangSichern(sg), true);
  const zeile = anfragen[0].zeilen;
  assert.equal(anfragen[0].tabelle, 'suchgang');
  assert.equal(anfragen[0].optionen.onConflict, 'id');
  assert.deepEqual(Object.keys(zeile).sort(), ['benutzer', ...spalten].sort());
  assert.equal(zeile.id, sg.id);
  assert.equal(zeile.benutzer, 'u1');
  assert.equal(zeile.config_hash, h1);
  assert.equal(zeile.modellversion, null);
  assert.ok(anfragen[0].lokal, 'vor dem Netzaufruf lokal gesichert');
  const lokal = JSON.parse(anfragen[0].lokal);
  assert.equal(lokal.benutzer, 'u1');
  assert.equal(lokal.suchgang.id, sg.id);
  assert.equal(lokal.punkte.length, 1);
  assert.ok(!('versionBereit' in lokal.suchgang));
  fehler = { message: 'Netz weg' };
  assert.equal(await c.suchgangSichern(sg), false);
  assert.equal(sg.fehler, 'Netz weg');
  fehler = null;

  // Gesicherter Stand: nur fuer dieselbe Person, wieder verwendbar
  const gemerkt = c.suchgangGemerkt();
  assert.equal(gemerkt.suchgang.id, sg.id);
  const zurueck = c.suchgangAusGemerkt(gemerkt);
  assert.deepEqual([...zurueck.besuchte_zellen], [...sg.besuchte_zellen]);
  assert.equal(zurueck.gesichert, false);
  await zurueck.versionBereit;
  run('benutzer = { id: "u2" }');
  assert.equal(c.suchgangGemerkt(), null, 'fremder Stand bleibt verborgen');
  run('benutzer = { id: "u1" }');
  c.suchgangVergessen('andere-id');
  assert.ok(speicher.has('pilzkarte_suchgang_offen'), 'nur passende Kennung loeschen');
  c.suchgangVergessen(sg.id);
  assert.ok(!speicher.has('pilzkarte_suchgang_offen'));
  run('aufzeichnung = null');

  // Nullfunde nur fuer ausdruecklich verneinte Arten, stabile Kennungen
  const zwei = c.suchgangNeu({ arten: ['stein', 'pfiff'], daten, beginn: BEGINN });
  c.suchgangOrt(zwei, 52.4, 10.7, 5, daten);
  anfragen.length = 0;
  assert.equal(await c.suchgangNullfunde(zwei, 52.4, 10.7), 0);
  assert.equal(anfragen.length, 0, 'alles offen: kein Nullfund');
  zwei.ergebnisse = { stein: 'nullfund', pfiff: 'offen' };
  assert.equal(await c.suchgangNullfunde(zwei, 52.4, 10.7), 1);
  await c.suchgangNullfunde(zwei, 52.4, 10.7);
  const [erst, dann] = anfragen.map(a => a.zeilen);
  assert.equal(erst[0].id, dann[0].id);
  assert.equal(erst[0].art, 'stein');
  assert.ok(erst[0].nullfund && erst[0].suchgang === zwei.id && erst[0].gefunden_am === '2026-09-23');
  assert.equal(erst[0].score, 80);

  // Eingetragene Funde: zaehlen und die Art als gefunden markieren
  anfragen.length = 0;
  c.suchgangFundeZaehlen(zwei, [{ art: 'pfiff', nullfund: false },
                                { art: 'parasol', nullfund: false },
                                { art: 'stein', nullfund: true }]);
  await new Promise(r => setTimeout(r, 0));
  assert.equal(zwei.ergebnisse.pfiff, 'fund');
  assert.equal(zwei.ergebnisse.stein, 'nullfund', 'Nullfund-Zeile aendert nichts');
  assert.equal(zwei.funde.pfiff, 1);
  assert.equal(zwei.funde.parasol, 1);
  assert.equal(c.fundZahl(zwei), 2);
  assert.equal(anfragen.filter(a => a.tabelle === 'suchgang').length, 1, 'gesichert');
  zwei.ergebnisse.stein = 'fund';
  assert.deepEqual([...c.suchgangFundLuecken(zwei)], ['stein']);

  // Ersatzort: Beginn, sonst Mitte der Route
  const ohneOrt = c.suchgangNeu({ arten: ['stein'], daten });
  assert.deepEqual({ ...c.sucheOrt(ohneOrt, [{ lat: 52, lon: 10 }, { lat: 53, lon: 11 }]) },
                   { lat: 52.5, lon: 10.5 });
  assert.equal(c.sucheOrt(ohneOrt, []), null);
  assert.deepEqual({ ...c.sucheOrt(sg) }, { lat: 52.4, lon: 10.7 });

  // Dauer im Tagebuch: Suchdauer vor Wegdauer, sonst unbekannt
  assert.equal(c.suchgangDauerText({ suchdauer_min: 45, beginn: 'x', ende: 'y' }), '45 min gesucht');
  assert.equal(c.suchgangDauerText({ beginn: '2026-09-23T08:00:00Z', ende: '2026-09-23T09:30:00Z' }),
               '90 min unterwegs');
  assert.equal(c.suchgangDauerText({ beginn: null, ende: null }), 'Dauer unbekannt');

  console.log('test_suchgang: alle Pruefungen bestanden');
})().catch(e => { console.error(e); process.exit(1); });
