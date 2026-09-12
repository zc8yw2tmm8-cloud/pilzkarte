"""
Bereitet die Reliefbilder fuer die Website auf.

Die Bilder aus relief.py liegen im UTM-Gitter in 2-m-Aufloesung und
sind je Gebiet mehrere Megabyte gross - zu viel fuer eine Seite, die
im Wald ueber Mobilfunk geladen wird.

Dieses Skript
  - verkleinert sie auf etwa 6 m je Bildpunkt. Taeler, Mulden und
    Graeben bleiben sichtbar, nur die feinsten Strukturen verschwinden.
  - legt sie ins Kartenraster um (Laenge/Breite, Zeilen in Mercator).
    Als UTM-Rechteck hingelegt, lagen sie an den Ecken 300 bis 500 m
    daneben, weil die UTM-Gitterlinien auf der Karte schraeg stehen.
  - schneidet beide Bilder auf den Gesamtwald der Karte zu. Vorher lag
    die Schummerung als grauer Schleier ueber dem ganzen Rechteck -
    sie war ein JPEG, und JPEG kennt keine Durchsichtigkeit.

Ergebnis: web/relief/*.png, web/relief/*.webp und web/relief.json
"""
import os
import csv
import json
import math
import numpy as np
from PIL import Image

import relief
import relief_geo as geo

Image.MAX_IMAGE_PIXELS = None

QUELLE = "bilder"
ZIEL = os.path.join("web", "relief")
GRENZEN = "relief_grenzen.csv"
INDEX = os.path.join("web", "relief.json")

# Zielbreite in Bildpunkten. Bei 15 km Gebietsbreite sind 2500 Punkte
# etwa 6 m je Punkt - genug fuer Taeler und Graeben.
MAX_BREITE = 2500

# Farbstufen der Feuchtekarte. 64 reichen fuer einen Verlauf und
# druecken die Datei auf einen Bruchteil.
FARBEN = 64

# Die Schummerung als WebP mit Durchsichtigkeit: etwa so klein wie
# das fruehere JPEG, aber mit Loechern, wo kein Wald ist. Safari kann
# WebP seit iOS 14.
WEBP_GUETE = 80

# Bildzeilen je Rechenschritt - haelt den Speicherbedarf klein
STREIFEN = 256


def utm_rahmen(g, bildgroesse):
    """
    Das UTM-Rechteck eines Gebiets zurueckgewinnen.

    relief_grenzen.csv haelt SW- und NO-Ecke in Grad. Die DGM-Kacheln
    liegen auf vollen Kilometern, also wird darauf gerundet und an der
    Bildgroesse geprueft.
    """
    ost_min, nord_min = relief.wgs84_zu_utm(float(g["sued"]), float(g["west"]))
    ost_max, nord_max = relief.wgs84_zu_utm(float(g["nord"]), float(g["ost"]))
    rahmen = tuple(round(x / 1000.0) * 1000.0
                   for x in (ost_min, nord_min, ost_max, nord_max))
    schritt_x = (rahmen[2] - rahmen[0]) / bildgroesse[0]
    schritt_y = (rahmen[3] - rahmen[1]) / bildgroesse[1]
    if abs(schritt_x - schritt_y) > 0.01:
        raise ValueError(f"{g['gebiet']}: Bild {bildgroesse} passt nicht "
                         f"zum UTM-Rahmen {rahmen}")
    return rahmen


def lade_verkleinert(pfad, breite):
    """RGBA-Bild auf die gegebene Breite, als numpy-Feld."""
    with Image.open(pfad) as bild:
        if bild.mode != "RGBA":
            bild = bild.convert("RGBA")
        hoehe = round(bild.height * breite / bild.width)
        # Pillow rechnet RGBA dabei mit vormultipliziertem Alpha - an
        # den Waldraendern entstehen keine dunklen Saeume
        return np.array(bild.resize((breite, hoehe), Image.LANCZOS))


def umlegen(quellen, rahmen, raster, maske):
    """
    Tastet die UTM-Bilder im Kartenraster ab (naechster Nachbar) und
    macht alles ausserhalb des Waldes durchsichtig.
    """
    sued, west, nord, ost, hoehe = raster
    ost_min, nord_min, ost_max, nord_max = rahmen
    lon = geo.rasterspalten(west, ost, MAX_BREITE)
    ergebnis = {art: np.zeros((hoehe, MAX_BREITE, 4), dtype=np.uint8)
                for art in quellen}
    hq, bq = next(iter(quellen.values())).shape[:2]

    for y0 in range(0, hoehe, STREIFEN):
        y1 = min(hoehe, y0 + STREIFEN)
        lat = geo.rasterzeilen(sued, nord, hoehe, y0, y1)
        lon_f, lat_f = np.meshgrid(lon, lat)
        e, n = geo.wgs84_zu_utm(lat_f, lon_f)
        spalte = np.floor((e - ost_min) / (ost_max - ost_min) * bq).astype(np.int64)
        zeile = np.floor((nord_max - n) / (nord_max - nord_min) * hq).astype(np.int64)
        innen = (spalte >= 0) & (spalte < bq) & (zeile >= 0) & (zeile < hq)
        if maske is not None:
            innen &= maske.wald(lat_f, lon_f)
        for art, q in quellen.items():
            stueck = np.zeros((y1 - y0, MAX_BREITE, 4), dtype=np.uint8)
            stueck[innen] = q[zeile[innen], spalte[innen]]
            ergebnis[art][y0:y1] = stueck
    return ergebnis


