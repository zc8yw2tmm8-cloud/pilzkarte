"use strict";

function waldAuswahlWechseln(aktuell, schluessel) {
  const neu = new Set(aktuell);
  if (neu.has(schluessel)) neu.delete(schluessel);
  else if (schluessel === "gesamt") return new Set(["gesamt"]);
  else {
    neu.delete("gesamt");
    neu.add(schluessel);
  }
  return neu;
}

function waldEinrichten(karte, manifest, leiste, legende, speichern, start = []) {
  let auswahl = new Set(start.filter(s => manifest.ebenen.some(e => e.schluessel === s)));
  const g = manifest.grenzen;
  const grenzen = [[g[0][1], g[1][0]], [g[1][1], g[1][0]],
                   [g[1][1], g[0][0]], [g[0][1], g[0][0]]];
  const knoepfe = new Map();

  function laden(e) {
    const id = "wald_" + e.schluessel;
    if (karte.getLayer(id)) return;
    const bildUrl = datei => datei + (manifest.version ? "?v=" + encodeURIComponent(manifest.version) : "");
    karte.addSource(id, {type: "image", url: bildUrl(e.datei), coordinates: grenzen});
    karte.addLayer({id, type: "raster", source: id,
      layout: {visibility: "none"},
      paint: {"raster-opacity": 0.7, "raster-fade-duration": 0}
    }, karte.getLayer("beschriftung") ? "beschriftung" : undefined);
    if (e.kontur) {
      const kontur = id + "_kontur";
      karte.addSource(kontur, {type: "image", url: bildUrl(e.kontur), coordinates: grenzen});
      karte.addLayer({id: kontur, type: "raster", source: kontur,
        layout: {visibility: "none"},
        paint: {"raster-opacity": ["interpolate", ["linear"], ["zoom"],
          9, 0, 11, 0.3, 13, 0.85], "raster-fade-duration": 0}
      }, karte.getLayer("beschriftung") ? "beschriftung" : undefined);
    }
    // Feste Reihenfolge, unabhaengig von der Klickfolge; Konturen ueber allen Fuellungen.
    for (const suffix of ["", "_kontur"]) {
      for (const ebene of manifest.ebenen) {
        const kennung = "wald_" + ebene.schluessel + suffix;
        if (karte.getLayer(kennung)) karte.moveLayer(kennung,
          karte.getLayer("beschriftung") ? "beschriftung" : undefined);
      }
    }
  }

  function farbpunkt(e) {
    const punkt = document.createElement("span");
    punkt.className = "baumfarbe";
    punkt.style.backgroundColor = e.farbe || "#344b70";
    punkt.setAttribute("aria-hidden", "true");
    return punkt;
  }

  function aktualisieren() {
    legende.replaceChildren();
    for (const e of manifest.ebenen) {
      const an = auswahl.has(e.schluessel);
      const b = knoepfe.get(e.schluessel);
      b.classList.toggle("aktiv", an);
      b.setAttribute("aria-pressed", String(an));
      if (an) laden(e);
      for (const suffix of ["", "_kontur"]) {
        const id = "wald_" + e.schluessel + suffix;
        if (!karte.getLayer(id)) continue;
        if (an) karte.setLayoutProperty(id, "visibility", "visible");
        else {
          karte.removeLayer(id);
          karte.removeSource(id);
        }
      }
      if (an) {
        const eintrag = document.createElement("span");
        eintrag.className = "baumlegende-eintrag";
        eintrag.append(farbpunkt(e), document.createTextNode(e.name));
        legende.append(eintrag);
      }
    }
    legende.hidden = auswahl.size === 0;
  }

  leiste.replaceChildren();
  for (const e of manifest.ebenen) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tag";
    b.dataset.baum = e.schluessel;
    b.setAttribute("aria-pressed", "false");
    b.append(farbpunkt(e), document.createTextNode(e.name));
    b.onclick = () => {
      auswahl = waldAuswahlWechseln(auswahl, e.schluessel);
      aktualisieren();
      speichern();
    };
    knoepfe.set(e.schluessel, b);
    leiste.append(b);
  }
  aktualisieren();
}
