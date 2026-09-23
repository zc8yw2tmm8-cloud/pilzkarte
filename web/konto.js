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

// Nur fuer HTML-Text und zitierte HTML-Attribute, nie fuer JavaScript/URLs.
// Erst bei der Ausgabe kodieren: gespeicherte Originaltexte bleiben erhalten.
function kontoHtml(wert) {
  return String(wert ?? "").replace(/[&<>"']/g, zeichen => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[zeichen]);
}

// ---- Verbindung -----------------------------------------------------

async function kontoStarten() {
  if (typeof SUPABASE_URL === "undefined" || !SUPABASE_URL) return;

  sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

  const { data } = await sb.auth.getSession();
  benutzer = data.session ? data.session.user : null;

  sb.auth.onAuthStateChange((art, sitzung) => {
    benutzer = sitzung ? sitzung.user : null;
    kontoDatenLaden();

    // Kommt jemand ueber den Link aus der Zuruecksetzen-Mail,
    // meldet Supabase diesen Fall - dann gleich nach dem neuen
    // Passwort fragen.
    if (art === "PASSWORD_RECOVERY") {
      setTimeout(zeigeNeuesPasswort, 300);
    }
  });

  document.getElementById("kontoleiste").hidden = false;
  kontoDatenLaden();
}

function zeigeKontostand() {
  // Neuer Aufbau: Der Zugang steht in der Reiterleiste unten, nicht
  // mehr oben rechts. Dort ist er mit dem Daumen erreichbar und
  // steht bei den anderen Zielen.
  const reiterName = document.getElementById("reitername");
  const reiterTagebuch = document.getElementById("reitertagebuch");

  // Bild statt Punkt im Reiter, sofern eines gewaehlt ist
  const reiterBild = document.querySelector("#reiterkonto i");
  if (reiterBild) {
    reiterBild.innerHTML = (benutzer && avatar)
      ? avatarBild(avatar, 64) : "\u25CF";
  }

  if (reiterName) {
    if (benutzer) {
      let n = anzeigename || (benutzer.email || "").split("@")[0];
      if (n.length > 10) n = n.slice(0, 9) + "\u2026";
      reiterName.textContent = n;
    } else {
      reiterName.textContent = "Anmelden";
    }
  }
  if (reiterTagebuch) reiterTagebuch.hidden = !benutzer;

  // NUR anzeigen. Keine Datenbankabfragen, keine Ladefunktionen.
  //
  // Vorher stand hier ein Aufruf von pruefeMitleser(), und
  // pruefeMitleser() rief am Ende zeigeKontostand() - ein
  // Ringaufruf, der endlos lief und bei jeder Runde die Datenbank
  // fragte. Die Konsole war voll und die Seite kam nie zur Ruhe.
  const el = document.getElementById("kontostand");
  if (!el) return;

  if (benutzer) {
    let name = anzeigename || (benutzer.email || "").split("@")[0];
    if (name.length > 12) name = name.slice(0, 11) + "\u2026";
    el.innerHTML = `<button class="tag an" onclick="zeigeKontomenue()"
      title="${kontoHtml(benutzer.email)}">&#9679; ${kontoHtml(name)}</button>`;
  } else {
    el.innerHTML = `<button class="tag" onclick="zeigeAnmeldung()">
        anmelden</button>`;
  }

  zeigeRoutenknopf();
  zeigeRoutenschalter();
  zeigeMitleserknopf();
}


// Alles, was Daten braucht, steht hier - und wird genau einmal je
// An- oder Abmeldung aufgerufen.
async function kontoDatenLaden() {
  if (!benutzer) {
    istMitleser = false;
    fremdeSichtbar = false;
    anzeigename = null;
    avatar = null;
    alleRouten = [];
    wiederhergestellt = false;
    zeigeKontostand();
    return;
  }

  await pruefeMitleser();
  zeigeKontostand();

  if (karte) {
    ladeEigeneFunde();
    ladeRouten();
  }

  setTimeout(() => stelleWiederHer(ladeEinstellungen()), 250);
  // Falls nichts wiederherzustellen ist, muss trotzdem gespeichert
  // werden koennen
  setTimeout(() => { einstellungenBereit = true; }, 3000);

  // Beim ersten Anmelden nach einem Namen fragen, sonst nach einem
  // Suchgang, der auf diesem Geraet nicht abgeschlossen wurde
  if (!anzeigename) {
    setTimeout(() => zeigeNamenswahl(true), 500);
  } else {
    setTimeout(suchgangOffenPruefen, 800);
  }
}


function zeigeKontomenue() {
  kasten(`
    <div class="kontokopf">
      <button class="avatarknopf" onclick="zeigeAvatarwahl()"
              title="Bild ändern">
        ${avatar ? avatarBild(avatar, 52)
                 : '<span class="ohnebild">?</span>'}
      </button>
      <div>
        <h3>${kontoHtml(anzeigename || "ohne Namen")}
          <button class="stift" title="Name ändern"
            onclick="zeigeNamenswahl(false)">${STIFT}</button></h3>
        <p class="klein">${kontoHtml(benutzer.email)}</p>
      </div>
    </div>
    <button class="voll" onclick="zeigeTagebuch()">Tagebuch</button>
    <button class="voll leer" onclick="kastenZu(); routeUmschalten()">
      ${aufzeichnung ? "Aufzeichnung beenden" : "Pilzsuche oder Route starten"}
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
    <button class="voll leer" onclick="zeigePasswortVergessen()">
      Passwort vergessen</button>
    <p class="klein" id="anmeldehinweis"></p>
  `);

  // Mit Enter abschicken
  const feld = document.getElementById("passwort");
  if (feld) feld.onkeydown = e => { if (e.key === "Enter") anmelden(); };
}

function zeigePasswortVergessen() {
  kasten(`
    <h3>Passwort zurücksetzen</h3>
    <p class="klein">Du bekommst eine E-Mail mit einem Link. Darüber
    lässt sich ein neues Passwort setzen.</p>
    <input type="email" id="epost" placeholder="deine@email.de"
           autocomplete="email" inputmode="email">
    <button class="voll" onclick="passwortZuruecksetzen()">
      Link schicken</button>
    <button class="voll leer" onclick="zeigeAnmeldung()">Zurück</button>
    <p class="klein" id="anmeldehinweis"></p>
  `);
  const feld = document.getElementById("epost");
  if (feld) feld.onkeydown = e => {
    if (e.key === "Enter") passwortZuruecksetzen();
  };
}

async function passwortZuruecksetzen() {
  const adresse = (document.getElementById("epost").value || "").trim();
  const hinweis = document.getElementById("anmeldehinweis");
  if (!adresse) {
    hinweis.textContent = "Bitte E-Mail eintragen.";
    hinweis.className = "klein fehler";
    return;
  }

  hinweis.textContent = "Wird verschickt ...";
  hinweis.className = "klein";

  const { error } = await sb.auth.resetPasswordForEmail(adresse, {
    redirectTo: window.location.href.split("#")[0]
  });

  if (error) {
    hinweis.textContent = fehlertext(error.message);
    hinweis.className = "klein fehler";
    return;
  }
  hinweis.innerHTML = "Schau in dein Postfach. Der Link führt "
    + "hierher zurück, dann kannst du ein neues Passwort setzen.";
  hinweis.className = "klein frei";
}

function zeigeNeuesPasswort() {
  kasten(`
    <h3>Neues Passwort setzen</h3>
    <input type="password" id="passwort" autocomplete="new-password"
           placeholder="Neues Passwort, mindestens 8 Zeichen">
    <button class="voll" onclick="neuesPasswortSpeichern()">
      Speichern</button>
    <p class="klein" id="anmeldehinweis"></p>
  `);
  const feld = document.getElementById("passwort");
  if (feld) {
    feld.focus();
    feld.onkeydown = e => {
      if (e.key === "Enter") neuesPasswortSpeichern();
    };
  }
}

async function neuesPasswortSpeichern() {
  const neu = document.getElementById("passwort").value;
  const hinweis = document.getElementById("anmeldehinweis");

  if (neu.length < 8) {
    hinweis.textContent = "Mindestens 8 Zeichen.";
    hinweis.className = "klein fehler";
    return;
  }

  const { error } = await sb.auth.updateUser({ password: neu });
  if (error) {
    hinweis.textContent = fehlertext(error.message);
    hinweis.className = "klein fehler";
    return;
  }
  kastenZu();
  melde("Passwort geändert.");
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
    return "Die Adresse ist noch nicht bestätigt. Schau in dein "
         + "Postfach - dort liegt eine E-Mail mit einem Link.";
  }
  if (m.includes("rate limit") || m.includes("too many")) {
    return "Zu viele Versuche. Bitte ein paar Minuten warten.";
  }
  if (m.includes("user not found")) {
    return "Für diese Adresse gibt es kein Konto.";
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
  // Eine laufende Pilzsuche bleibt offen und wird beim naechsten
  // Anmelden zum Abschliessen angeboten
  if (aufzeichnung?.suchgang) await routeBeenden(true);
  else if (aufzeichnung) routeUmschalten();
  suchgangEnde = null;
  suchgangOffenGefragt = false;
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

    // Der Knopf kommt erst nach dem Anmelden dazu und landet sonst
    // ganz unten - die Reihenfolge muss neu gesetzt werden.
    if (typeof ordneKnoepfe === "function") ordneKnoepfe();
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
    // Erst fragen, ob es eine Pilzsuche ist - die gesuchten Arten
    // werden vor dem Gang festgelegt, nicht nachtraeglich
    suchgangStartDialog();
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

// fortsetzung: auf dem Geraet gesicherter Stand eines Suchgangs, dessen
// Seite sich unterwegs geschlossen hat
function routeBeginnen(suchgang = null, fortsetzung = null) {
  if (!navigator.geolocation) {
    melde("Dieser Browser kennt keine Standortbestimmung.");
    return false;
  }

  aufzeichnung = {
    beginn: fortsetzung ? new Date(fortsetzung.beginn) : new Date(),
    punkte: fortsetzung ? [...fortsetzung.punkte] : [],
    puffer: [],
    verworfen: 0,
    wache: null,
    km: fortsetzung ? fortsetzung.km : 0,
    suchgang
  };

  aufzeichnung.wache = navigator.geolocation.watchPosition(
    p => rohposition(p),
    fehler => {
      melde("Standort nicht verfuegbar: " + fehler.message);
      // Eine Pilzsuche wird trotzdem abgeschlossen oder verworfen
      routeBeenden(!aufzeichnung?.suchgang);
    },
    { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 }
  );

  if (navigator.wakeLock) {
    navigator.wakeLock.request("screen")
      .then(w => { aufzeichnung.wach = w; })
      .catch(() => {});
  }

  zeigeAufnahmestand();
  if (fortsetzung) zeichneRoute();
  melde(suchgang ? "Pilzsuche laeuft. Die Seite muss offen bleiben."
                 : "Aufzeichnung laeuft. Die Seite muss offen bleiben.", 8000);
  return true;
}

function rohposition(p) {
  if (!aufzeichnung) return;

  const genau = p.coords.accuracy;
  if (genau && genau > MAX_UNGENAU) {
    aufzeichnung.verworfen++;
    zeigeAufnahmestand();
    return;
  }

  // Erster brauchbarer Standort: Ort des Suchgangs und die Bewertung,
  // die die Karte dort gerade zeigt
  const sg = aufzeichnung.suchgang;
  if (sg && sg.lat == null) {
    suchgangOrt(sg, p.coords.latitude, p.coords.longitude, genau);
    suchgangSichern(sg);
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

  const suche = aufzeichnung.suchgang;
  if (suche) {
    suchgangZelleMerken(suche, punkt.lat, punkt.lon);
    suchgangMerken(aufzeichnung);
  }
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

  if (fertig.suchgang) {
    if (stillschweigend) return suchgangAnhalten(fertig);
    suchgangEndeDialog(fertig);
    return;
  }

  if (stillschweigend || fertig.punkte.length < 3) {
    // Die gezeichnete Linie mit entfernen - sonst bleibt ein
    // gruener Strich auf der Karte stehen
    loescheRoutenlinie();
    if (!stillschweigend) melde("Zu wenige Punkte - nicht gespeichert.");
    return;
  }

  const min = Math.round((Date.now() - fertig.beginn) / 60000);
  const vorwaehlen = () => {
    // Text markieren, damit Tippen ihn ersetzt statt anzuhaengen
    const feld = document.getElementById("routentitel");
    if (feld) { feld.focus(); feld.select(); }
  };
  setTimeout(vorwaehlen, 80);

  kasten(`
    <h3>Route speichern</h3>
    <p class="klein">${fertig.km.toFixed(1)} km in ${min} Minuten,
    ${fertig.punkte.length} Punkte</p>
    <input type="text" id="routentitel" placeholder="Wo warst du?"
           value="${kontoHtml(routenvorschlag(fertig.punkte))}">
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


function routenvorschlag(punkte) {
  // Aus der naechstgelegenen Kartenzelle einen Namen bauen -
  // "Wald bei Gerstenbuettel" ist brauchbarer als das Datum.
  if (!D || !D.zellen || !punkte.length) {
    return new Date().toLocaleDateString("de-DE");
  }

  // Mitte der Route
  const lat = punkte.reduce((s, p) => s + p.lat, 0) / punkte.length;
  const lon = punkte.reduce((s, p) => s + p.lon, 0) / punkte.length;

  let naechste = null, kleinster = 1e9;
  D.zellen.forEach(z => {
    const d = (z.lat - lat) ** 2 + (z.lon - lon) ** 2;
    if (d < kleinster) { kleinster = d; naechste = z; }
  });

  if (!naechste || !naechste.titel) {
    return new Date().toLocaleDateString("de-DE");
  }

  // Der Titel lautet etwa "Elm bei Koenigslutter" oder
  // "Wald 2,0 km von Bokel" - beides taugt als Routenname
  let titel = naechste.titel;
  const m = titel.match(/^Wald [\d,]+ km von (.+)$/);
  if (m) titel = "Wald bei " + m[1];

  return titel;
}

// Legt die Route an und liefert ihre Kennung - der Suchgang verweist darauf
async function routeEinfuegen(daten, min, titel, notiz) {
  const linie = "LINESTRING(" +
    daten.punkte.map(p => `${p.lon} ${p.lat}`).join(",") + ")";

  const { data, error } = await sb.from("route").insert({
    benutzer: benutzer.id,
    titel: titel || null,
    begonnen: daten.beginn,
    beendet: new Date().toISOString(),
    weg: linie,
    laenge_km: +daten.km.toFixed(2),
    dauer_min: min,
    punkte: daten.punkte,
    start_lat: daten.punkte[0] ? daten.punkte[0].lat : null,
    start_lon: daten.punkte[0] ? daten.punkte[0].lon : null,
    notiz: notiz || null
  }).select("id").single();

  if (error) throw error;
  return data ? data.id : null;
}

async function routeSpeichern(daten) {
  if (!sb || !benutzer) {
    melde("Nicht angemeldet.");
    return;
  }

  try {
    await routeEinfuegen(daten, daten.min,
      document.getElementById("routentitel").value,
      document.getElementById("routennotiz").value);
  } catch (error) {
    melde("Konnte nicht speichern: " + error.message);
    return;
  }
  kastenZu();
  loescheRoutenlinie();
  melde("Route gespeichert.");
  ladeRouten();
}


// ---- Suchgaenge -----------------------------------------------------
//
// Ein Suchgang haelt fest, wann jemand wie lange wonach gesucht hat,
// was dabei je Art herauskam - auch "nichts" - und welche Bewertung die
// Karte an den besuchten Stellen und am Tag zeigte. Nur so laesst sich
// spaeter pruefen, ob hohe Werte haeufiger zu Funden fuehren. Die
// gesuchten Arten werden vor dem Gang festgelegt, damit das Ergebnis sie
// nicht nachtraeglich beeinflusst. Ohne ausdrueckliche Angabe bleibt eine
// Art "offen" - nur so ist ein Nullfund ein echter Nullfund.

// Weiter von der naechsten Kartenzelle entfernt: keine Zuordnung
const SUCHE_ABSTAND_KM = 3;
// Obergrenze fuer die unterwegs beruehrten Zellen eines Gangs
const SUCHE_MAX_ZELLEN = 40;
// Voreinstellung fuer neue Gaenge, nur auf diesem Geraet. Gespeichert
// wird die Einwilligung je Gang mit Textstand und Zeitpunkt.
const SUCHE_ZUSTIMMUNG = "pilzkarte_suche_auswertung";
// Laufender oder nicht abgeschlossener Gang, falls die Seite schliesst
const SUCHE_OFFEN = "pilzkarte_suchgang_offen";
// Stand des Einwilligungstextes in zustimmungHaken
const EINWILLIGUNG_VERSION = "2026-09-23";
const SUCHE_ERGEBNISSE = {
  fund: "gefunden", nullfund: "nichts gefunden", offen: "offen"
};
// Spalten der Tabelle suchgang, ohne benutzer
const SUCHGANG_SPALTEN = ["id", "datum", "beginn", "ende", "suchdauer_min",
  "arten", "ergebnisse", "route", "lat", "lon", "genauigkeit_m", "zelle",
  "besuchte_zellen", "raeumlich_gemischt", "angezeigt", "datenstand",
  "config_hash", "modellversion", "versionsstatus", "auswertung_erlaubt",
  "einwilligung_version", "einwilligung_zeit", "quelle", "notiz"];

let suchgangEnde = null;
let suchgangOffenGefragt = false;

// JSON mit sortierten Schluesseln: gleiche Inhalte ergeben unabhaengig
// von der Reihenfolge in daten.json dieselbe Zeichenkette
function stabilesJson(wert) {
  if (Array.isArray(wert)) return "[" + wert.map(stabilesJson).join(",") + "]";
  if (wert && typeof wert === "object") {
    return "{" + Object.keys(wert).sort().map(k =>
      JSON.stringify(k) + ":" + stabilesJson(wert[k])).join(",") + "}";
  }
  return JSON.stringify(wert ?? null);
}

// Kennung der Bewertungsparameter, die daten.json mitliefert: die ersten
// 12 Stellen des SHA-256. Der Tageswert "saison" wechselt taeglich und
// bleibt aussen vor. Kein Fingerabdruck des ganzen Modells - Baum- und
// Bodengewichte und die Wetteraufbereitung stehen nicht in daten.json.
// Deshalb bleibt modellversion leer und versionsstatus "legacy".
async function configHashAus(arten) {
  if (!arten || !globalThis.crypto?.subtle) return null;
  const regeln = {};
  for (const [a, e] of Object.entries(arten)) {
    const { saison, ...rest } = e;
    regeln[a] = rest;
  }
  const hash = await crypto.subtle.digest("SHA-256",
    new TextEncoder().encode(stabilesJson(regeln)));
  return [...new Uint8Array(hash)].slice(0, 6)
    .map(b => b.toString(16).padStart(2, "0")).join("");
}

function kmZwischen(lat1, lon1, lat2, lon2) {
  const r = Math.PI / 180;
  const a = Math.sin((lat2 - lat1) * r / 2) ** 2 + Math.cos(lat1 * r)
    * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(a));
}

function naechsteZelle(daten, lat, lon, maxKm = SUCHE_ABSTAND_KM) {
  if (!daten || !Array.isArray(daten.zellen)) return null;
  let beste = null, km = Infinity;
  for (const z of daten.zellen) {
    const d = kmZwischen(lat, lon, z.lat, z.lon);
    if (d < km) { km = d; beste = z; }
  }
  return beste && km <= maxKm ? { zelle: beste, km } : null;
}

// Werte einer Kartenzelle fuer die gesuchten Arten an einem Tag; null,
// wenn der Tag nicht in den geladenen Daten steht
function zellWerte(daten, zelle, arten, datum) {
  const tag = (daten?.tage || []).findIndex(t => t.datum === datum);
  if (tag < 0) return null;
  const werte = {};
  for (const a of arten) {
    const w = zelle.scores?.[a]?.[tag];
    werte[a] = Number.isInteger(w) && w >= 0 && w <= 100 ? w : null;
  }
  return werte;
}

// Was zeigte die Karte am Startpunkt? Null, wenn der Ort ausserhalb der
// Karte liegt oder der Tag nicht in den geladenen Daten steht - dann ist
// die Anzeige unbekannt, nicht 0. Unterwegs beruehrte Zellen kommen mit
// suchgangZelleMerken hinzu.
function angezeigteBewertung(daten, arten, lat, lon, datum) {
  const treffer = naechsteZelle(daten, lat, lon);
  const werte = treffer && zellWerte(daten, treffer.zelle, arten, datum);
  if (!werte) return null;
  return { datenstand: daten.stand ?? null, tag: datum, bereich: "startpunkt",
           startzelle: treffer.zelle.id, abstand_km: +treffer.km.toFixed(2),
           zellen: { [treffer.zelle.id]: werte } };
}

function startwert(sg, art) {
  const a = sg.angezeigt;
  return a?.zellen?.[a.startzelle]?.[art] ?? null;
}

// Ein Startpunkt-Wert gilt nur fuer den Startpunkt. Fuehrt der Weg durch
// weitere Zellen, werden sie mit ihren Werten festgehalten und der Gang
// als raeumlich gemischt gekennzeichnet. Werte nur aus demselben
// Datenstand wie zu Beginn - laedt die Seite unterwegs neue Daten, bleibt
// die Zelle ohne Wert.
function suchgangZelleMerken(sg, lat, lon, daten = D) {
  const treffer = naechsteZelle(daten, lat, lon);
  if (!treffer) return false;
  const id = treffer.zelle.id;
  if (sg.besuchte_zellen.includes(id)
      || sg.besuchte_zellen.length >= SUCHE_MAX_ZELLEN) return false;
  sg.besuchte_zellen.push(id);
  sg.raeumlich_gemischt = sg.besuchte_zellen.length > 1;
  const a = sg.angezeigt;
  if (a && (daten.stand ?? null) === a.datenstand) {
    const werte = zellWerte(daten, treffer.zelle, sg.arten, a.tag);
    if (werte) a.zellen[id] = werte;
  }
  if (a && sg.raeumlich_gemischt) a.bereich = "besuchte_zellen";
  return true;
}

function einwilligungSetzen(sg, an) {
  sg.auswertung_erlaubt = !!an;
  sg.einwilligung_version = an ? EINWILLIGUNG_VERSION : null;
  sg.einwilligung_zeit = an ? new Date().toISOString() : null;
}

// Aufgezeichnete Gaenge haben Uhrzeiten und den Datenstand der Karte.
// Nachtraege nur das Datum: Die heutige Karte zeigt nicht mehr, was
// damals angezeigt wurde, deshalb bleiben Werte und Kennungen leer.
function suchgangNeu({ arten, einwilligung = false, quelle = "aufzeichnung",
                       beginn = new Date(), datum = null, daten = D }) {
  const nachtrag = quelle === "nachtrag";
  const sg = {
    id: crypto.randomUUID(),
    datum: nachtrag ? datum : berlinDatum(beginn),
    beginn: nachtrag ? null : new Date(beginn).toISOString(),
    ende: null, suchdauer_min: null,
    arten: [...arten],
    ergebnisse: Object.fromEntries(arten.map(a => [a, "offen"])),
    route: null, lat: null, lon: null, genauigkeit_m: null,
    zelle: null, besuchte_zellen: [], raeumlich_gemischt: false,
    angezeigt: null, datenstand: nachtrag ? null : daten?.stand || null,
    config_hash: null, modellversion: null, versionsstatus: "legacy",
    auswertung_erlaubt: false, einwilligung_version: null,
    einwilligung_zeit: null, quelle, notiz: null,
    // Nur im Browser
    funde: {}, gesichert: false, fehler: null, nullfundIds: {}
  };
  einwilligungSetzen(sg, einwilligung);
  sg.versionBereit = nachtrag ? Promise.resolve()
    : configHashAus(daten?.arten).then(v => { sg.config_hash = v; }, () => {});
  return sg;
}

// Ende hoechstens 24 Stunden nach Beginn, wie in der Datenbank verlangt
function endeBegrenzt(sg, ende) {
  const grenze = new Date(sg.beginn).getTime() + 24 * 3600000;
  return new Date(Math.min(new Date(ende).getTime(), grenze)).toISOString();
}

function suchgangOrt(sg, lat, lon, genauigkeit, daten = D) {
  sg.lat = +(+lat).toFixed(6);
  sg.lon = +(+lon).toFixed(6);
  sg.genauigkeit_m = Number.isFinite(genauigkeit) ? Math.round(genauigkeit) : null;
  const naechste = naechsteZelle(daten, sg.lat, sg.lon);
  sg.zelle = naechste ? naechste.zelle.id : null;
  if (sg.zelle && !sg.besuchte_zellen.includes(sg.zelle)) {
    sg.besuchte_zellen.push(sg.zelle);
  }
  if (sg.quelle !== "nachtrag") {
    sg.angezeigt = angezeigteBewertung(daten, sg.arten, sg.lat, sg.lon, sg.datum);
  }
}

function suchgangZeile(sg) {
  const zeile = { benutzer: benutzer.id };
  for (const s of SUCHGANG_SPALTEN) zeile[s] = sg[s] ?? null;
  return zeile;
}

function fundZahl(sg) {
  return Object.values(sg.funde || {}).reduce((s, n) => s + n, 0);
}

// Arten mit "gefunden", fuer die noch kein Fund eingetragen ist
function suchgangFundLuecken(sg) {
  return sg.arten.filter(a => sg.ergebnisse[a] === "fund" && !sg.funde[a]);
}

// ---- Suchgang auf dem Geraet sichern --------------------------------
//
// Schliesst sich die Seite unterwegs - auf dem Telefon beim Wechsel in
// eine andere App durchaus ueblich -, ginge der Weg sonst verloren.
// Gesichert wird vor jedem Netzaufruf und bei jedem neuen Wegpunkt.

function suchgangMerken(stand) {
  if (!benutzer || !stand?.suchgang) return;
  const { versionBereit, gesichert, fehler, ...sg } = stand.suchgang;
  const eintrag = {
    benutzer: benutzer.id, zuletzt: new Date().toISOString(),
    beginn: new Date(stand.beginn).toISOString(), km: stand.km || 0,
    punkte: stand.punkte || [], routeId: stand.routeId || null, suchgang: sg
  };
  try { localStorage.setItem(SUCHE_OFFEN, JSON.stringify(eintrag)); } catch (e) {}
}

// Sichert den Gang in dem Zusammenhang, in dem er gerade steckt
function suchgangStandMerken(sg) {
  if (aufzeichnung && aufzeichnung.suchgang === sg) {
    suchgangMerken(aufzeichnung);
  } else if (suchgangEnde && suchgangEnde.sg === sg) {
    suchgangMerken({ ...suchgangEnde.fertig, routeId: suchgangEnde.routeId });
  }
}

function suchgangGemerktRoh() {
  try { return JSON.parse(localStorage.getItem(SUCHE_OFFEN)); } catch (e) { return null; }
}

function suchgangGemerkt() {
  const e = suchgangGemerktRoh();
  return e && benutzer && e.benutzer === benutzer.id && e.suchgang?.id ? e : null;
}

function suchgangVergessen(id) {
  if (suchgangGemerktRoh()?.suchgang?.id !== id) return;
  try { localStorage.removeItem(SUCHE_OFFEN); } catch (e) {}
}

function suchgangAusGemerkt(eintrag) {
  return { ...eintrag.suchgang, funde: eintrag.suchgang.funde || {},
           nullfundIds: eintrag.suchgang.nullfundIds || {},
           gesichert: false, fehler: null, versionBereit: Promise.resolve() };
}

// Speichert den aktuellen Stand; die feste Kennung macht Wiederholungen
// nach Netzfehlern unschaedlich
async function suchgangSichern(sg) {
  if (!sb || !benutzer || !sg) return false;
  await sg.versionBereit;
  suchgangStandMerken(sg);
  const { error } = await sb.from("suchgang")
    .upsert(suchgangZeile(sg), { onConflict: "id" });
  sg.gesichert = !error;
  sg.fehler = error ? error.message : null;
  return !error;
}

// Nullfund nur fuer ausdruecklich verneinte Arten, damit Tagebuch,
// Zahlen und Karte es wie bisher zeigen. Feste Kennungen je Art.
async function suchgangNullfunde(sg, lat, lon) {
  const verneint = sg.arten.filter(a => sg.ergebnisse[a] === "nullfund");
  if (!verneint.length) return 0;
  const zeilen = verneint.map(a => {
    sg.nullfundIds[a] = sg.nullfundIds[a] || crypto.randomUUID();
    return {
      id: sg.nullfundIds[a], art: a, nullfund: true, anzahl: null,
      benutzer: benutzer.id, gefunden_am: sg.datum,
      ort: `POINT(${lon} ${lat})`, zelle: sg.zelle, notiz: null,
      score: startwert(sg, a), suchgang: sg.id
    };
  });
  const { error } = await sb.from("fund").upsert(zeilen, { onConflict: "id" });
  if (error) throw error;
  return zeilen.length;
}

// Ort fuer Nullfunde und nachzutragende Funde: Beginn des Suchgangs,
// sonst die Mitte der Route
function sucheOrt(sg, punkte = []) {
  if (sg.lat != null) return { lat: sg.lat, lon: sg.lon };
  if (!punkte.length) return null;
  return {
    lat: +(punkte.reduce((s, p) => s + p.lat, 0) / punkte.length).toFixed(6),
    lon: +(punkte.reduce((s, p) => s + p.lon, 0) / punkte.length).toFixed(6)
  };
}

function artName(a) {
  return (D && D.arten && D.arten[a] && D.arten[a].name) || a;
}

function artenChips(vorwahl) {
  return `<div class="suche-arten" id="suche-arten" role="group"
      aria-label="Gesuchte Arten">${Object.entries(D.arten).map(([a, e]) => {
    const an = vorwahl.has(a);
    return `<button type="button" class="tag${an ? " aktiv" : ""}"
      data-sucheart="${kontoHtml(a)}" aria-pressed="${an}">${kontoHtml(e.name)}</button>`;
  }).join("")}</div>`;
}

function artenChipsVerbinden(beiAenderung = null) {
  document.querySelectorAll("#suche-arten [data-sucheart]").forEach(b => {
    b.onclick = () => {
      const an = !b.classList.contains("aktiv");
      b.classList.toggle("aktiv", an);
      b.setAttribute("aria-pressed", String(an));
      if (beiAenderung) beiAenderung();
    };
  });
}

function gewaehlteArten() {
  return [...document.querySelectorAll("#suche-arten [data-sucheart].aktiv")]
    .map(b => b.dataset.sucheart);
}

function vorgewaehlteArten() {
  const liste = [...(typeof lieblinge !== "undefined" ? lieblinge : []),
                 typeof art === "string" ? art : null];
  return new Set(liste.filter(a => a && D.arten[a]));
}

function zustimmungHaken() {
  let an = false;
  try { an = localStorage.getItem(SUCHE_ZUSTIMMUNG) === "1"; } catch (e) {}
  return `<label class="suche-haken"><input type="checkbox" id="suche-auswertung"
    ${an ? "checked" : ""}> Diesen Suchgang zur Prüfung der Karte auswerten
    lassen. Genutzt werden Ort, Zeit, Arten und Ergebnis, nicht dein Name.
    Widerruf jederzeit im Tagebuch.</label>`;
}

function zustimmungLesen() {
  const an = document.getElementById("suche-auswertung").checked;
  try { localStorage.setItem(SUCHE_ZUSTIMMUNG, an ? "1" : "0"); } catch (e) {}
  return an;
}

// Je Art: gefunden, nichts gefunden oder offen
function ergebnisWahl(arten, vorgaben = {}) {
  return arten.map(a => {
    const wert = vorgaben[a] || "offen";
    return `<fieldset class="suche-ergebnis"><legend>${kontoHtml(artName(a))}</legend>
      <div class="suche-wahl">${Object.entries(SUCHE_ERGEBNISSE).map(([w, text]) =>
        `<label><input type="radio" name="suche-ergebnis-${kontoHtml(a)}"
          data-ergebnis="${kontoHtml(a)}" value="${w}"${w === wert ? " checked" : ""}>
          ${text}</label>`).join("")}</div>
    </fieldset>`;
  }).join("");
}

// Liest die Auswahl im Dialog und ergaenzt vorgaben damit - so bleibt
// sie erhalten, wenn der Bereich neu gezeichnet wird
function ergebnisseLesen(arten, vorgaben = {}) {
  document.querySelectorAll("#kasten input[data-ergebnis]:checked")
    .forEach(i => { vorgaben[i.dataset.ergebnis] = i.value; });
  return Object.fromEntries(arten.map(a => [a, vorgaben[a] || "offen"]));
}

function sucheFehler(text) {
  const el = document.getElementById("suche-fehler");
  el.textContent = text;
  el.hidden = !text;
}

function suchgangStartDialog() {
  if (!benutzer) return;
  if (!D || !D.arten) { routeBeginnen(); return; }
  kasten(`
    <h3>Aufzeichnung starten</h3>
    <p class="klein">Gehst du Pilze suchen? Dann wird festgehalten, welche
      Arten du suchst und was die Karte hier zeigt – auch wenn du nichts
      findest. So lässt sich später prüfen, ob die Karte stimmt.</p>
    ${artenChips(vorgewaehlteArten())}
    ${zustimmungHaken()}
    <p id="suche-fehler" class="klein fehler" role="alert" hidden></p>
    <button type="button" class="voll" id="suche-start">Pilzsuche starten</button>
    <button type="button" class="voll leer" id="suche-nur-route">Nur Route aufzeichnen</button>
    <button type="button" class="voll leer" id="suche-abbrechen">Abbrechen</button>
  `);
  artenChipsVerbinden();
  document.getElementById("suche-start").onclick = () => {
    const arten = gewaehlteArten();
    if (!arten.length) {
      sucheFehler("Bitte mindestens eine gesuchte Art wählen.");
      return;
    }
    const sg = suchgangNeu({ arten, einwilligung: zustimmungLesen() });
    suchgangEnde = null;
    kastenZu();
    // Sofort sichern; scheitert es hier, folgt der naechste Versuch,
    // sobald der Standort feststeht
    if (routeBeginnen(sg)) suchgangSichern(sg);
  };
  document.getElementById("suche-nur-route").onclick = () => {
    kastenZu();
    routeBeginnen();
  };
  document.getElementById("suche-abbrechen").onclick = () => kastenZu();
}

// Ohne Rueckfrage beenden (Abmelden): Der Gang bleibt offen und wird
// beim naechsten Oeffnen zum Abschliessen angeboten
function suchgangAnhalten(fertig) {
  const sg = fertig.suchgang;
  sg.ende = endeBegrenzt(sg, new Date());
  suchgangMerken(fertig);
  loescheRoutenlinie();
  return suchgangSichern(sg);
}

function suchgangEndeDialog(fertig, endeZeit = new Date()) {
  const sg = fertig.suchgang;
  const mitRoute = fertig.punkte.length >= 3;
  const zustand = { fertig, sg, mitRoute, routeId: fertig.routeId || null,
                    laeuft: false };
  suchgangEnde = zustand;
  // Ende sofort festhalten - schliesst jemand den Dialog, bleibt der
  // Suchgang offen im Tagebuch und auf dem Geraet gesichert
  sg.ende = endeBegrenzt(sg, endeZeit);
  zustand.min = Math.max(0, Math.round((new Date(sg.ende) - new Date(sg.beginn)) / 60000));
  suchgangSichern(sg);

  const funde = fundZahl(sg);
  const verwerfbar = !fertig.punkte.length && !funde;
  kasten(`
    <h3>Suchgang beenden</h3>
    <p class="klein">${(fertig.km || 0).toFixed(1)} km in ${zustand.min} Minuten${funde
        ? ` · ${funde} ${funde === 1 ? "Fund" : "Funde"} eingetragen` : ""}</p>
    <label class="fund-label" for="suche-dauer">Davon wirklich gesucht (Minuten)</label>
    <input type="number" id="suche-dauer" min="1" max="${Math.max(1, zustand.min)}"
           step="1" inputmode="numeric" placeholder="leer lassen, wenn unklar">
    <p class="fund-label">Ergebnis je gesuchter Art</p>
    ${ergebnisWahl(sg.arten, sg.ergebnisse)}
    <p class="klein">„Nichts gefunden“ nur, wenn du die Art wirklich
      gesucht und nicht gefunden hast. Im Zweifel offen lassen.</p>
    ${mitRoute ? `
      <label class="suche-haken"><input type="checkbox" id="suche-route" checked>
        Route speichern</label>
      <input type="text" id="routentitel" placeholder="Wo warst du?"
             value="${kontoHtml(routenvorschlag(fertig.punkte))}">
      <textarea id="routennotiz" rows="2"
        placeholder="Notiz (was gesehen, was gefunden)"></textarea>`
      : '<p class="klein">Zu wenige Punkte für eine Route – gespeichert wird nur der Suchgang.</p>'}
    <p id="suche-fehler" class="klein fehler" role="alert" hidden></p>
    <button type="button" class="voll" id="suche-fertig">Fertig</button>
    ${verwerfbar ? `<button type="button" class="voll leer" id="suche-verwerfen">
      Suchgang verwerfen</button>` : ""}
  `);
  document.getElementById("suche-fertig").onclick = () => suchgangAbschliessen(zustand);
  const verwerfen = document.getElementById("suche-verwerfen");
  if (verwerfen) verwerfen.onclick = () => suchgangVerwerfen(zustand);
}

async function suchgangAbschliessen(zustand) {
  if (zustand.laeuft) return;
  const { fertig, sg } = zustand;
  const roh = document.getElementById("suche-dauer").value;
  const dauer = roh === "" ? null : Number(roh);
  const grenze = Math.max(1, zustand.min);
  if (dauer !== null && (!Number.isInteger(dauer) || dauer < 1 || dauer > grenze)) {
    sucheFehler(`Die Suchdauer muss zwischen 1 und ${grenze} Minuten liegen – oder leer bleiben.`);
    return;
  }
  const knopf = document.getElementById("suche-fertig");
  zustand.laeuft = true;
  knopf.disabled = true;
  sucheFehler("");
  sg.suchdauer_min = dauer;
  sg.ergebnisse = ergebnisseLesen(sg.arten);
  const ort = sucheOrt(sg, fertig.punkte);
  try {
    const routeWahl = document.getElementById("suche-route");
    // Eine bereits angelegte Route beim Wiederholen nicht erneut anlegen
    if (zustand.mitRoute && routeWahl && routeWahl.checked && !zustand.routeId) {
      zustand.routeId = await routeEinfuegen(fertig, zustand.min,
        document.getElementById("routentitel").value,
        document.getElementById("routennotiz").value);
    }
    sg.route = zustand.routeId;
    if (!await suchgangSichern(sg)) {
      throw new Error(sg.fehler || "Verbindung fehlgeschlagen.");
    }
    if (ort) await suchgangNullfunde(sg, ort.lat, ort.lon);
  } catch (e) {
    sucheFehler("Konnte nicht speichern: " + (e.message || e));
    return;
  } finally {
    zustand.laeuft = false;
    knopf.disabled = false;
  }
  suchgangVergessen(sg.id);
  suchgangEnde = null;
  kastenZu();
  loescheRoutenlinie();
  if (zustand.routeId) ladeRouten();
  if (sg.arten.some(a => sg.ergebnisse[a] === "nullfund")) ladeEigeneFunde();
  const fehlend = suchgangFundLuecken(sg);
  if (fehlend.length && ort) {
    melde("Suchgang gespeichert. Jetzt die Funde eintragen.");
    fundFormularOeffnen({ lat: ort.lat, lon: ort.lon, zelle: sg.zelle,
                          suchgang: sg, datum: sg.datum, arten: fehlend });
  } else {
    melde("Suchgang gespeichert.");
  }
}

// Fuer Gaenge ohne Weg und Fund, etwa wenn der Standort gleich zu Beginn
// verweigert wurde
async function suchgangVerwerfen(zustand) {
  if (zustand.laeuft) return;
  if (!confirm("Diesen Suchgang verwerfen?\n\nEr wird auch aus dem Tagebuch gelöscht.")) return;
  const { error } = await sb.from("suchgang").delete().eq("id", zustand.sg.id);
  if (error) {
    sucheFehler("Konnte nicht verwerfen: " + error.message);
    return;
  }
  suchgangVergessen(zustand.sg.id);
  suchgangEnde = null;
  kastenZu();
  loescheRoutenlinie();
  melde("Suchgang verworfen.");
}

// Fuer Gaenge ohne Aufzeichnung. Ort ist die Kartenmitte. Ohne
// Uhrzeiten und ohne Kartenwerte - siehe suchgangNeu.
function suchgangNachtragen() {
  if (!benutzer || !karte || !D || !D.arten) return;
  kasten(`
    <h3>Suchgang nachtragen</h3>
    <p class="klein">Ort ist die aktuelle Kartenmitte – vorher die Karte auf
      das Suchgebiet schieben. Die Kartenwerte werden nicht mitgespeichert:
      Die heutige Karte zeigt nicht mehr, was damals angezeigt wurde.</p>
    <label class="fund-label" for="suche-datum">Datum</label>
    <input type="date" id="suche-datum" min="2020-01-02" required>
    <label class="fund-label" for="suche-dauer">Suchdauer in Minuten</label>
    <input type="number" id="suche-dauer" min="1" max="1440" step="1"
           inputmode="numeric" placeholder="leer lassen, wenn unklar">
    <p class="fund-label">Gesuchte Arten</p>
    ${artenChips(vorgewaehlteArten())}
    <div id="suche-ergebnisse"></div>
    <textarea id="suche-notiz" rows="2" placeholder="Notiz (optional)"></textarea>
    ${zustimmungHaken()}
    <p id="suche-fehler" class="klein fehler" role="alert" hidden></p>
    <button type="button" class="voll" id="suche-speichern">Speichern</button>
    <button type="button" class="voll leer" id="suche-zurueck">Zurück</button>
  `);
  const datum = document.getElementById("suche-datum");
  datum.value = fundHeute();
  datum.max = fundHeute();
  const vorgaben = {};
  const ergebnisseZeigen = () => {
    const arten = gewaehlteArten();
    ergebnisseLesen(arten, vorgaben);
    document.getElementById("suche-ergebnisse").innerHTML = arten.length
      ? '<p class="fund-label">Ergebnis je Art</p>' + ergebnisWahl(arten, vorgaben) : "";
  };
  artenChipsVerbinden(ergebnisseZeigen);
  ergebnisseZeigen();
  document.getElementById("suche-zurueck").onclick = () => zeigeTagebuch();
  const knopf = document.getElementById("suche-speichern");
  let sg = null;
  knopf.onclick = async () => {
    const arten = gewaehlteArten();
    const roh = document.getElementById("suche-dauer").value;
    const dauer = roh === "" ? null : Number(roh);
    if (!datum.value || !datum.checkValidity()) return sucheFehler("Bitte ein gültiges Datum bis heute wählen.");
    if (dauer !== null && (!Number.isInteger(dauer) || dauer < 1 || dauer > 1440)) {
      return sucheFehler("Die Suchdauer muss zwischen 1 und 1440 Minuten liegen – oder leer bleiben.");
    }
    if (!arten.length) return sucheFehler("Bitte mindestens eine gesuchte Art wählen.");
    // Beim Wiederholen nach einem Fehler dieselbe Kennung behalten
    if (!sg) {
      const mitte = karte.getCenter();
      sg = suchgangNeu({ arten, quelle: "nachtrag", datum: datum.value });
      suchgangOrt(sg, mitte.lat, mitte.lng, null);
    }
    einwilligungSetzen(sg, zustimmungLesen());
    sg.datum = datum.value;
    sg.arten = arten;
    sg.suchdauer_min = dauer;
    sg.ergebnisse = ergebnisseLesen(arten, vorgaben);
    sg.notiz = document.getElementById("suche-notiz").value.trim() || null;
    knopf.disabled = true;
    sucheFehler("");
    try {
      if (!await suchgangSichern(sg)) throw new Error(sg.fehler || "Verbindung fehlgeschlagen.");
      await suchgangNullfunde(sg, sg.lat, sg.lon);
    } catch (e) {
      sucheFehler("Konnte nicht speichern: " + (e.message || e));
      return;
    } finally {
      knopf.disabled = false;
    }
    if (arten.some(a => sg.ergebnisse[a] === "nullfund")) ladeEigeneFunde();
    const fehlend = suchgangFundLuecken(sg);
    if (fehlend.length) {
      melde("Suchgang gespeichert. Jetzt die Funde eintragen.");
      fundFormularOeffnen({ lat: sg.lat, lon: sg.lon, zelle: sg.zelle,
                            suchgang: sg, datum: sg.datum, arten: fehlend });
    } else {
      melde("Suchgang gespeichert.");
      zeigeTagebuch();
    }
  };
}

// Nach dem Anmelden: Liegt auf dem Geraet ein nicht abgeschlossener Gang,
// fortsetzen (nur am selben Tag und solange keine Route angelegt ist),
// abschliessen oder offen lassen
function suchgangOffenPruefen() {
  if (suchgangOffenGefragt || aufzeichnung || suchgangEnde || fundFormular) return;
  const offen = suchgangGemerkt();
  if (!offen) return;
  suchgangOffenGefragt = true;
  const sg = suchgangAusGemerkt(offen);
  const fertig = { beginn: new Date(offen.beginn), punkte: offen.punkte || [],
                   km: offen.km || 0, suchgang: sg, routeId: offen.routeId || null };
  const fortsetzbar = sg.datum === fundHeute() && !fertig.routeId;
  const namen = sg.arten.map(artName).join(", ");
  const zeit = new Date(sg.beginn).toLocaleString("de-DE",
    { dateStyle: "short", timeStyle: "short" });
  kasten(`
    <h3>Suchgang nicht abgeschlossen</h3>
    <p class="klein">Begonnen ${kontoHtml(zeit)}, gesucht: ${kontoHtml(namen)}.
      ${fertig.punkte.length} Wegpunkte sind auf diesem Gerät gesichert.</p>
    ${fortsetzbar ? '<button type="button" class="voll" id="suche-weiter">Aufzeichnung fortsetzen</button>' : ""}
    <button type="button" class="voll${fortsetzbar ? " leer" : ""}" id="suche-jetzt">Jetzt abschließen</button>
    <button type="button" class="voll leer" id="suche-spaeter">Offen lassen</button>
    <p class="klein">Offen lassen: Der Gang bleibt ohne Ergebnis im
      Tagebuch, der Weg wird nicht gespeichert.</p>
    <p id="suche-fehler" class="klein fehler" role="alert" hidden></p>
  `);
  const weiter = document.getElementById("suche-weiter");
  if (weiter) weiter.onclick = () => {
    kastenZu();
    sg.ende = null;
    if (routeBeginnen(sg, fertig)) suchgangSichern(sg);
  };
  document.getElementById("suche-jetzt").onclick = () =>
    suchgangEndeDialog(fertig, sg.ende || offen.zuletzt);
  document.getElementById("suche-spaeter").onclick = async () => {
    sg.ende = sg.ende || endeBegrenzt(sg, offen.zuletzt);
    if (!await suchgangSichern(sg)) {
      sucheFehler("Konnte nicht speichern: " + (sg.fehler || "Verbindung fehlgeschlagen."));
      return;
    }
    suchgangVergessen(sg.id);
    kastenZu();
    melde("Der Suchgang bleibt offen im Tagebuch.");
  };
}

// Widerruf gilt fuer alle eigenen Gaenge, auch bereits gespeicherte
async function suchgangAuswertungWiderrufen() {
  if (!sb || !benutzer) return;
  if (!confirm("Auswertung für alle deine Suchgänge widerrufen?\n\n"
             + "Sie bleiben in deinem Tagebuch, werden aber nicht mehr zur "
             + "Prüfung der Karte genutzt. Neue Suchgänge werden nur mit "
             + "erneutem Haken ausgewertet.")) return;
  const { error } = await sb.from("suchgang").update({ auswertung_erlaubt: false })
    .eq("benutzer", benutzer.id).eq("auswertung_erlaubt", true);
  if (error) {
    melde("Konnte nicht widerrufen: " + error.message);
    return;
  }
  try { localStorage.setItem(SUCHE_ZUSTIMMUNG, "0"); } catch (e) {}
  // Auch Gaenge, die gerade offen sind - sonst setzt das naechste Sichern
  // die Erlaubnis wieder
  for (const sg of [aufzeichnung?.suchgang, suchgangEnde?.sg, fundFormular?.ort?.suchgang]) {
    if (sg) sg.auswertung_erlaubt = false;
  }
  const offen = suchgangGemerkt();
  if (offen) {
    offen.suchgang.auswertung_erlaubt = false;
    try { localStorage.setItem(SUCHE_OFFEN, JSON.stringify(offen)); } catch (e) {}
  }
  melde("Auswertung widerrufen.");
  zeigeTagebuch();
}

function suchgangDauerText(s) {
  if (s.suchdauer_min) return `${s.suchdauer_min} min gesucht`;
  if (s.beginn && s.ende) {
    return Math.round((new Date(s.ende) - new Date(s.beginn)) / 60000) + " min unterwegs";
  }
  return s.beginn ? "ohne Ende" : "Dauer unbekannt";
}



// ---- Karteneinstellungen merken -------------------------------------
//
// Art, Tag, Darstellung, Deckkraft, Waldebene, Gelaende - alles was
// jemand einstellt, soll beim naechsten Mal wieder da sein. Am
// Konto, nicht am Geraet.

let einstellungenBereit = false;

function gespeicherteBaeume(e) {
  const werte = Array.isArray(e.baeume) ? e.baeume : (e.baum ? [e.baum] : []);
  const arten = [...new Set(werte.filter(w => typeof w === "string" && /^[a-z_]+$/.test(w)))];
  return arten.slice(0, 1);
}

function sammleEinstellungen() {
  const gewaehlt = w => {
    const b = document.querySelector(`[data-${w}].aktiv`);
    return b ? b.dataset[w] : null;
  };
  const an = w => {
    const b = document.querySelector(`[data-schalter=${w}]`);
    return b ? b.classList.contains("aktiv") : false;
  };
  const regler = id => {
    const el = document.getElementById(id);
    return el ? +el.value : null;
  };

  return {
    hell: hell,
    // Vorgemerkte Arten gehoeren ins Konto, nicht nur in den
    // Browserspeicher: Safari raeumt den nach einiger Zeit auf,
    // und auf einem zweiten Geraet waeren sie ohnehin weg.
    lieblinge: (typeof lieblinge !== "undefined") ? lieblinge : [],
    art: typeof art !== "undefined" ? art : null,
    stil: gewaehlt("stil"),
    baeume: [...document.querySelectorAll("[data-baum].aktiv")].map(b => b.dataset.baum),
    relief: gewaehlt("relief"),
    deckkraft: regler("deckregler"),
    funde: an("funde"),
    routen: an("routen"),
    schutz: an("schutz")
  };
}

let sichernZeit = null;

function merkeEinstellungen() {
  // Ohne Anmeldung laeuft stelleWiederHer nie, und damit wurde
  // einstellungenBereit nie gesetzt - dann hat diese Funktion gar
  // nichts geschrieben, auch nicht in den Browserspeicher.
  if (!einstellungenBereit && benutzer) return;

  // Nicht bei jedem Klick schreiben - erst wenn Ruhe eingekehrt ist
  clearTimeout(sichernZeit);
  sichernZeit = setTimeout(async () => {
    const e = sammleEinstellungen();
    try {
      localStorage.setItem("pilzkarte_einstellungen", JSON.stringify(e));
    } catch (x) {}

    if (sb && benutzer) {
      await sb.from("profile").update({ einstellungen: e })
        .eq("id", benutzer.id);
    }
  }, 1200);
}

let wiederhergestellt = false;

function stelleWiederHer(e, versuch) {
  if (!e || !karte) return;

  // Wald- und Gelaendeknoepfe entstehen erst, wenn wald.json und
  // relief.json geladen sind. Beim ersten Versuch gibt es sie oft
  // noch nicht - dann greift der Klick ins Leere und die zuletzt
  // gewaehlte Waldebene bleibt aus.
  versuch = versuch || 0;
  const baeume = gespeicherteBaeume(e);
  const fehltNoch = !document.querySelector("[data-baum]")
                 || (e.relief && !document.querySelector(
                       `[data-relief="${e.relief}"]`));
  if (fehltNoch && versuch < 20) {
    setTimeout(() => stelleWiederHer(e, versuch + 1), 250);
    return;
  }
  // Nur einmal je Sitzung - sonst klickt es die Knoepfe bei jedem
  // Aufruf erneut durch
  if (wiederhergestellt) return;
  wiederhergestellt = true;

  const druecke = (wahl, wert) => {
    if (!wert) return;
    const b = document.querySelector(`[data-${wahl}="${wert}"]`);
    if (b && !b.classList.contains("aktiv")) b.click();
  };

  if (typeof e.hell === "boolean") setzeAnsicht(e.hell, false);

  if (Array.isArray(e.lieblinge)
      && typeof lieblinge !== "undefined") {
    lieblinge = e.lieblinge;
    try {
      localStorage.setItem("pilzkarte_lieblinge",
                           JSON.stringify(lieblinge));
    } catch (x) {}
    // Ohne das bleibt die Reihenfolge stehen, wie sie war - die
    // zurueckgeholten Vorgemerkten wuerden erst beim naechsten
    // Klick nach oben ruecken.
    if (typeof aktualisiere === "function") aktualisiere();
  }

  if (e.art && D.arten[e.art]) {
    const b = document.querySelector(`[data-art="${e.art}"]`);
    if (b) b.click();
  }
  druecke("stil", e.stil);
  document.querySelectorAll("[data-baum].aktiv").forEach(b => {
    if (!baeume.includes(b.dataset.baum)) b.click();
  });
  baeume.forEach(baum => druecke("baum", baum));
  druecke("relief", e.relief);

  if (typeof e.deckkraft === "number") {
    const el = document.getElementById("deckregler");
    if (el) {
      el.value = e.deckkraft;
      el.dispatchEvent(new Event("input"));
    }
  }

  ["funde", "routen"].forEach(w => {
    const b = document.querySelector(`[data-schalter=${w}]`);
    if (b && !!e[w] !== b.classList.contains("aktiv")) b.click();
  });
  // Schutzgebiete sind von Haus aus an. Aeltere gespeicherte
  // Einstellungen kennen den Schalter noch nicht - fehlt er, bleibt
  // die Ebene an.
  const schutz = document.querySelector("[data-schalter=schutz]");
  if (schutz && (e.schutz !== false) !== schutz.classList.contains("aktiv")) {
    schutz.click();
  }

  einstellungenBereit = true;
}

function ladeEinstellungen() {
  // Erst das Konto, sonst der Browser
  if (benutzer && benutzer.einstellungen
      && Object.keys(benutzer.einstellungen).length) {
    return benutzer.einstellungen;
  }
  try {
    const t = localStorage.getItem("pilzkarte_einstellungen");
    return t ? JSON.parse(t) : null;
  } catch (e) {
    return null;
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

let letzteAnsicht = null;

async function setzeAnsicht(neuHell, speichern) {
  hell = neuHell;
  document.body.classList.toggle("hell", hell);

  // Die Kacheln nur wechseln, wenn sich wirklich etwas aendert.
  //
  // setTiles laedt die ganze Grundkarte neu. Wird es mehrmals kurz
  // hintereinander gerufen, bricht MapLibre den jeweils vorigen
  // Ladevorgang ab und meldet AbortError - die Konsole fuellt sich,
  // ohne dass etwas kaputt waere.
  if (karte && letzteAnsicht !== hell) {
    letzteAnsicht = hell;
    // Esri Grey Canvas, hell oder dunkel. Muss zu den Quellen in
    // index.html passen - dort steht dieselbe Adresse.
    const basis = "https://services.arcgisonline.com/ArcGIS/rest/"
                + "services/Canvas/World_";
    const teil = hell ? "Light_Gray" : "Dark_Gray";

    ["grund", "beschriftung"].forEach(quelle => {
      const q = karte.getSource(quelle);
      if (!q || typeof q.setTiles !== "function") return;
      const rolle = quelle === "grund" ? "Base" : "Reference";
      try {
        q.setTiles([`${basis}${teil}_${rolle}/MapServer/`
                    + `tile/{z}/{y}/{x}`]);
      } catch (e) {
        // Ein abgebrochener Ladevorgang ist kein Fehler
      }
    });
  }

  // Schutzgebiete: dunkleres Rot auf der hellen Karte
  if (typeof schutzFaerben === "function") schutzFaerben();

  // Das Symbol bleibt ein Symbol - vorher wurde es hier durch das
  // Wort "hell" oder "dunkel" ersetzt, und der runde Knopf sah
  // danach aus wie ein verrutschtes Textfeld.
  const knopf = document.querySelector("[data-ansicht-hell]");
  if (knopf) {
    // Das Symbol bleibt der halb gefuellte Pilz - es steht fuer
    // den Gegensatz selbst, nicht fuer einen der beiden Zustaende.
    // Nur der Hinweistext sagt, wohin der Druck fuehrt.
    knopf.title = hell ? "Auf dunkel umschalten"
                       : "Auf hell umschalten";
  }

  if (!speichern) return;

  try {
    localStorage.setItem("pilzkarte_hell", hell ? "1" : "0");
  } catch (e) {}

  if (sb && benutzer) {
    // ALLE Einstellungen schreiben, nicht nur "hell".
    //
    // Vorher stand hier update({ einstellungen: { hell: hell } }) -
    // das ersetzt das ganze Objekt. Jedes Umschalten zwischen hell
    // und dunkel loeschte damit die vorgemerkten Arten, die
    // gewaehlte Art, die Deckkraft und die Waldebene aus dem
    // Profil.
    const alles = sammleEinstellungen();
    try {
      localStorage.setItem("pilzkarte_einstellungen",
                           JSON.stringify(alles));
    } catch (e) {}
    await sb.from("profile")
      .update({ einstellungen: alles })
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
    .select("mitleser, einstellungen, anzeigename, avatar")
    .eq("id", benutzer.id).single();
  istMitleser = !!(data && data.mitleser);
  anzeigename = data && data.anzeigename ? data.anzeigename : null;
  avatar = data && data.avatar ? data.avatar : null;
  if (data && data.einstellungen) {
    benutzer.einstellungen = data.einstellungen;
  }
  // KEIN zeigeKontostand() hier - das ruft sonst wieder hierher
  // zurueck. Die Anzeige uebernimmt kontoDatenLaden().
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
  b.title = "Funde und Routen der anderen Nutzer einblenden "
          + "(orange). Nur fuer Mitleser.";
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
          <b>${kontoHtml(p.null == 1 ? "Nichts gefunden" : p.art)}</b>
          <div class="lage">${kontoHtml(p.datum)} &middot; anderer Nutzer</div>
          ${p.notiz ? `<div class="klein">${kontoHtml(p.notiz)}</div>` : ""}
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


// ---- Benutzername ---------------------------------------------------
//
// Mindestens 4 Zeichen, nur Buchstaben und Ziffern. Geprueft wird
// waehrend des Tippens gegen die Datenbank - und beim Speichern
// nochmal dort, weil sich die Browserpruefung umgehen liesse.

let anzeigename = null;
let namenspruefung = null;

function namenFehler(name) {
  if (name.length < 4) return "Mindestens 4 Zeichen.";
  if (name.length > 20) return "Höchstens 20 Zeichen.";
  if (!/^[A-Za-z0-9]+$/.test(name)) {
    return "Nur Buchstaben und Zahlen.";
  }
  return null;
}

function zeigeNamenswahl(erstmalig) {
  kasten(`
    <h3>${erstmalig ? "Benutzername wählen" : "Name ändern"}</h3>
    <p class="klein">Mindestens 4 Zeichen, nur Buchstaben und
    Zahlen.</p>
    <input type="text" id="wunschname" maxlength="20"
           autocomplete="off" autocapitalize="off"
           placeholder="dein Name"
           value="${kontoHtml(erstmalig ? "" : (anzeigename || ""))}">
    <p class="klein" id="namenshinweis">&nbsp;</p>
    <button class="voll" id="namenknopf" onclick="namenSpeichern()"
            disabled>Speichern</button>
    ${erstmalig ? "" :
      '<button class="voll leer" onclick="zeigeKontomenue()">' +
      'Zurück</button>'}
  `);

  const feld = document.getElementById("wunschname");
  feld.oninput = () => pruefeName();
  feld.onkeydown = e => {
    if (e.key === "Enter") namenSpeichern();
  };
  feld.focus();
  feld.select();
  if (!erstmalig) pruefeName();
}

async function pruefeName() {
  const feld = document.getElementById("wunschname");
  const hinweis = document.getElementById("namenshinweis");
  const knopf = document.getElementById("namenknopf");
  if (!feld) return;

  const name = feld.value.trim();
  knopf.disabled = true;

  if (!name) {
    hinweis.textContent = "\u00a0";
    return;
  }

  const fehler = namenFehler(name);
  if (fehler) {
    hinweis.textContent = fehler;
    hinweis.className = "klein fehler";
    return;
  }

  if (name.toLowerCase() === (anzeigename || "").toLowerCase()) {
    hinweis.textContent = "Das ist dein jetziger Name.";
    hinweis.className = "klein";
    return;
  }

  // Waehrend des Tippens nicht bei jedem Zeichen fragen
  hinweis.textContent = "Prüfe ...";
  hinweis.className = "klein";
  clearTimeout(namenspruefung);

  namenspruefung = setTimeout(async () => {
    const { data, error } = await sb.rpc("name_frei", { wunsch: name });
    if (feld.value.trim() !== name) return;   // schon weitergetippt

    if (error) {
      hinweis.textContent = "Konnte nicht prüfen.";
      hinweis.className = "klein fehler";
      return;
    }
    if (data) {
      hinweis.textContent = "\u2713 frei";
      hinweis.className = "klein frei";
      knopf.disabled = false;
    } else {
      hinweis.textContent = "Schon vergeben.";
      hinweis.className = "klein fehler";
    }
  }, 350);
}

async function namenSpeichern() {
  const feld = document.getElementById("wunschname");
  const hinweis = document.getElementById("namenshinweis");
  const name = feld.value.trim();

  const fehler = namenFehler(name);
  if (fehler) {
    hinweis.textContent = fehler;
    hinweis.className = "klein fehler";
    return;
  }

  const { data, error } = await sb.rpc("name_setzen", { wunsch: name });
  if (error) {
    hinweis.textContent = error.message;
    hinweis.className = "klein fehler";
    return;
  }

  anzeigename = data;
  kastenZu();
  zeigeKontostand();
  melde("Name gespeichert.");
}


// ---- Bild fuers Profil ----------------------------------------------
//
// Eine feste Auswahl, kein Hochladen. Die Bilder liegen in
// web/avatare/, welche es gibt, steht in avatare.json - neue
// hinzuzufuegen heisst also: Datei ablegen, eine Zeile ergaenzen.

let avatar = null;
let avatarliste = null;

async function ladeAvatarliste() {
  if (avatarliste) return avatarliste;
  try {
    const a = await fetch("avatare/avatare.json");
    avatarliste = a.ok ? await a.json() : [];
  } catch (e) {
    avatarliste = [];
  }
  return avatarliste;
}

function avatarBild(datei, groesse) {
  if (!datei) return "";
  return `<img src="avatare/${kontoHtml(datei)}" alt=""
    width="${groesse}" height="${groesse}" class="avatar">`;
}

async function zeigeAvatarwahl() {
  const liste = await ladeAvatarliste();

  if (!liste.length) {
    kasten(`<h3>Bild wählen</h3>
      <p class="klein">Noch keine Bilder vorhanden.</p>
      <button class="voll leer" onclick="zeigeKontomenue()">
        Zurück</button>`);
    return;
  }

  const felder = liste.map(e => `
    <button class="avatarfeld ${avatar === e.datei ? "aktiv" : ""}"
            data-avatar="${e.datei}" title="${e.name}">
      ${avatarBild(e.datei, 64)}
      <span>${e.name}</span>
    </button>`).join("");

  kasten(`<h3>Bild wählen</h3>
    <div class="avatarraster">${felder}</div>
    ${avatar ? `<button class="voll leer"
       onclick="avatarSpeichern(null)">Kein Bild</button>` : ""}
    <button class="voll leer" onclick="zeigeKontomenue()">
      Zurück</button>`);

  document.querySelectorAll("[data-avatar]").forEach(b =>
    b.onclick = () => avatarSpeichern(b.dataset.avatar));
}

async function avatarSpeichern(datei) {
  if (!sb || !benutzer) return;

  const { error } = await sb.from("profile")
    .update({ avatar: datei }).eq("id", benutzer.id);

  if (error) {
    melde("Konnte nicht speichern: " + error.message);
    return;
  }
  avatar = datei;
  kastenZu();
  zeigeKontostand();
}

// ---- Fund eintragen -------------------------------------------------
//
// Der wichtigste Teil: Was hier gesammelt wird, gibt es sonst
// nirgends. Vor allem die Nullfunde - "war hier, nichts gefunden".
// Ohne sie lassen sich die Schwellen der Karte nur einseitig pruefen.

let fundFormular = null;

// Kalendertag in Europe/Berlin als JJJJ-MM-TT
function berlinDatum(zeit = new Date()) {
  const teile = Object.fromEntries(new Intl.DateTimeFormat("de-DE", {
    timeZone: "Europe/Berlin", year: "numeric", month: "2-digit", day: "2-digit"
  }).formatToParts(new Date(zeit)).map(p => [p.type, p.value]));
  return `${teile.year}-${teile.month}-${teile.day}`;
}

function fundHeute() {
  return berlinDatum();
}

function fundBeginnen(lat, lon, zelle) {
  if (!benutzer) {
    melde("Erst anmelden, dann lassen sich Funde eintragen.");
    return;
  }
  // Waehrend einer Pilzsuche gehoert jeder Fund zu diesem Suchgang
  fundFormularOeffnen({ lat, lon, zelle, suchgang: aufzeichnung?.suchgang || null });
}

function fundFormularOeffnen(ort, original = null) {
  if (fundFormular?.speichert) return;
  const zustand = { ort, original, zeilen: [], speichert: false, daten: D };
  fundFormular = zustand;
  kasten(`
    <h3>${original ? "Fund bearbeiten" : "Funde eintragen"}</h3>
    <p class="klein">Weitere Pilzarten über das Plus hinzufügen.
      Ort, Datum und Notiz gelten für alle Einträge.</p>
    ${ort.suchgang ? `<p class="klein">Gehört zum Suchgang vom ${kontoHtml(
      new Date(`${ort.suchgang.datum}T12:00:00`).toLocaleDateString("de-DE"))}.</p>` : ""}
    <div id="fundzeilen"></div>
    <button type="button" class="voll leer fund-plus" id="fund-plus">
      <span aria-hidden="true">＋</span> Weitere Pilzart</button>
    <label class="fund-label" for="funddatum">Funddatum</label>
    <input type="date" id="funddatum" required>
    <label class="fund-label" for="fundnotiz">Notiz für diese Funde</label>
    <textarea id="fundnotiz" rows="2" placeholder="Bestand, Boden, Besonderheiten"></textarea>
    <p id="fundfehler" class="klein fehler" role="alert" hidden></p>
    <button type="button" class="voll" id="fund-speichern">Speichern</button>
    ${original ? "" : `<button type="button" class="voll leer" id="fund-null">
      Nichts gefunden – alle als Nullfund speichern</button>`}
    <button type="button" class="voll leer" id="fund-abbrechen">Abbrechen</button>
  `);
  zustand.element = document.querySelector("#kasten .kasten-inhalt");
  const datum = document.getElementById("funddatum");
  datum.value = original ? original.gefunden_am.slice(0, 10) : (ort.datum || fundHeute());
  datum.max = fundHeute();
  document.getElementById("fundnotiz").value = original?.notiz ?? "";
  document.getElementById("fund-plus").onclick = () => fundZeileHinzufuegen();
  document.getElementById("fund-speichern").onclick = () => fundSpeichern(false);
  const nullknopf = document.getElementById("fund-null");
  if (nullknopf) nullknopf.onclick = () => fundSpeichern(true);
  document.getElementById("fund-abbrechen").onclick = () => {
    if (zustand.speichert) return;
    fundFormular = null;
    if (original) zeigeTagebuch(); else kastenZu();
  };
  // Nach einem Suchgang je Art mit "gefunden" eine Zeile
  const vorgaben = original ? [original]
    : ort.arten?.length ? ort.arten.map(a => ({ art: a }))
    : [{ art: typeof art === "string" && D.arten[art] ? art : Object.keys(D.arten)[0] }];
  vorgaben.forEach(v => fundZeileHinzufuegen(v, false));
}

function fundZeileHinzufuegen(vorgabe = {}, fokus = true) {
  const zustand = fundFormular;
  if (!zustand || zustand.speichert) return;
  const zeile = { id: vorgabe.id ?? crypto.randomUUID(), original: vorgabe.id != null };
  const el = document.createElement("fieldset");
  el.className = "fund-zeile";
  el.innerHTML = `
    <legend></legend>
    <div class="fund-artwahl"><select aria-label="Pilzart" required></select>
      <button type="button" class="fund-entfernen" aria-label="Zusätzlichen Fund entfernen">−</button></div>
    <input class="fund-eigene" type="text" aria-label="Eigener Pilzname" placeholder="Welcher Pilz?" hidden>
    <input class="fund-anzahl" type="number" aria-label="Anzahl" placeholder="Anzahl (optional)" min="1" step="1">
    <label class="fund-nullwahl"><input type="checkbox"> Nichts gefunden</label>`;
  const auswahl = el.querySelector("select");
  auswahl.add(new Option("Pilzart wählen …", ""));
  Object.entries(zustand.daten.arten).forEach(([a, e]) => auswahl.add(new Option(e.name, a)));
  auswahl.add(new Option("Andere Art, selbst eintragen …", "__eigene"));
  const eigene = el.querySelector(".fund-eigene");
  if (vorgabe.art) {
    const bekannt = Object.hasOwn(zustand.daten.arten, vorgabe.art);
    auswahl.value = bekannt ? vorgabe.art : "__eigene";
    if (!bekannt) eigene.value = vorgabe.art;
  }
  const anzahl = el.querySelector(".fund-anzahl");
  anzahl.value = vorgabe.anzahl ?? "";
  const nullfund = el.querySelector('input[type="checkbox"]');
  nullfund.checked = !!vorgabe.nullfund;
  const wechsel = () => {
    eigene.hidden = auswahl.value !== "__eigene";
    eigene.required = !eigene.hidden;
    anzahl.disabled = nullfund.checked;
  };
  auswahl.onchange = () => { wechsel(); if (!eigene.hidden) eigene.focus(); };
  nullfund.onchange = wechsel;
  wechsel();
  const entfernen = el.querySelector(".fund-entfernen");
  entfernen.hidden = zustand.zeilen.length === 0;
  entfernen.onclick = () => {
    if (zustand.speichert) return;
    zustand.zeilen = zustand.zeilen.filter(z => z !== zeile);
    el.remove();
    fundZeilenNummerieren();
    document.getElementById("fund-plus").focus();
  };
  Object.assign(zeile, { el, auswahl, eigene, anzahl, nullfund });
  zustand.zeilen.push(zeile);
  document.getElementById("fundzeilen").appendChild(el);
  fundZeilenNummerieren();
  if (fokus) auswahl.focus();
}

function fundZeilenNummerieren() {
  fundFormular.zeilen.forEach((z, i) => {
    z.el.querySelector("legend").textContent = `Fund ${i + 1}`;
    z.auswahl.setAttribute("aria-label", `Pilzart für Fund ${i + 1}`);
    z.anzahl.setAttribute("aria-label", `Anzahl für Fund ${i + 1}`);
  });
}

function fundZeilenLesen(zustand, alleNull = false) {
  return zustand.zeilen.map((z, i) => {
    const art = z.auswahl.value === "__eigene" ? z.eigene.value.trim() : z.auswahl.value;
    if (!art) throw new Error(`Bitte für Fund ${i + 1} eine Pilzart eintragen.`);
    const nullfund = alleNull || z.nullfund.checked;
    const roh = z.anzahl.value;
    const anzahl = nullfund || roh === "" ? null : Number(roh);
    if (!nullfund && (z.anzahl.validity.badInput ||
        (anzahl !== null && (!Number.isSafeInteger(anzahl) || anzahl < 1)))) {
      throw new Error(`Die Anzahl für Fund ${i + 1} muss eine positive ganze Zahl sein.`);
    }
    return { id: z.id, art, nullfund, anzahl };
  });
}

function fundScore(zustand, eintrag, datum) {
  // Zu einem nachgetragenen Suchgang gibt es keinen damals angezeigten Wert
  if (zustand.ort.suchgang?.quelle === "nachtrag") return null;
  const alt = zustand.original;
  if (alt && eintrag.id === alt.id && eintrag.art === alt.art &&
      datum === alt.gefunden_am.slice(0, 10)) return alt.score ?? null;
  const zelle = zustand.daten.zellen.find(z => z.id === zustand.ort.zelle);
  const tag = zustand.daten.tage.findIndex(t => t.datum === datum);
  const wert = zelle?.scores[eintrag.art]?.[tag];
  return Number.isInteger(wert) && wert >= 0 && wert <= 100 ? wert : null;
}

async function fundSpeichern(alleNull = false) {
  const zustand = fundFormular;
  if (!sb || !benutzer || !zustand || zustand.speichert) return;
  const fehler = zustand.element.querySelector("#fundfehler");
  fehler.hidden = true;
  let zeilen;
  try {
    const datumfeld = zustand.element.querySelector("#funddatum");
    if (!datumfeld.value || !datumfeld.checkValidity()) throw new Error("Bitte ein gültiges Funddatum bis heute wählen.");
    const datum = datumfeld.value;
    const { lat, lon, zelle } = zustand.ort;
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      throw new Error("Der Fundort fehlt. Bitte den Fund über die Karte öffnen.");
    }
    const notiz = zustand.element.querySelector("#fundnotiz").value.trim() || null;
    // Nur mitschicken, wenn gesetzt: beim Bearbeiten bleibt eine
    // bestehende Zuordnung sonst erhalten
    const zuordnung = zustand.ort.suchgang ? { suchgang: zustand.ort.suchgang.id } : {};
    zeilen = fundZeilenLesen(zustand, alleNull).map(e => ({
      ...e, benutzer: benutzer.id, gefunden_am: datum,
      ort: `POINT(${lon} ${lat})`, zelle: zelle || null, notiz,
      score: fundScore(zustand, e, datum), ...zuordnung
    }));
  } catch (e) {
    fehler.textContent = e.message;
    fehler.hidden = false;
    return;
  }
  zustand.speichert = true;
  const controls = [...zustand.element.querySelectorAll("input, select, textarea, button")];
  const vorher = controls.map(el => el.disabled);
  controls.forEach(el => { el.disabled = true; });
  const knopf = zustand.element.querySelector("#fund-speichern");
  knopf.textContent = "Wird gespeichert …";
  const suchgang = zustand.ort.suchgang;
  try {
    // Der Fund verweist auf den Suchgang - der muss vorher gespeichert sein
    if (suchgang && !suchgang.gesichert && !await suchgangSichern(suchgang)) {
      throw new Error("Suchgang nicht gespeichert: " + (suchgang.fehler || "Verbindung fehlgeschlagen."));
    }
    // Ein Request: vorhandenen Fund aktualisieren und weitere anlegen.
    // Stabile IDs verhindern Duplikate beim Wiederholen nach Netzfehlern.
    const { error } = await sb.from("fund").upsert(zeilen, { onConflict: "id" });
    if (error) throw error;
    if (suchgang) suchgangFundeZaehlen(suchgang, zeilen);
  } catch (e) {
    fehler.textContent = "Konnte nicht speichern: " + (e.message || "Verbindung fehlgeschlagen.");
    fehler.hidden = false;
    return;
  } finally {
    zustand.speichert = false;
    controls.forEach((el, i) => { el.disabled = vorher[i]; });
    knopf.textContent = "Speichern";
  }
  if (fundFormular === zustand) {
    fundFormular = null;
    kastenZu();
  }
  melde(zeilen.length === 1 ? "Fund gespeichert." : `${zeilen.length} Funde gespeichert.`);
  await ladeEigeneFunde();
  if (zustand.original && !fundFormular) zeigeTagebuch();
}

// Ein eingetragener Fund einer gesuchten Art ist deren Ergebnis
function suchgangFundeZaehlen(sg, zeilen) {
  let geaendert = false;
  for (const z of zeilen) {
    if (z.nullfund) continue;
    sg.funde[z.art] = (sg.funde[z.art] || 0) + 1;
    if (sg.arten.includes(z.art) && sg.ergebnisse[z.art] !== "fund") {
      sg.ergebnisse[z.art] = "fund";
      geaendert = true;
    }
  }
  if (geaendert) suchgangSichern(sg);
  else suchgangStandMerken(sg);
}

// ---- Eigene Funde auf der Karte -------------------------------------

let eigeneFunde = [];

function fundeSichtbar() {
  const b = document.querySelector("[data-schalter=funde]");
  return b ? b.classList.contains("aktiv") : false;
}

async function ladeEigeneFunde() {
  if (!sb || !benutzer || !karte) return;

  // NUR die eigenen. Als Mitleser darf man alle Funde lesen -
  // ohne diesen Filter erschienen die Funde der anderen gruen,
  // noch bevor man "alle Nutzer" gedrueckt hat.
  const { data, error } = await sb.from("fund")
    .select("id, art, gefunden_am, nullfund, anzahl, notiz, lat, lon")
    .eq("benutzer", benutzer.id)
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
        <b>${kontoHtml(p.null == 1 ? "Nichts gefunden" : p.art)}</b>
        <div class="lage">${kontoHtml(p.datum)}${p.anzahl
          ? " &middot; " + kontoHtml(p.anzahl) + " Stück" : ""}</div>
        ${p.notiz ? `<div class="klein">${kontoHtml(p.notiz)}</div>` : ""}
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

// Alle geladenen Routen. Gezeichnet wird entweder eine einzelne
// (nach Klick im Tagebuch) oder alle - deshalb der Speicher.
let alleRouten = [];
let gezeigteRoute = null;

function pfeilBildAnlegen() {
  if (!karte || karte.hasImage("routenpfeil")) return;

  // Ein nach rechts zeigendes Dreieck, weiss mit dunklem Rand.
  // MapLibre dreht es entlang der Linie.
  const n = 18;
  const flaeche = document.createElement("canvas");
  flaeche.width = n;
  flaeche.height = n;
  const stift = flaeche.getContext("2d");

  stift.beginPath();
  stift.moveTo(n * 0.28, n * 0.18);
  stift.lineTo(n * 0.80, n * 0.50);
  stift.lineTo(n * 0.28, n * 0.82);
  stift.closePath();

  stift.fillStyle = "#f2fbf2";
  stift.fill();
  stift.lineWidth = 1.6;
  stift.strokeStyle = "#1a3320";
  stift.stroke();

  karte.addImage("routenpfeil",
    stift.getImageData(0, 0, n, n), { pixelRatio: 2 });
}

async function ladeRouten() {
  if (!sb || !benutzer || !karte) return;

  const { data, error } = await sb.from("route")
    .select("id, titel, begonnen, laenge_km, dauer_min, punkte")
    .order("begonnen", { ascending: false }).limit(100);

  if (error || !data) return;

  alleRouten = data.filter(r => Array.isArray(r.punkte)
                                && r.punkte.length >= 2);
  zeichneRouten();
}

function zeichneRouten() {
  if (!karte) return;

  // Entweder eine bestimmte Route oder alle
  const data = gezeigteRoute
    ? alleRouten.filter(r => r.id === gezeigteRoute)
    : alleRouten;

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
    zeigeRoutenleiste();
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

  // Laufrichtung: Pfeile entlang der Linie.
  //
  // Als BILD, nicht als Schriftzeichen. Das Dreieck U+25B6 ist in
  // Open Sans nicht enthalten - mit text-field blieb die Linie
  // deshalb pfeillos, ohne Fehlermeldung.
  pfeilBildAnlegen();

  karte.addLayer({
    id: "routen_pfeile", type: "symbol", source: "routen",
    layout: {
      visibility: sichtbar,
      "symbol-placement": "line",
      "symbol-spacing": 55,
      "icon-image": "routenpfeil",
      "icon-size": 0.8,
      "icon-allow-overlap": true,
      "icon-ignore-placement": true,
      "icon-rotation-alignment": "map"
    }
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
      .setHTML(`<div class="pop"><b>${kontoHtml(p.titel)}</b>
        <div class="lage">${kontoHtml(p.datum)} &middot; ${kontoHtml(p.km)} km
        &middot; ${kontoHtml(p.min)} min</div></div>`)
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
  zeigeRoutenleiste();
}

function zeigeRoutenleiste() {
  // Kleine Zeile auf der Karte: was gerade zu sehen ist, mit
  // Knopf zum Umschalten und zum Ausblenden.
  let el = document.getElementById("routenleiste");

  if (!routenSichtbar || !alleRouten.length) {
    if (el) el.remove();
    return;
  }

  if (!el) {
    el = document.createElement("div");
    el.id = "routenleiste";
    el.className = "routenleiste";
    document.getElementById("karte").appendChild(el);
  }

  if (gezeigteRoute) {
    const r = alleRouten.find(x => x.id === gezeigteRoute);
    const titel = r ? (r.titel || "Route") : "Route";
    el.innerHTML = `<span>${kontoHtml(titel)}</span>
      <button onclick="alleRoutenZeigen()">alle ${alleRouten.length}
        </button>
      <button onclick="routenAusblenden()" title="Ausblenden">
        &times;</button>`;
  } else {
    el.innerHTML = `<span>${alleRouten.length} Routen</span>
      <button onclick="routenAusblenden()" title="Ausblenden">
        &times;</button>`;
  }
}

function alleRoutenZeigen() {
  gezeigteRoute = null;
  zeichneRouten();
  routenAnzeigen(true);
}

function routenAusblenden() {
  gezeigteRoute = null;
  routenAnzeigen(false);
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
  b.onclick = () => {
    if (routenSichtbar) {
      routenAusblenden();
    } else {
      alleRoutenZeigen();
    }
  };
  leiste.appendChild(b);
}

// Eine bestimmte Route auf der Karte zeigen
async function zeigeRouteAufKarte(id, lat, lon) {
  kastenZu();
  if (!karte) return;

  if (!alleRouten.length) await ladeRouten();

  // Nur diese eine zeichnen
  gezeigteRoute = id;
  zeichneRouten();
  routenAnzeigen(true);

  // Auf die ganze Route zoomen, nicht nur auf den Anfang
  const r = alleRouten.find(x => x.id === id);
  if (r && r.punkte.length > 1) {
    const lats = r.punkte.map(p => p.lat);
    const lons = r.punkte.map(p => p.lon);
    karte.fitBounds(
      [[Math.min(...lons), Math.min(...lats)],
       [Math.max(...lons), Math.max(...lats)]],
      { padding: 70, duration: 900, maxZoom: 15 });
  } else {
    karte.flyTo({ center: [lon, lat], zoom: 13, duration: 900 });
  }
}



async function routeBearbeiten(id) {
  const r = alleRouten.find(x => x.id === id);
  if (!r) return;

  kasten(`
    <h3>Route bearbeiten</h3>
    <p class="klein">${new Date(r.begonnen)
      .toLocaleDateString("de-DE")} &middot; ${r.laenge_km || "?"} km
      &middot; ${r.dauer_min || "?"} min</p>
    <input type="text" id="rtitel" maxlength="60"
           value="${kontoHtml(r.titel || "")}">
    <textarea id="rnotiz" rows="3"
      placeholder="Notiz">${kontoHtml(r.notiz || "")}</textarea>
    <button class="voll" onclick="routeSpeichernAenderung('${id}')">
      Speichern</button>
    <button class="voll leer" onclick="zeigeTagebuch()">Zurück</button>
  `);
  const feld = document.getElementById("rtitel");
  feld.focus();
  feld.select();
}

async function routeSpeichernAenderung(id) {
  const titel = document.getElementById("rtitel").value.trim();
  const notiz = document.getElementById("rnotiz").value.trim();

  const { error } = await sb.from("route")
    .update({ titel: titel || null, notiz: notiz || null })
    .eq("id", id);

  if (error) {
    melde("Konnte nicht speichern: " + error.message);
    return;
  }
  const r = alleRouten.find(x => x.id === id);
  if (r) { r.titel = titel; r.notiz = notiz; }

  melde("Gespeichert.");
  zeigeTagebuch();
}

async function fundBearbeiten(id) {
  if (!sb || !benutzer) return;
  const { data, error } = await sb.from("fund")
    .select("id, art, gefunden_am, anzahl, notiz, nullfund, lat, lon, zelle, score")
    .eq("id", id).eq("benutzer", benutzer.id).single();
  if (error || !data) {
    melde("Der Fund konnte nicht geladen werden.");
    return;
  }
  fundFormularOeffnen({ lat: data.lat, lon: data.lon, zelle: data.zelle }, data);
}


// ---- Loeschen -------------------------------------------------------
//
// Mit Rueckfrage, weil es nicht rueckgaengig zu machen ist. Die
// Zeilenrechte in der Datenbank erlauben das Loeschen ohnehin nur
// dem Besitzer - ein Mitleser kann fremde Eintraege sehen, aber
// nicht entfernen.

const STIFT =
  '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
  'stroke-linejoin="round">' +
  '<path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>' +
  '</svg>';

const MUELLEIMER =
  '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
  'stroke-linejoin="round"><path d="M3 6h18"/>' +
  '<path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/>' +
  '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>' +
  '<path d="M10 11v6M14 11v6"/></svg>';

async function loesche(tabelle, id, beschreibung) {
  if (!sb || !benutzer) return;

  const was = tabelle === "route" ? "Diese Route"
            : tabelle === "suchgang" ? "Diesen Suchgang" : "Diesen Eintrag";
  if (!confirm(`${was} wirklich l\u00f6schen?\n\n${beschreibung}\n\n`
             + "Das l\u00e4sst sich nicht r\u00fcckg\u00e4ngig machen.")) {
    return;
  }

  const { error } = await sb.from(tabelle).delete().eq("id", id);

  if (error) {
    melde("Konnte nicht l\u00f6schen: " + error.message);
    return;
  }

  melde(tabelle === "route" ? "Route gel\u00f6scht."
      : tabelle === "suchgang" ? "Suchgang gel\u00f6scht." : "Eintrag gel\u00f6scht.");

  // Karte und Tagebuch auffrischen
  if (tabelle === "route") {
    await ladeRouten();
  } else if (tabelle === "fund") {
    await ladeEigeneFunde();
  }
  zeigeTagebuch();
}

// ---- Tagebuch -------------------------------------------------------

function fundeZurRoute(route, funde) {
  // Wie viele Funde gehoeren zu dieser Route?
  //
  // Nicht nur die waehrend der Aufzeichnung eingetragenen: Wer
  // abends nachtraegt, soll sie hier trotzdem wiederfinden.
  // Massstab ist deshalb der Ort - alles, was am selben Tag im
  // Umkreis von 50 m um den Weg liegt.
  if (!Array.isArray(route.punkte) || !route.punkte.length) return 0;

  const tag = new Date(route.begonnen).toISOString().slice(0, 10);
  const UMKREIS = 0.05;   // 50 m

  return (funde || []).filter(f => {
    if (f.nullfund) return false;
    if (f.lat == null || f.lon == null) return false;
    if ((f.gefunden_am || "").slice(0, 10) !== tag) return false;
    return route.punkte.some(p =>
      abstandKm(p.lat, p.lon, f.lat, f.lon) <= UMKREIS);
  }).length;
}


async function zeigeTagebuch() {
  kasten('<h3>Tagebuch</h3><p class="klein">Wird geladen ...</p>');

  const [routen, funde, zahlen, suchen] = await Promise.all([
    sb.from("route")
      .select("id, titel, begonnen, laenge_km, dauer_min, notiz, "
              + "start_lat, start_lon, punkte")
      .eq("benutzer", benutzer.id)
      .order("begonnen", { ascending: false }).limit(30),
    sb.from("fund")
      .select("id, art, gefunden_am, nullfund, anzahl, notiz, lat, lon")
      .eq("benutzer", benutzer.id)
      .order("gefunden_am", { ascending: false }).limit(30),
    sb.rpc("meine_zahlen"),
    sb.from("suchgang")
      .select("id, datum, beginn, ende, suchdauer_min, arten, ergebnisse, "
              + "quelle, raeumlich_gemischt, auswertung_erlaubt")
      .eq("benutzer", benutzer.id)
      .order("datum", { ascending: false })
      .order("beginn", { ascending: false }).limit(30)
  ]);

  const z = (zahlen.data && zahlen.data[0]) || {};

  // Fehlt die Tabelle noch (Migration nicht ausgefuehrt), bleibt das
  // uebrige Tagebuch nutzbar
  const suchListe = suchen.error
    ? '<p class="klein">Suchgänge sind noch nicht eingerichtet.</p>'
    : ((suchen.data || []).map(s => {
      const datum = new Date(`${s.datum}T12:00:00`).toLocaleDateString("de-DE");
      const arten = s.arten || [];
      const ergebnisse = arten.map(a => `${artName(a)}: `
        + (SUCHE_ERGEBNISSE[s.ergebnisse?.[a]] || "offen")).join(" · ");
      const zusatz = [s.quelle === "nachtrag" ? "nachgetragen" : "",
                      s.raeumlich_gemischt ? "mehrere Kartenzellen" : "",
                      s.auswertung_erlaubt ? "wird ausgewertet" : ""]
        .filter(Boolean).map(t => " &middot; " + t).join("");
      return `<div class="eintrag">
        <div class="kopfzeile"><b>${kontoHtml(arten.map(artName).join(", "))}</b>
          <button class="muell" title="Löschen"
            data-loeschen="suchgang" data-id="${kontoHtml(s.id)}"
            data-beschreibung="${kontoHtml(`Suchgang vom ${datum}`)}"
            >${MUELLEIMER}</button>
        </div>
        <div class="klein">${kontoHtml(datum)} &middot;
          ${kontoHtml(suchgangDauerText(s))}${zusatz}</div>
        <div class="klein">${kontoHtml(ergebnisse)}</div>
      </div>`;
    }).join("") || '<p class="klein">Noch keine Suchgänge.</p>');
  const suchZahl = suchen.error ? 0 : (suchen.data || []).length;
  const widerrufbar = !suchen.error && (suchen.data || []).some(s => s.auswertung_erlaubt);

  const routenListe = (routen.data || []).map(r => {
    const anzahl = fundeZurRoute(r, funde.data);
    const marke = anzahl
      ? `<span class="fundzahl">+${anzahl}</span>` : "";
    const knopf = (r.start_lat != null && r.start_lon != null)
      ? `<button class="zeigen" onclick="zeigeRouteAufKarte(
           '${r.id}', ${r.start_lat}, ${r.start_lon})">
         Auf der Karte</button>`
      : "";
    const titel = r.titel || "ohne Titel";
    const datum = new Date(r.begonnen).toLocaleDateString("de-DE");
    return `<div class="eintrag">
      <div class="kopfzeile"><b>${kontoHtml(titel)}</b>${knopf}
        <button class="stift" title="Bearbeiten"
          onclick="routeBearbeiten('${r.id}')">${STIFT}</button>
        <button class="muell" title="L\u00f6schen"
          data-loeschen="route" data-id="${kontoHtml(r.id)}"
          data-beschreibung="${kontoHtml(`${titel} vom ${datum}, ${r.laenge_km || "?"} km`)}"
          >${MUELLEIMER}</button>
      </div>
      <div class="klein">${new Date(r.begonnen)
        .toLocaleDateString("de-DE")} &middot; ${r.laenge_km || "?"} km
        &middot; ${r.dauer_min || "?"} min ${marke}</div>
      ${r.notiz ? `<div class="klein">${kontoHtml(r.notiz)}</div>` : ""}
    </div>`;
  }).join("") || '<p class="klein">Noch keine Routen.</p>';

  const fundListe = (funde.data || []).map(f => {
    const knopf = (f.lat != null && f.lon != null)
      ? `<button class="zeigen" onclick="zeigeFundAufKarte(
           ${f.lat}, ${f.lon})">Auf der Karte</button>`
      : "";
    // f.art ist der Schluessel ("steinpilz"), nicht der Name
    const name = f.nullfund
      ? "nichts gefunden"
      : ((D.arten[f.art] || {}).name || f.art);
    const datum = new Date(f.gefunden_am).toLocaleDateString("de-DE");
    return `<div class="eintrag">
      <div class="kopfzeile">
        <b>${kontoHtml(name)}</b>${knopf}
        <button class="stift" title="Bearbeiten"
          onclick="fundBearbeiten('${f.id}')">${STIFT}</button>
        <button class="muell" title="L\u00f6schen"
          data-loeschen="fund" data-id="${kontoHtml(f.id)}"
          data-beschreibung="${kontoHtml(`${name} vom ${datum}`)}"
          >${MUELLEIMER}</button>
      </div>
      <div class="klein">${new Date(f.gefunden_am)
        .toLocaleDateString("de-DE")}${f.anzahl
        ? " &middot; " + f.anzahl + " Stück" : ""}</div>
      ${f.notiz ? `<div class="klein">${kontoHtml(f.notiz)}</div>` : ""}
    </div>`;
  }).join("") || '<p class="klein">Noch keine Funde.</p>';

  kasten(`
    <h3>Tagebuch</h3>
    <div class="zahlen">
      <span><b>${z.funde || 0}</b> Funde</span>
      <span><b>${z.arten || 0}</b> Arten</span>
      <span><b>${z.routen || 0}</b> Routen</span>
      <span><b>${(+z.km || 0).toFixed(0)}</b> km</span>
      <span><b>${suchZahl >= 30 ? "30+" : suchZahl}</b> Suchgänge</span>
    </div>
    <h4>Suchgänge</h4>${suchListe}
    ${suchen.error ? "" : `<button class="voll leer" id="suche-nachtragen">
      Suchgang nachtragen</button>`}
    ${widerrufbar ? `<button class="voll leer" id="suche-widerruf">
      Auswertung meiner Suchgänge widerrufen</button>` : ""}
    <h4>Routen</h4>${routenListe}
    <h4>Funde</h4>${fundListe}
    <button class="voll leer" onclick="kastenZu()">Schliessen</button>
  `);
  document.querySelectorAll("#kasten [data-loeschen]").forEach(knopf => {
    knopf.onclick = () => loesche(knopf.dataset.loeschen,
      knopf.dataset.id, knopf.dataset.beschreibung);
  });
  const nachtrag = document.getElementById("suche-nachtragen");
  if (nachtrag) nachtrag.onclick = () => suchgangNachtragen();
  const widerruf = document.getElementById("suche-widerruf");
  if (widerruf) widerruf.onclick = () => suchgangAuswertungWiderrufen();
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
  if (fundFormular?.speichert) return;
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
  if (fundFormular?.speichert) return;
  const el = document.getElementById("kasten");
  if (el) el.hidden = true;
}