def speichere_feuchte(feld, ziel):
    """Auf 64 Farben reduziert, die Durchsichtigkeit bleibt."""
    bild = Image.fromarray(feld, mode="RGBA")
    alpha = bild.getchannel("A")
    farbig = bild.convert("RGB").quantize(
        colors=FARBEN, method=Image.MEDIANCUT, dither=Image.NONE)
    farbig = farbig.convert("RGBA")
    farbig.putalpha(alpha)
    farbig.save(ziel, "PNG", optimize=True)


def speichere_schummerung(feld, ziel):
    Image.fromarray(feld, mode="RGBA").save(
        ziel, "WEBP", quality=WEBP_GUETE, alpha_quality=90, method=6)


def main():
    if not os.path.exists(GRENZEN):
        print(f"{GRENZEN} fehlt. Erst relief.py laufen lassen.")
        return

    with open(GRENZEN, "r", encoding="utf-8") as f:
        gebiete = list(csv.DictReader(f))
    if not gebiete:
        print("Keine Gebiete eingetragen.")
        return

    maske = geo.Waldmaske.laden()
    if maske is None:
        print("Waldebene fehlt (web/wald.json) - Relief wird nicht "
              "auf den Wald zugeschnitten.")

    os.makedirs(ZIEL, exist_ok=True)
    eintraege = []
    gesamt_vorher = gesamt_nachher = 0

    print(f"{'Gebiet':<16}{'Art':<14}{'vorher':>9}{'nachher':>9}"
          f"{'Groesse':>13}")

    for g in gebiete:
        schluessel = g["gebiet"]
        teil = f"_{schluessel}" if schluessel else ""
        arten = [("feuchte", ".png", speichere_feuchte),
                 ("schummerung", ".webp", speichere_schummerung)]
        pfade = {art: os.path.join(QUELLE, f"relief{teil}_{art}.png")
                 for art, _, _ in arten}
        pfade = {art: p for art, p in pfade.items() if os.path.exists(p)}
        if not pfade:
            continue

        with Image.open(next(iter(pfade.values()))) as probe:
            groesse = probe.size
        rahmen = utm_rahmen(g, groesse)
        raster = geo.umschliessendes_raster(rahmen, MAX_BREITE)
        sued, west, nord, ost, hoehe = raster

        # Quelle etwa auf die Aufloesung des Ziels bringen, bevor
        # abgetastet wird - sonst flimmert die Schummerung
        m_je_punkt = ((ost - west) * 111320.0
                      * math.cos(math.radians((sued + nord) / 2)) / MAX_BREITE)
        breite_quelle = round((rahmen[2] - rahmen[0]) / m_je_punkt)
        quellen = {art: lade_verkleinert(p, breite_quelle)
                   for art, p in pfade.items()}
        umgelegt = umlegen(quellen, rahmen, raster, maske)
        del quellen

        dateien = {}
        for art, endung, speichern in arten:
            if art not in umgelegt:
                continue
            zieldatei = f"relief{teil}_{art}{endung}"
            speichern(umgelegt[art], os.path.join(ZIEL, zieldatei))

            vorher = os.path.getsize(pfade[art]) / 1024 / 1024
            nachher = os.path.getsize(os.path.join(ZIEL, zieldatei)) / 1024 / 1024
            gesamt_vorher += vorher
            gesamt_nachher += nachher
            print(f"{schluessel:<16}{art:<14}{vorher:>8.1f}M"
                  f"{nachher:>8.2f}M{MAX_BREITE:>7}x{hoehe}")
            dateien[art] = f"relief/{zieldatei}"

        eintraege.append({
            "gebiet": schluessel,
            "titel": g.get("titel") or schluessel,
            "grenzen": [[round(sued, 6), round(west, 6)],
                        [round(nord, 6), round(ost, 6)]],
            "dateien": dateien,
        })

    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(eintraege, f, ensure_ascii=False, indent=1)

    print(f"\n{len(eintraege)} Gebiete in {INDEX}")
    print(f"Zusammen {gesamt_vorher:.0f} MB -> {gesamt_nachher:.1f} MB")
    print("\nWeiter: die Dateien einchecken und die Seite neu bauen.")


if __name__ == "__main__":
    main()
