"""
Bereitet die Waldkarte fuer die Website auf.

waldebenen.py erzeugt aus den Thuenen-Kacheln Maskenbilder je Baumart.
Fuer die Website reicht die Gesamtwaldflaeche - sie beantwortet die
Frage, die man auf der Karte hat: Wo ist ueberhaupt Wald?

Ergebnis: web/wald.png und ein Eintrag in web/wald.json
"""
import os
import json
import glob
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

QUELLE = "bilder"
ZIEL = "web"
MAX_BREITE = 2200


def main():
    pfad = os.path.join(QUELLE, "wald_gesamt.png")
    if not os.path.exists(pfad):
        vorhanden = glob.glob(os.path.join(QUELLE, "wald_*.png"))
        print(f"{pfad} fehlt.")
        if vorhanden:
            print(f"Gefunden: {', '.join(os.path.basename(v) for v in vorhanden[:5])}")
        print("Erst karte.py laufen lassen - das erzeugt die Waldebenen.")
        return

    # Die Grenzen stehen in waldebenen.py; sie entsprechen dem
    # Kachelbereich der Thuenen-Karte
    grenzenpfad = os.path.join(QUELLE, "wald_grenzen.txt")
    if os.path.exists(grenzenpfad):
        with open(grenzenpfad, "r", encoding="utf-8") as f:
            sued, west, nord, ost = [float(x) for x in
                                     f.read().strip().split(",")]
    else:
        # Rueckfall auf das Arbeitsgebiet
        sued, west, nord, ost = 52.05, 10.10, 52.85, 11.15
        print("wald_grenzen.txt fehlt - nehme das Arbeitsgebiet.")

    bild = Image.open(pfad)
    breite, hoehe = bild.size
    if breite > MAX_BREITE:
        bild = bild.resize((MAX_BREITE, int(hoehe * MAX_BREITE / breite)),
                           Image.LANCZOS)

    if bild.mode != "RGBA":
        bild = bild.convert("RGBA")

    ziel = os.path.join(ZIEL, "wald.png")
    bild.save(ziel, "PNG", optimize=True)

    with open(os.path.join(ZIEL, "wald.json"), "w", encoding="utf-8") as f:
        json.dump({"datei": "wald.png",
                   "grenzen": [[sued, west], [nord, ost]]}, f)

    vorher = os.path.getsize(pfad) / 1024 / 1024
    nachher = os.path.getsize(ziel) / 1024 / 1024
    print(f"wald.png  {bild.size[0]}x{bild.size[1]}  "
          f"{vorher:.1f} MB -> {nachher:.2f} MB")


main()
