/*
 * Anmeldung, Routenaufzeichnung und Fundtagebuch.
 *
 * Wird von index.html eingebunden. Ohne Supabase-Zugangsdaten in
 * konto_konfig.js bleibt alles ausgeblendet - die Karte funktioniert
 * dann wie bisher.
 */

let sb = null;             // Supabase-Verbindung
let benutzer = null;       // angemeldeter Benutzer
let aufzeichnung = null;   // laufende Routenaufzeichnung

// ---- Verbindung -----------------------------------------------------

async function kontoStarten() {
  if (typeof SUPABASE_URL === "undefined" || !SUPABASE_URL) return;

  sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

  const { data } = await sb.auth.getSession();
  benutzer = data.session ? data.session.user : null;

  sb.auth.onAuthStateChange((_, sitzung) => {
    benutzer = sitzung ? sitzung.user : null;
    zeigeKontostand();
  });

  document.getElementById("kontoleiste").hidden = false;
  zeigeKontostand();
}

function zeigeKontostand() {
  const el = document.getElementById("kontostand");
  if (!el) return;

  if (benutzer) {
    // Ein Knopf statt dreier - der Rest steht im Menue dahinter
    let name = (benutzer.email || "").split("@")[0];
    if (name.length > 12) name = name.slice(0, 11) + "\u2026";
    el.innerHTML = `<button class="tag an" onclick="zeigeKontomenue()"
      title="${benutzer.email}">&#9679; ${name}</button>`;
    if (karte) ladeEigeneFunde();
    zeigeRoutenknopf();
    zeigeRoutenschalter();
    ladeRouten();
    pruefeMitleser().then(() => setzeAnsicht(ladeAnsicht(), false));
  } else {
    el.innerHTML = `<button class="tag" onclick="zeigeAnmeldung()">
        anmelden</button>`;
    zeigeRoutenknopf();
    istMitleser = false;
    fremdeSichtbar = false;
    zeigeMitleserknopf();
    zeigeRoutenschalter();
  }
}

function zeigeKontomenue() {
  kasten(`
    <h3>${(benutzer.email || "").split("@")[0]}</h3>
    <p class="klein">${benutzer.email}</p>
    <button class="voll" onclick="zeigeTagebuch()">Tagebuch</button>
    <button class="voll leer" onclick="kastenZu(); routeUmschalten()">
      ${aufzeichnung ? "Aufzeichnung beenden" : "Route aufzeichnen"}
    </button>
    <button class="voll leer" onclick="abmelden()">Abmelden</button>
  `);
}

// ---- Anmeldung ------------------------------------------------------

function zeigeAnmeldung() {
  kasten(`
    <h3>Anmelden</h3>
    <input type="email" id="epost" placeholder="deine@email.de"
           autocomplete="email" inputmode="email">
    <input type="password" id="passwort" placeholder="Passwort"
           autocomplete="current-password">
    <button class="voll" onclick="anmelden()">Anmelden</button>
    <button class="voll leer" onclick="zeigeRegistrierung()">
      Noch kein Konto? Hier anlegen</button>
    <p class="klein" id="anmeldehinweis"></p>
  `);

  // Mit Enter abschicken
  const feld = document.getElementById("passwort");
  if (feld) feld.onkeydown = e => { if (e.key === "Enter") anmelden(); };
}

function zeigeRegistrierung() {
  kasten(`
    <h3>Konto anlegen</h3>
    <p class="klein">Nur freigeschaltete Adressen bekommen ein
    Konto.</p>
    <input type="email" id="epost" placeholder="deine@email.de"
           autocomplete="email" inputmode="email">
    <input type="password" id="passwort" placeholder="Passwort, mindestens 8 Zeichen"
           autocomplete="new-password">
    <button class="voll" onclick="registrieren()">Konto anlegen</button>
    <button class="voll leer" onclick="zeigeAnmeldung()">Zurück</button>
    <p class="klein" id="anmeldehinweis"></p>
  `);

  const feld = document.getElementById("passwort");
  if (feld) feld.onkeydown = e => {
    if (e.key === "Enter") registrieren();
  };
}

function anmeldedaten() {
  const adresse = (document.getElementById("epost").value || "").trim();
  const passwort = document.getElementById("passwort").value || "";
  const hinweis = document.getElementById("anmeldehinweis");

  if (!adresse || !passwort) {
    hinweis.textContent = "Bitte beides ausfüllen.";
    return null;
  }
  return { adresse, passwort, hinweis };
}

function fehlertext(meldung) {
  // Supabase antwortet auf Englisch - die haeufigsten Faelle
  // uebersetzen, damit man weiss, was zu tun ist
  const m = (meldung || "").toLowerCase();
  if (m.includes("invalid login")) {
    return "E-Mail oder Passwort stimmt nicht.";
  }
  if (m.includes("already registered")) {
    return "Für diese Adresse gibt es schon ein Konto - "
         + "dann oben anmelden.";
  }
  if (m.includes("nicht freigeschaltet")) {
    return "Diese Adresse ist nicht freigeschaltet. Sie muss in "
         + "Supabase in der Tabelle 'erlaubt' stehen.";
  }
  if (m.includes("password") && m.includes("6")) {
    return "Das Passwort ist zu kurz.";
  }
  if (m.includes("email not confirmed")) {
    return "Die Adresse ist noch nicht bestätigt. In Supabase unter "
         + "Authentication → Providers die Bestätigung abschalten.";
  }
  return meldung;
}

