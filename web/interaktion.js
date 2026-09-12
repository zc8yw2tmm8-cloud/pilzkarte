"use strict";

function kompassWinkel(e, bildschirmwinkel = 0) {
  let winkel;
  if (Number.isFinite(e.webkitCompassHeading)) {
    if (Number.isFinite(e.webkitCompassAccuracy) &&
        (e.webkitCompassAccuracy < 0 || e.webkitCompassAccuracy > 50)) return null;
    winkel = e.webkitCompassHeading;
  } else if (e.absolute === true && Number.isFinite(e.alpha)) {
    winkel = 360 - e.alpha;
  } else return null;
  return ((winkel + bildschirmwinkel) % 360 + 360) % 360;
}

function popupGestenTrennen(container, karte) {
  const typen = ["touchstart", "touchmove", "touchend", "touchcancel",
    "pointerdown", "pointermove", "pointerup", "mousedown", "dblclick", "wheel"];
  const stop = e => {
    const popup = e.target.closest?.(".maplibregl-popup");
    if (!popup) return;
    popup.dataset.beruehrt = "1";
    if (["touchstart", "pointerdown", "wheel"].includes(e.type)) karte.stop();
    e.stopPropagation();
  };
  typen.forEach(t => container.addEventListener(t, stop, { capture: true, passive: true }));
  return () => typen.forEach(t => container.removeEventListener(t, stop, true));
}

function blickrichtungEinrichten(karte, orten, melden) {
  let position = null, marker = null, aktiv = false, erlaubt = false;
  let anfrage = false, timer = null;
  const knopf = () => karte.getContainer().querySelector(".maplibregl-ctrl-geolocate");
  const entfernen = () => {
    clearTimeout(timer);
    if (marker) marker.remove();
    marker = null;
  };
  const sensor = e => {
    if (!aktiv || !position || document.hidden) return;
    const winkel = kompassWinkel(e, window.screen?.orientation?.angle ?? window.orientation ?? 0);
    if (winkel === null) { entfernen(); return; }
    if (!marker) {
      const el = document.createElement("div");
      el.className = "blickrichtung";
      el.setAttribute("aria-label", "Blickrichtung");
      const pfeil = document.createElement("span");
      el.appendChild(pfeil);
      marker = new maplibregl.Marker({ element: el, rotationAlignment: "map" })
        .setLngLat(position).addTo(karte);
    }
    marker.setLngLat(position).setRotation(winkel);
    clearTimeout(timer);
    timer = setTimeout(entfernen, 8000);
  };
  const erlauben = async e => {
    if (!e.target.closest?.(".maplibregl-ctrl-geolocate") || erlaubt || anfrage) return;
    const sensorAPI = window.DeviceOrientationEvent;
    if (!sensorAPI) {
      melden("Dieser Browser liefert keine Kompassdaten.");
      return;
    }
    anfrage = true;
    try {
      if (typeof sensorAPI.requestPermission === "function" &&
          await sensorAPI.requestPermission(true) !== "granted") {
        melden("Kompasszugriff nicht erlaubt. Für die Blickrichtung Bewegung und Ausrichtung für diese Website freigeben.");
        return;
      }
      erlaubt = true;
      window.addEventListener("deviceorientation", sensor);
      window.addEventListener("deviceorientationabsolute", sensor);
    } catch (_) {
      melden("Kompasszugriff konnte nicht aktiviert werden. Standortknopf erneut antippen.");
    } finally { anfrage = false; }
  };
  const ort = e => {
    position = [e.coords.longitude, e.coords.latitude];
    aktiv = true;
    if (marker) marker.setLngLat(position);
  };
  const status = () => {
    if (knopf()?.getAttribute("aria-pressed") === "false") {
      aktiv = false;
      entfernen();
    }
  };
  const fehler = () => { aktiv = false; entfernen(); };
  const verborgen = () => { if (document.hidden) entfernen(); };
  const container = karte.getContainer();
  container.addEventListener("click", erlauben, true);
  const beobachter = new MutationObserver(status);
  beobachter.observe(container, { subtree: true, attributes: true, attributeFilter: ["aria-pressed"] });
  orten.on("geolocate", ort);
  orten.on("error", fehler);
  document.addEventListener("visibilitychange", verborgen);
  karte.on("remove", () => {
    entfernen(); beobachter.disconnect();
    container.removeEventListener("click", erlauben, true);
    window.removeEventListener("deviceorientation", sensor);
    window.removeEventListener("deviceorientationabsolute", sensor);
    document.removeEventListener("visibilitychange", verborgen);
    orten.off("geolocate", ort); orten.off("error", fehler);
  });
}
