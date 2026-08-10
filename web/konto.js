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
    el.innerHTML = `<button class="tag" onclick="zeigeTagebuch()">
        Tagebuch</button>
      <button class="tag" id="aufnahme" onclick="routeUmschalten()">
        &#9679; Route aufzeichnen</button>
      <button class="tag" onclick="abmelden()">abmelden</button>`;
    if (karte) ladeEigeneFunde();
  } else {
    el.innerHTML = `<button class="tag" onclick="zeigeAnmeldung()">
        anmelden</button>`;
  }
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
    notiz: document.getElementById("routennotiz").value || null
  });

  if (error) {
    melde("Konnte nicht speichern: " + error.message);
  } else {
    kastenZu();
    melde("Route gespeichert.");
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
    .select("id, art, gefunden_am, nullfund, anzahl, notiz, ort")
    .order("gefunden_am", { ascending: false })
    .limit(500);

  if (error || !data) return;
  eigeneFunde = data;

  const punkte = {
    type: "FeatureCollection",
    features: data.filter(f => f.ort).map(f => {
      // PostGIS liefert die Geometrie als GeoJSON-Objekt
      const g = typeof f.ort === "string" ? JSON.parse(f.ort) : f.ort;
      return {
        type: "Feature",
        properties: {
          art: (D.arten[f.art] || {}).name || f.art,
          datum: new Date(f.gefunden_am).toLocaleDateString("de-DE"),
          null: f.nullfund ? 1 : 0,
          anzahl: f.anzahl || "",
          notiz: f.notiz || ""
        },
        geometry: g
      };
    })
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

// ---- Tagebuch -------------------------------------------------------

async function zeigeTagebuch() {
  kasten('<h3>Tagebuch</h3><p class="klein">Wird geladen ...</p>');

  const [routen, funde, zahlen] = await Promise.all([
    sb.from("route").select("*").order("begonnen", { ascending: false })
      .limit(30),
    sb.from("fund").select("*").order("gefunden_am", { ascending: false })
      .limit(30),
    sb.rpc("meine_zahlen")
  ]);

  const z = (zahlen.data && zahlen.data[0]) || {};

  const routenListe = (routen.data || []).map(r => `
    <div class="eintrag">
      <b>${r.titel || "ohne Titel"}</b>
      <div class="klein">${new Date(r.begonnen).toLocaleDateString("de-DE")}
        &middot; ${r.laenge_km || "?"} km &middot; ${r.dauer_min || "?"} min</div>
      ${r.notiz ? `<div class="klein">${r.notiz}</div>` : ""}
    </div>`).join("") || '<p class="klein">Noch keine Routen.</p>';

  const fundListe = (funde.data || []).map(f => {
    const g = f.ort
      ? (typeof f.ort === "string" ? JSON.parse(f.ort) : f.ort)
      : null;
    const knopf = g && g.coordinates
      ? `<button class="zeigen" onclick="zeigeFundAufKarte(
           ${g.coordinates[1]}, ${g.coordinates[0]})">Auf der Karte
         </button>`
      : "";
    return `<div class="eintrag">
      <div class="kopfzeile">
        <b>${f.nullfund ? "nichts gefunden" : f.art}</b>${knopf}
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