async function anmelden() {
  const d = anmeldedaten();
  if (!d) return;

  d.hinweis.textContent = "Melde an ...";
  const { error } = await sb.auth.signInWithPassword({
    email: d.adresse, password: d.passwort
  });

  if (error) {
    d.hinweis.textContent = fehlertext(error.message);
    return;
  }
  kastenZu();
  melde("Angemeldet.");
}

async function registrieren() {
  const d = anmeldedaten();
  if (!d) return;

  if (d.passwort.length < 8) {
    d.hinweis.textContent = "Mindestens 8 Zeichen.";
    return;
  }

  d.hinweis.textContent = "Lege an ...";
  const { data, error } = await sb.auth.signUp({
    email: d.adresse, password: d.passwort
  });

  if (error) {
    d.hinweis.textContent = fehlertext(error.message);
    return;
  }

  if (data.session) {
    kastenZu();
    melde("Konto angelegt und angemeldet.");
    return;
  }

  // Ohne Sitzung: Supabase verlangt eine Bestaetigung per Mail
  d.hinweis.innerHTML =
    "Konto angelegt. Supabase verlangt noch eine Bestätigung per "
    + "E-Mail.<br>Abschalten geht in Supabase unter "
    + "<b>Authentication → Providers → Email</b>, dort "
    + "<b>Confirm email</b> aus.";
}

async function abmelden() {
  if (aufzeichnung) routeUmschalten();
  await sb.auth.signOut();
  kastenZu();
  melde("Abgemeldet.");
}

// ---- Routenknopf auf der Karte --------------------------------------
//
// Als Kartensteuerung unter dem Standortknopf - dort sucht man ihn,
// wenn man unterwegs ist. Das Symbol ist ein Wegverlauf; laeuft die
// Aufzeichnung, wird daraus ein rotes Viereck zum Beenden.

let routenknopf = null;

const SYMBOL_WEG =
  '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
  'stroke-linejoin="round">' +
  '<path d="M4 20c0-3 3-4 6-4s6-1 6-4-3-4-6-4"/>' +
  '<circle cx="4" cy="20" r="1.6" fill="currentColor"/>' +
  '<circle cx="19" cy="6" r="1.6" fill="currentColor"/></svg>';

const SYMBOL_STOPP =
  '<svg viewBox="0 0 24 24" width="18" height="18">' +
  '<rect x="6" y="6" width="12" height="12" rx="2" fill="#c0392b"/>' +
  '</svg>';

function zeigeRoutenknopf() {
  if (!karte) return;

  if (!routenknopf) {
    const steuerung = {
      onAdd() {
        const kasten = document.createElement("div");
        kasten.className = "maplibregl-ctrl maplibregl-ctrl-group";
        const knopf = document.createElement("button");
        knopf.type = "button";
        knopf.id = "routenknopf";
        knopf.title = "Route aufzeichnen";
        knopf.innerHTML = SYMBOL_WEG;
        knopf.onclick = () => routeUmschalten();
        kasten.appendChild(knopf);
        return kasten;
      },
      onRemove() {}
    };
    karte.addControl(steuerung, "top-right");
    routenknopf = true;
  }

  const knopf = document.getElementById("routenknopf");
  if (knopf) knopf.hidden = !benutzer;
}

// ---- Routenaufzeichnung ---------------------------------------------
//
// Der Browser verfolgt die Position, solange die Seite im Vordergrund
// ist. Wird sie in den Hintergrund geschoben oder das Telefon
// gesperrt, hoert die Aufzeichnung auf - das ist bei Webseiten so.
// Fuer ein bis zwei Stunden mit gelegentlichem Draufschauen reicht es.

function routeUmschalten() {
  if (aufzeichnung) {
    routeBeenden();
  } else {
    routeBeginnen();
  }
}

// Wie viele Rohpositionen zu einem Punkt zusammengefasst werden.
// watchPosition liefert etwa jede Sekunde einen Wert, und der
// springt: bei Baumbestand sind 10 bis 20 Meter Streuung normal,
// obwohl man stillsteht. Ein Mittel aus mehreren Werten glaettet
// das, ohne die Strecke zu verfaelschen.
const GLAETTUNG = 8;

// Rohpositionen mit schlechterer Genauigkeit als das hier ganz
// verwerfen - unter Kronendach kommen gelegentlich Werte mit
// 50 Metern Unsicherheit.
const MAX_UNGENAU = 35;

function routeBeginnen() {
  if (!navigator.geolocation) {
    melde("Dieser Browser kennt keine Standortbestimmung.");
    return;
  }

  aufzeichnung = {
    beginn: new Date(),
    punkte: [],
    puffer: [],
    verworfen: 0,
    wache: null,
    km: 0
  };

  aufzeichnung.wache = navigator.geolocation.watchPosition(
    p => rohposition(p),
    fehler => {
      melde("Standort nicht verfuegbar: " + fehler.message);
      routeBeenden(true);
    },
    { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 }
  );

  if (navigator.wakeLock) {
    navigator.wakeLock.request("screen")
      .then(w => { aufzeichnung.wach = w; })
      .catch(() => {});
  }

  zeigeAufnahmestand();
  melde("Aufzeichnung laeuft. Die Seite muss offen bleiben.", 8000);
}

