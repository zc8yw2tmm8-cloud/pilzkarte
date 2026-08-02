"""
Bereitet die Reliefbilder fuer die Website auf.

Die Bilder aus relief.py liegen in 2-m-Aufloesung und sind je Gebiet
mehrere Megabyte gross - zu viel fuer eine Seite, die im Wald ueber
Mobilfunk geladen wird.

Dieses Skript verkleinert sie und legt sie nach web/relief/. Der
Verlust ist gering: Bei 6 m sieht man Taeler, Mulden und Graeben
weiterhin, nur die feinsten Strukturen verschwinden.

Ergebnis: web/relief/*.jpg und web/relief.json
"""
import os
import json
import csv
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

QUELLE = "bilder"
ZIEL = os.path.join("web", "relief")
GRENZEN = "relief_grenzen.csv"
INDEX = os.path.join("web", "relief.json")

# Zielbreite in Bildpunkten. Bei 15 km Gebietsbreite sind 2500 Punkte
# etwa 6 m je Punkt - genug fuer Taeler und Graeben.
MAX_BREITE = 2500

# JPEG-Guete fuer die Schummerung. Die ist ein Graustufenbild ohne
# scharfe Kanten, da faellt Kompression kaum auf.
GUETE = 78

# Farbstufen der Feuchtekarte. 64 reichen fuer einen Verlauf und
# druecken die Datei auf einen Bruchteil.
FARBEN = 64


def verkleinere(pfad, ziel, durchsichtig):
    """
    Verkleinert ein Bild.

    Die Feuchtekarte braucht Durchsichtigkeit (nur ueber Wald), also
    PNG. Die Schummerung deckt die ganze Flaeche ab - dort spart JPEG
    ein Vielfaches.
    """
    bild = Image.open(pfad)
    breite, hoehe = bild.size

    if breite > MAX_BREITE:
        neu = (MAX_BREITE, int(hoehe * MAX_BREITE / breite))
        bild = bild.resize(neu, Image.LANCZOS)

    if durchsichtig:
        # Auf 64 Farben reduzieren. Die Feuchtekarte hat ohnehin nur
        # einen Farbverlauf - das spart ein Vielfaches, ohne dass man
        # es sieht. Die Durchsichtigkeit bleibt erhalten.
        if bild.mode != "RGBA":
            bild = bild.convert("RGBA")
        alpha = bild.split()[3]
        farbig = bild.convert("RGB").quantize(
            colors=FARBEN, method=Image.MEDIANCUT, dither=Image.NONE)
        farbig = farbig.convert("RGBA")
        farbig.putalpha(alpha)
        farbig.save(ziel, "PNG", optimize=True)
    else:
        # Durchsichtige Stellen werden dunkel wie der Kartenhintergrund
        if bild.mode == "RGBA":
            grund = Image.new("RGB", bild.size, (21, 24, 28))
            grund.paste(bild, mask=bild.split()[3])
            bild = grund
        bild.convert("RGB").save(ziel, "JPEG", quality=GUETE,
                                 optimize=True, progressive=True)

    return bild.size


def main():
    if not os.path.exists(GRENZEN):
        print(f"{GRENZEN} fehlt. Erst relief.py laufen lassen.")
        return

    with open(GRENZEN, "r", encoding="utf-8") as f:
        gebiete = list(csv.DictReader(f))

    if not gebiete:
        print("Keine Gebiete eingetragen.")
        return

    os.makedirs(ZIEL, exist_ok=True)
    eintraege = []
    gesamt_vorher = gesamt_nachher = 0

    print(f"{'Gebiet':<16}{'Art':<14}{'vorher':>9}{'nachher':>9}"
          f"{'Groesse':>13}")

    for g in gebiete:
        schluessel = g["gebiet"]
        teil = f"_{schluessel}" if schluessel else ""

        dateien = {}
        for art, endung, durchsichtig in [
            ("feuchte", ".png", True),
            ("schummerung", ".jpg", False),
        ]:
            quelle = os.path.join(QUELLE, f"relief{teil}_{art}.png")
            if not os.path.exists(quelle):
                continue

            zieldatei = f"relief{teil}_{art}{endung}"
            groesse = verkleinere(quelle, os.path.join(ZIEL, zieldatei),
                                  durchsichtig)

            vorher = os.path.getsize(quelle) / 1024 / 1024
            nachher = os.path.getsize(
                os.path.join(ZIEL, zieldatei)) / 1024 / 1024
            gesamt_vorher += vorher
            gesamt_nachher += nachher

            print(f"{schluessel:<16}{art:<14}{vorher:>8.1f}M"
                  f"{nachher:>8.2f}M{groesse[0]:>7}x{groesse[1]}")

            dateien[art] = f"relief/{zieldatei}"

        if dateien:
            eintraege.append({
                "gebiet": schluessel,
                "titel": g.get("titel") or schluessel,
                "grenzen": [[float(g["sued"]), float(g["west"])],
                            [float(g["nord"]), float(g["ost"])]],
                "dateien": dateien,
            })

    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(eintraege, f, ensure_ascii=False, indent=1)

    print(f"\n{len(eintraege)} Gebiete in {INDEX}")
    print(f"Zusammen {gesamt_vorher:.0f} MB -> {gesamt_nachher:.1f} MB")
    print("\nWeiter: die Dateien einchecken und die Seite neu bauen.")


main()