function rohposition(p) {
  if (!aufzeichnung) return;

  const genau = p.coords.accuracy;
  if (genau && genau > MAX_UNGENAU) {
    aufzeichnung.verworfen++;
    zeigeAufnahmestand();
    return;
  }

  aufzeichnung.puffer.push({
    lat: p.coords.latitude,
    lon: p.coords.longitude,
    // Genauere Messungen staerker gewichten
    gewicht: 1 / Math.max(3, genau || 10)
  });

  if (aufzeichnung.puffer.length >= GLAETTUNG) {
    mittelwertPunkt();
  }
  zeigeAufnahmestand();
}

function mittelwertPunkt() {
  const puffer = aufzeichnung.puffer;
  if (!puffer.length) return;

  // Gewichtetes Mittel - genauere Messungen zaehlen mehr
  let sg = 0, slat = 0, slon = 0;
  puffer.forEach(r => {
    sg += r.gewicht;
    slat += r.lat * r.gewicht;
    slon += r.lon * r.gewicht;
  });

  const punkt = {
    lat: +(slat / sg).toFixed(6),
    lon: +(slon / sg).toFixed(6),
    t: Math.round((Date.now() - aufzeichnung.beginn) / 1000)
  };
  aufzeichnung.puffer = [];

  const letzter = aufzeichnung.punkte[aufzeichnung.punkte.length - 1];
  if (letzter) {
    const d = abstandKm(letzter.lat, letzter.lon, punkt.lat, punkt.lon);
    // Unter 10 m ist Rauschen, ueber 300 m in kurzer Zeit ein Sprung
    if (d < 0.010) return;
    if (d > 0.3 && punkt.t - letzter.t < 20) {
      aufzeichnung.verworfen++;
      return;
    }
    aufzeichnung.km += d;
  }

  aufzeichnung.punkte.push(punkt);
  zeichneRoute();
}

function zeichneRoute() {
  if (!karte || !aufzeichnung || aufzeichnung.punkte.length < 2) return;

  const linie = {
    type: "Feature",
    geometry: {
      type: "LineString",
      coordinates: aufzeichnung.punkte.map(p => [p.lon, p.lat])
    }
  };

  if (karte.getSource("route")) {
    karte.getSource("route").setData(linie);
  } else {
    karte.addSource("route", { type: "geojson", data: linie });
    karte.addLayer({
      id: "route", type: "line", source: "route",
      paint: {
        "line-color": "#5fb763", "line-width": 4, "line-opacity": 0.85
      },
      layout: { "line-cap": "round", "line-join": "round" }
    });
  }
}

function zeigeAufnahmestand() {
  const knopf = document.getElementById("routenknopf");
  if (knopf) {
    knopf.innerHTML = aufzeichnung ? SYMBOL_STOPP : SYMBOL_WEG;
    knopf.title = aufzeichnung
      ? "Aufzeichnung beenden" : "Route aufzeichnen";
    knopf.classList.toggle("laeuft", !!aufzeichnung);
  }

  const anzeige = document.getElementById("routenstand");
  if (aufzeichnung) {
    const min = Math.round((Date.now() - aufzeichnung.beginn) / 60000);
    const text = `${aufzeichnung.km.toFixed(1)} km \u00B7 ${min} min `
               + `\u00B7 ${aufzeichnung.punkte.length} Punkte`;
    if (anzeige) {
      anzeige.textContent = text;
      anzeige.hidden = false;
    } else {
      const el = document.createElement("div");
      el.id = "routenstand";
      el.className = "routenstand";
      el.textContent = text;
      document.getElementById("karte").appendChild(el);
    }
  } else if (anzeige) {
    anzeige.hidden = true;
  }

  const b = document.getElementById("aufnahme");
  if (!b) return;
  if (!aufzeichnung) {
    b.textContent = "\u25CF Route aufzeichnen";
    b.classList.remove("aktiv");
    return;
  }
  const min = Math.round((Date.now() - aufzeichnung.beginn) / 60000);
  const punkte = aufzeichnung.punkte.length;
  b.textContent = `\u25A0 ${aufzeichnung.km.toFixed(1)} km \u00B7 `
                + `${min} min \u00B7 ${punkte}P`;
  b.classList.add("aktiv");
}

function routeBeenden(stillschweigend) {
  if (!aufzeichnung) return;

  // Angefangenen Puffer noch verwerten
  if (aufzeichnung.puffer && aufzeichnung.puffer.length >= 3) {
    mittelwertPunkt();
  }

  navigator.geolocation.clearWatch(aufzeichnung.wache);
  if (aufzeichnung.wach) {
    try { aufzeichnung.wach.release(); } catch (e) {}
  }

  const fertig = aufzeichnung;
  aufzeichnung = null;
  zeigeAufnahmestand();

  if (stillschweigend || fertig.punkte.length < 3) {
    // Die gezeichnete Linie mit entfernen - sonst bleibt ein
    // gruener Strich auf der Karte stehen
    loescheRoutenlinie();
    if (!stillschweigend) melde("Zu wenige Punkte - nicht gespeichert.");
    return;
  }

  const min = Math.round((Date.now() - fertig.beginn) / 60000);
  kasten(`
    <h3>Route speichern</h3>
    <p class="klein">${fertig.km.toFixed(1)} km in ${min} Minuten,
    ${fertig.punkte.length} Punkte</p>
    <input type="text" id="routentitel" placeholder="Wo warst du?"
           value="${new Date().toLocaleDateString("de-DE")}">
    <textarea id="routennotiz" rows="2"
      placeholder="Notiz (was gesehen, was gefunden)"></textarea>
    <button class="voll" onclick='routeSpeichern(${JSON.stringify(
      { km: fertig.km, min: min, beginn: fertig.beginn,
        punkte: fertig.punkte })})'>Speichern</button>
    <button class="voll leer" onclick="kastenZu()">Verwerfen</button>
  `);
}

function loescheRoutenlinie() {
  if (!karte) return;
  if (karte.getLayer("route")) karte.removeLayer("route");
  if (karte.getSource("route")) karte.removeSource("route");
}

async function routeSpeichern(daten) {
  if (!sb || !benutzer) {
    melde("Nicht angemeldet.");
    return;
  }

  const linie = "LINESTRING(" +
    daten.punkte.map(p => `${p.lon} ${p.lat}`).join(",") + ")";

  const { error } = await sb.from("route").insert({
    benutzer: benutzer.id,
    titel: document.getElementById("routentitel").value || null,
    begonnen: daten.beginn,
    beendet: new Date().toISOString(),
    weg: linie,
    laenge_km: +daten.km.toFixed(2),
    dauer_min: daten.min,
    punkte: daten.punkte,
    start_lat: daten.punkte[0] ? daten.punkte[0].lat : null,
    start_lon: daten.punkte[0] ? daten.punkte[0].lon : null,
    notiz: document.getElementById("routennotiz").value || null
  });

  if (error) {
    melde("Konnte nicht speichern: " + error.message);
  } else {
    kastenZu();
    loescheRoutenlinie();
    melde("Route gespeichert.");
    ladeRouten();
  }
}



// ---- Helle und dunkle Karte -----------------------------------------
//
// Die Wahl haengt am Konto, nicht am Geraet - wer sich auf dem
// Telefon anmeldet, bekommt dieselbe Ansicht wie am Rechner. Ohne
// Anmeldung merkt sich der Browser die Wahl fuer sich.

let hell = false;

function ladeAnsicht() {
  // Erst das Konto fragen, sonst den Browser
  if (benutzer && benutzer.einstellungen
      && typeof benutzer.einstellungen.hell === "boolean") {
    return benutzer.einstellungen.hell;
  }
  try {
    return localStorage.getItem("pilzkarte_hell") === "1";
  } catch (e) {
    return false;
  }
}

async function setzeAnsicht(neuHell, speichern) {
  hell = neuHell;
  document.body.classList.toggle("hell", hell);

  if (karte) {
    const teil = hell ? "light" : "dark";
    ["grund", "beschriftung"].forEach(quelle => {
      const q = karte.getSource(quelle);
      if (!q) return;
      const endung = quelle === "grund" ? "nolabels" : "only_labels";
      q.setTiles(["a", "b", "c"].map(x =>
        `https://${x}.basemaps.cartocdn.com/${teil}_${endung}/` +
        `{z}/{x}/{y}.png`));
    });
  }

  const knopf = document.querySelector("[data-ansicht-hell]");
  if (knopf) knopf.textContent = hell ? "dunkel" : "hell";

  if (!speichern) return;

  try {
    localStorage.setItem("pilzkarte_hell", hell ? "1" : "0");
  } catch (e) {}

  if (sb && benutzer) {
    await sb.from("profile")
      .update({ einstellungen: { hell: hell } })
      .eq("id", benutzer.id);
  }
}

function ansichtUmschalten() {
  setzeAnsicht(!hell, true);
}


// ---- Funde und Routen aller Nutzer ----------------------------------
//
// Nur fuer Mitleser. Wird auf Wunsch eingeblendet.

let istMitleser = false;
let fremdeSichtbar = false;

async function pruefeMitleser() {
  if (!sb || !benutzer) {
    istMitleser = false;
    return;
  }
  const { data } = await sb.from("profile")
    .select("mitleser, einstellungen").eq("id", benutzer.id).single();
  istMitleser = !!(data && data.mitleser);
  if (data && data.einstellungen) {
    benutzer.einstellungen = data.einstellungen;
  }
  zeigeMitleserknopf();
}

function zeigeMitleserknopf() {
  const leiste = document.getElementById("darstellung");
  if (!leiste) return;
  let b = leiste.querySelector("[data-schalter=fremde]");

  if (!istMitleser) {
    if (b) b.remove();
    return;
  }
  if (b) return;

  b = document.createElement("button");
  b.className = "tag";
  b.dataset.schalter = "fremde";
  b.innerHTML = "&#9679; alle Nutzer";
  b.onclick = () => {
    fremdeSichtbar = !fremdeSichtbar;
    b.classList.toggle("aktiv", fremdeSichtbar);
    ladeFremdeDaten();
  };
  leiste.appendChild(b);
}

async function ladeFremdeDaten() {
  if (!sb || !karte) return;

  const sichtbar = fremdeSichtbar ? "visible" : "none";
  ["fremde_funde", "fremde_routen"].forEach(e => {
    if (karte.getLayer(e)) {
      karte.setLayoutProperty(e, "visibility", sichtbar);
    }
  });
  if (!fremdeSichtbar) return;

  // Funde anderer
  const { data: funde } = await sb.from("fund")
    .select("art, gefunden_am, nullfund, anzahl, notiz, lat, lon, benutzer")
    .neq("benutzer", benutzer.id)
    .order("gefunden_am", { ascending: false }).limit(1000);

  const fundpunkte = {
    type: "FeatureCollection",
    features: (funde || [])
      .filter(f => f.lat != null && f.lon != null)
      .map(f => ({
        type: "Feature",
        properties: {
          art: (D.arten[f.art] || {}).name || f.art,
          datum: new Date(f.gefunden_am).toLocaleDateString("de-DE"),
          null: f.nullfund ? 1 : 0,
          anzahl: f.anzahl || "",
          notiz: f.notiz || ""
        },
        geometry: { type: "Point", coordinates: [f.lon, f.lat] }
      }))
  };

  if (karte.getSource("fremde_funde")) {
    karte.getSource("fremde_funde").setData(fundpunkte);
  } else {
    karte.addSource("fremde_funde", { type: "geojson",
                                      data: fundpunkte });
    karte.addLayer({
      id: "fremde_funde", type: "circle", source: "fremde_funde",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"],
          10, 6, 13, 9, 16, 12],
        "circle-color": ["case", ["==", ["get", "null"], 1],
          "rgba(0,0,0,0)", "#e8a33d"],
        "circle-stroke-width": 2.5,
        "circle-stroke-color": "#4a3410"
      }
    });
    karte.on("click", "fremde_funde", e => {
      const p = e.features[0].properties;
      new maplibregl.Popup({ maxWidth: "240px" })
        .setLngLat(e.features[0].geometry.coordinates)
        .setHTML(`<div class="pop">
          <b>${p.null == 1 ? "Nichts gefunden" : p.art}</b>
          <div class="lage">${p.datum} &middot; anderer Nutzer</div>
          ${p.notiz ? `<div class="klein">${p.notiz}</div>` : ""}
        </div>`).addTo(karte);
    });
  }

  // Routen anderer
  const { data: routen } = await sb.from("route")
    .select("titel, begonnen, punkte, benutzer")
    .neq("benutzer", benutzer.id)
    .order("begonnen", { ascending: false }).limit(200);

  const linien = {
    type: "FeatureCollection",
    features: (routen || [])
      .filter(r => Array.isArray(r.punkte) && r.punkte.length > 1)
      .map(r => ({
        type: "Feature",
        properties: { titel: r.titel || "Route" },
        geometry: {
          type: "LineString",
          coordinates: r.punkte.map(p => [p.lon, p.lat])
        }
      }))
  };

  if (karte.getSource("fremde_routen")) {
    karte.getSource("fremde_routen").setData(linien);
  } else {
    karte.addSource("fremde_routen", { type: "geojson", data: linien });
    karte.addLayer({
      id: "fremde_routen", type: "line", source: "fremde_routen",
      paint: { "line-color": "#e8a33d", "line-width": 2.5,
               "line-opacity": 0.6, "line-dasharray": [2, 1.5] },
      layout: { "line-cap": "round", "line-join": "round" }
    }, karte.getLayer("fremde_funde") ? "fremde_funde" : undefined);
  }
}

// ---- Fund eintragen -------------------------------------------------
//
// Der wichtigste Teil: Was hier gesammelt wird, gibt es sonst
// nirgends. Vor allem die Nullfunde - "war hier, nichts gefunden".
// Ohne sie lassen sich die Schwellen der Karte nur einseitig pruefen.

let fundOrt = null;

function fundBeginnen(lat, lon, zelle, score) {
  if (!benutzer) {
    melde("Erst anmelden, dann lassen sich Funde eintragen.");
    return;
  }
  fundOrt = { lat, lon, zelle, score };

  const heute = new Date().toISOString().slice(0, 10);
  const arten = Object.entries(D.arten)
    .map(([a, e]) => `<option value="${a}">${e.name}</option>`).join("");

  kasten(`
    <h3>Fund eintragen</h3>
    <p class="klein">${lat.toFixed(5)}, ${lon.toFixed(5)}</p>

    <select id="fundart" onchange="fundArtWechsel()">${arten}
      <option value="__eigene">— andere Art, selbst eintragen —</option>
    </select>
    <input type="text" id="fundeigene" placeholder="Welcher Pilz?"
           hidden>
    <input type="date" id="funddatum" value="${heute}">
    <input type="number" id="fundanzahl" placeholder="Wie viele? (kann leer bleiben)" min="1">
    <textarea id="fundnotiz" rows="2"
      placeholder="Notiz: Bestand, Bodenbeschaffenheit, Besonderheiten"></textarea>

    <button class="voll" onclick="fundSpeichern(false)">Fund speichern</button>
    <button class="voll leer" onclick="fundSpeichern(true)">
      Nichts gefunden &ndash; auch eintragen</button>
    <p class="klein" style="margin-top:10px">Ein Nullfund ist genauso
    wertvoll wie ein Fund: Er sagt, dass die Bedingungen hier nicht
    gereicht haben. Solche Daten gibt es sonst nirgends.</p>
  `);
}

function fundArtWechsel() {
  const wahl = document.getElementById("fundart").value;
  const feld = document.getElementById("fundeigene");
  feld.hidden = wahl !== "__eigene";
  if (!feld.hidden) feld.focus();
}

async function fundSpeichern(nullfund) {
  if (!sb || !benutzer || !fundOrt) return;

  let art = document.getElementById("fundart").value;
  if (art === "__eigene") {
    art = (document.getElementById("fundeigene").value || "").trim();
    if (!art && !nullfund) {
      melde("Bitte den Pilznamen eintragen.");
      return;
    }
    art = art || "unbekannt";
  }
  const datum = document.getElementById("funddatum").value;
  const anzahl = document.getElementById("fundanzahl").value;
  const notiz = document.getElementById("fundnotiz").value;

  const { error } = await sb.from("fund").insert({
    benutzer: benutzer.id,
    art: art,
    gefunden_am: datum,
    anzahl: nullfund ? null : (anzahl ? +anzahl : null),
    ort: `POINT(${fundOrt.lon} ${fundOrt.lat})`,
    nullfund: nullfund,
    notiz: notiz || null,
    zelle: fundOrt.zelle || null,
    score: fundOrt.score ?? null
  });

  if (error) {
    melde("Konnte nicht speichern: " + error.message);
    return;
  }

  kastenZu();
  melde(nullfund ? "Nullfund eingetragen." : "Fund eingetragen.");
  ladeEigeneFunde();
}

// ---- Eigene Funde auf der Karte -------------------------------------

let eigeneFunde = [];

function fundeSichtbar() {
  const b = document.querySelector("[data-schalter=funde]");
  return b ? b.classList.contains("aktiv") : false;
}

async function ladeEigeneFunde() {
  if (!sb || !benutzer || !karte) return;

  const { data, error } = await sb.from("fund")
    .select("id, art, gefunden_am, nullfund, anzahl, notiz, lat, lon")
    .order("gefunden_am", { ascending: false })
    .limit(500);

  if (error || !data) return;
  eigeneFunde = data;

  const punkte = {
    type: "FeatureCollection",
    features: data.filter(f => f.lat != null && f.lon != null).map(f => ({
      type: "Feature",
      properties: {
        art: (D.arten[f.art] || {}).name || f.art,
        datum: new Date(f.gefunden_am).toLocaleDateString("de-DE"),
        null: f.nullfund ? 1 : 0,
        anzahl: f.anzahl || "",
        notiz: f.notiz || ""
      },
      geometry: { type: "Point", coordinates: [f.lon, f.lat] }
    }))
  };

  if (karte.getSource("eigene")) {
    karte.getSource("eigene").setData(punkte);
    return;
  }

  karte.addSource("eigene", { type: "geojson", data: punkte });

  // Eigene Funde in Gruen, Nullfunde als leerer Ring
  karte.addLayer({
    id: "eigene", type: "circle", source: "eigene",
    // Zusammen mit den belegten Funden ein- und ausschalten
    layout: { visibility: fundeSichtbar() ? "visible" : "none" },
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"],
        10, 6, 13, 9, 16, 12],
      "circle-color": ["case", ["==", ["get", "null"], 1],
        "rgba(0,0,0,0)", "#5fb763"],
      "circle-stroke-width": 2.5,
      "circle-stroke-color": ["case", ["==", ["get", "null"], 1],
        "#9aa0a6", "#1a3320"]
    }
  });

  karte.on("click", "eigene", e => {
    const p = e.features[0].properties;
    new maplibregl.Popup({ maxWidth: "240px" })
      .setLngLat(e.features[0].geometry.coordinates)
      .setHTML(`<div class="pop">
        <b>${p.null == 1 ? "Nichts gefunden" : p.art}</b>
        <div class="lage">${p.datum}${p.anzahl
          ? " &middot; " + p.anzahl + " Stück" : ""}</div>
        ${p.notiz ? `<div class="klein">${p.notiz}</div>` : ""}
      </div>`)
      .addTo(karte);
  });
  karte.on("mouseenter", "eigene",
    () => karte.getCanvas().style.cursor = "pointer");
  karte.on("mouseleave", "eigene",
    () => karte.getCanvas().style.cursor = "");
}


// ---- Gespeicherte Routen auf der Karte ------------------------------
//
// Mit Laufrichtung: kleine Pfeile entlang der Linie, dazu ein
// gruener Punkt am Anfang und ein roter am Ende. Ohne das sieht man
// zwar den Weg, weiss aber nicht, wo er begann - bei einer
// Rundstrecke ist das der halbe Sinn.

let routenSichtbar = false;

async function ladeRouten() {
  if (!sb || !benutzer || !karte) return;

  const { data, error } = await sb.from("route")
    .select("id, titel, begonnen, laenge_km, dauer_min, punkte")
    .order("begonnen", { ascending: false }).limit(100);

  if (error || !data) return;

  const linien = [];
  const enden = [];

  data.forEach(r => {
    if (!Array.isArray(r.punkte) || r.punkte.length < 2) return;
    const koord = r.punkte.map(p => [p.lon, p.lat]);

    linien.push({
      type: "Feature",
      properties: {
        titel: r.titel || "Route",
        datum: new Date(r.begonnen).toLocaleDateString("de-DE"),
        km: r.laenge_km || "?",
        min: r.dauer_min || "?"
      },
      geometry: { type: "LineString", coordinates: koord }
    });

    enden.push({
      type: "Feature",
      properties: { art: "start" },
      geometry: { type: "Point", coordinates: koord[0] }
    });
    enden.push({
      type: "Feature",
      properties: { art: "ziel" },
      geometry: { type: "Point", coordinates: koord[koord.length - 1] }
    });
  });

  const linienDaten = { type: "FeatureCollection", features: linien };
  const endDaten = { type: "FeatureCollection", features: enden };

  if (karte.getSource("routen")) {
    karte.getSource("routen").setData(linienDaten);
    karte.getSource("routen_enden").setData(endDaten);
    return;
  }

  const sichtbar = routenSichtbar ? "visible" : "none";

  karte.addSource("routen", { type: "geojson", data: linienDaten });
  karte.addSource("routen_enden", { type: "geojson", data: endDaten });

  karte.addLayer({
    id: "routen", type: "line", source: "routen",
    layout: { visibility: sichtbar, "line-cap": "round",
              "line-join": "round" },
    paint: { "line-color": "#5fb763", "line-width": 3.5,
             "line-opacity": 0.85 }
  });

  // Laufrichtung: Pfeile entlang der Linie
  karte.addLayer({
    id: "routen_pfeile", type: "symbol", source: "routen",
    layout: {
      visibility: sichtbar,
      "symbol-placement": "line",
      "symbol-spacing": 60,
      "text-field": "\u25B6",
      "text-size": 11,
      "text-font": ["Open Sans Regular"],
      "text-allow-overlap": true,
      "text-keep-upright": false,
      "text-rotation-alignment": "map"
    },
    paint: { "text-color": "#eaf6ea", "text-halo-color": "#1a3320",
             "text-halo-width": 1.5 }
  });

  // Anfang gruen, Ende rot
  karte.addLayer({
    id: "routen_enden", type: "circle", source: "routen_enden",
    layout: { visibility: sichtbar },
    paint: {
      "circle-radius": 6,
      "circle-color": ["case", ["==", ["get", "art"], "start"],
        "#5fb763", "#c0392b"],
      "circle-stroke-width": 2,
      "circle-stroke-color": "#ffffff"
    }
  });

  karte.on("click", "routen", e => {
    const p = e.features[0].properties;
    new maplibregl.Popup({ maxWidth: "240px" })
      .setLngLat(e.lngLat)
      .setHTML(`<div class="pop"><b>${p.titel}</b>
        <div class="lage">${p.datum} &middot; ${p.km} km
        &middot; ${p.min} min</div></div>`)
      .addTo(karte);
  });
  karte.on("mouseenter", "routen",
    () => karte.getCanvas().style.cursor = "pointer");
  karte.on("mouseleave", "routen",
    () => karte.getCanvas().style.cursor = "");
}

function routenAnzeigen(an) {
  routenSichtbar = an;
  ["routen", "routen_pfeile", "routen_enden"].forEach(e => {
    if (karte && karte.getLayer(e)) {
      karte.setLayoutProperty(e, "visibility", an ? "visible" : "none");
    }
  });
  const b = document.querySelector("[data-schalter=routen]");
  if (b) b.classList.toggle("aktiv", an);
}

function zeigeRoutenschalter() {
  const leiste = document.getElementById("darstellung");
  if (!leiste) return;
  let b = leiste.querySelector("[data-schalter=routen]");

  if (!benutzer) {
    if (b) b.remove();
    return;
  }
  if (b) return;

  b = document.createElement("button");
  b.className = "tag";
  b.dataset.schalter = "routen";
  b.innerHTML = "&#9679; Routen";
  b.onclick = () => routenAnzeigen(!routenSichtbar);
  leiste.appendChild(b);
}

// Eine bestimmte Route auf der Karte zeigen
async function zeigeRouteAufKarte(id, lat, lon) {
  kastenZu();
  if (!karte) return;

  await ladeRouten();
  routenAnzeigen(true);
  karte.flyTo({ center: [lon, lat], zoom: 13, duration: 900 });
}


// ---- Loeschen -------------------------------------------------------
//
// Mit Rueckfrage, weil es nicht rueckgaengig zu machen ist. Die
// Zeilenrechte in der Datenbank erlauben das Loeschen ohnehin nur
// dem Besitzer - ein Mitleser kann fremde Eintraege sehen, aber
// nicht entfernen.

const MUELLEIMER =
  '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
  'stroke-linejoin="round"><path d="M3 6h18"/>' +
  '<path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/>' +
  '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>' +
  '<path d="M10 11v6M14 11v6"/></svg>';

async function loesche(tabelle, id, beschreibung) {
  if (!sb || !benutzer) return;

  const was = tabelle === "route" ? "Diese Route" : "Diesen Eintrag";
  if (!confirm(`${was} wirklich l\u00f6schen?\n\n${beschreibung}\n\n`
             + "Das l\u00e4sst sich nicht r\u00fcckg\u00e4ngig machen.")) {
    return;
  }

  const { error } = await sb.from(tabelle).delete().eq("id", id);

  if (error) {
    melde("Konnte nicht l\u00f6schen: " + error.message);
    return;
  }

  melde(tabelle === "route" ? "Route gel\u00f6scht." : "Eintrag gel\u00f6scht.");

  // Karte und Tagebuch auffrischen
  if (tabelle === "route") {
    await ladeRouten();
  } else {
    await ladeEigeneFunde();
  }
  zeigeTagebuch();
}

// ---- Tagebuch -------------------------------------------------------

async function zeigeTagebuch() {
  kasten('<h3>Tagebuch</h3><p class="klein">Wird geladen ...</p>');

  const [routen, funde, zahlen] = await Promise.all([
    sb.from("route")
      .select("id, titel, begonnen, laenge_km, dauer_min, notiz, "
              + "start_lat, start_lon")
      .order("begonnen", { ascending: false }).limit(30),
    sb.from("fund")
      .select("id, art, gefunden_am, nullfund, anzahl, notiz, lat, lon")
      .order("gefunden_am", { ascending: false }).limit(30),
    sb.rpc("meine_zahlen")
  ]);

  const z = (zahlen.data && zahlen.data[0]) || {};

  const routenListe = (routen.data || []).map(r => {
    const knopf = (r.start_lat != null && r.start_lon != null)
      ? `<button class="zeigen" onclick="zeigeRouteAufKarte(
           '${r.id}', ${r.start_lat}, ${r.start_lon})">
         Auf der Karte</button>`
      : "";
    const titel = r.titel || "ohne Titel";
    const datum = new Date(r.begonnen).toLocaleDateString("de-DE");
    return `<div class="eintrag">
      <div class="kopfzeile"><b>${titel}</b>${knopf}
        <button class="muell" title="L\u00f6schen"
          onclick="loesche('route', '${r.id}',
            '${titel.replace(/'/g, "")} vom ${datum}, '
            + '${r.laenge_km || "?"} km')"
          >${MUELLEIMER}</button>
      </div>
      <div class="klein">${new Date(r.begonnen)
        .toLocaleDateString("de-DE")} &middot; ${r.laenge_km || "?"} km
        &middot; ${r.dauer_min || "?"} min</div>
      ${r.notiz ? `<div class="klein">${r.notiz}</div>` : ""}
    </div>`;
  }).join("") || '<p class="klein">Noch keine Routen.</p>';

  const fundListe = (funde.data || []).map(f => {
    const knopf = (f.lat != null && f.lon != null)
      ? `<button class="zeigen" onclick="zeigeFundAufKarte(
           ${f.lat}, ${f.lon})">Auf der Karte</button>`
      : "";
    const name = f.nullfund ? "nichts gefunden" : f.art;
    const datum = new Date(f.gefunden_am).toLocaleDateString("de-DE");
    return `<div class="eintrag">
      <div class="kopfzeile">
        <b>${name}</b>${knopf}
        <button class="muell" title="L\u00f6schen"
          onclick="loesche('fund', '${f.id}',
            '${name.replace(/'/g, "")} vom ${datum}')"
          >${MUELLEIMER}</button>
      </div>
      <div class="klein">${new Date(f.gefunden_am)
        .toLocaleDateString("de-DE")}${f.anzahl
        ? " &middot; " + f.anzahl + " Stück" : ""}</div>
      ${f.notiz ? `<div class="klein">${f.notiz}</div>` : ""}
    </div>`;
  }).join("") || '<p class="klein">Noch keine Funde.</p>';

  kasten(`
    <h3>Tagebuch</h3>
    <div class="zahlen">
      <span><b>${z.funde || 0}</b> Funde</span>
      <span><b>${z.arten || 0}</b> Arten</span>
      <span><b>${z.routen || 0}</b> Routen</span>
      <span><b>${(+z.km || 0).toFixed(0)}</b> km</span>
    </div>
    <h4>Routen</h4>${routenListe}
    <h4>Funde</h4>${fundListe}
    <button class="voll leer" onclick="kastenZu()">Schliessen</button>
  `);
}

// ---- Kasten ---------------------------------------------------------

function zeigeFundAufKarte(lat, lon) {
  kastenZu();
  if (!karte) return;

  // Eigene Funde einblenden, falls sie aus sind
  const b = document.querySelector("[data-schalter=funde]");
  if (b && !b.classList.contains("aktiv")) b.click();

  karte.flyTo({ center: [lon, lat], zoom: 13, duration: 900 });
}

function kasten(inhalt) {
  let el = document.getElementById("kasten");
  if (!el) {
    el = document.createElement("div");
    el.id = "kasten";
    el.className = "kasten-huelle";
    el.onclick = e => { if (e.target === el) kastenZu(); };
    document.body.appendChild(el);
  }
  el.innerHTML = `<div class="kasten-inhalt">${inhalt}</div>`;
  el.hidden = false;
}

function kastenZu() {
  const el = document.getElementById("kasten");
  if (el) el.hidden = true;
}
