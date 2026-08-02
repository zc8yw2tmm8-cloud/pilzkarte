"""
Bereitet die Waldkarte fuer die Website auf.

waldebenen.py erzeugt aus den Thuenen-Kacheln Maskenbilder je Baumart.
Fuer die Website reicht die Gesamtwaldflaeche - sie beantwortet die
Frage, die man auf der Karte hat: Wo ist ueberhaupt Wald?

Ergebnis: web/wald/*.png und web/wald.json - eine Ebene je Baumart,
in der Karte einzeln zuschaltbar.
"""
import os
import json
import glob
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

QUELLE = "bilder"
ZIEL = "web"
MAX_BREITE = 2200


BAUMNAMEN = {
    "gesamt": "alles", "kiefer": "Kiefer", "eiche": "Eiche",
    "buche": "Buche", "birke": "Birke", "fichte": "Fichte",
    "laerche": "Laerche", "douglasie": "Douglasie", "erle": "Erle",
    "tanne": "Tanne", "laub_lang": "sonst. Laubholz",
    "laub_kurz": "Weide, Pappel, Aspe",
}

# Reihenfolge in der Leiste: haeufigste zuerst
REIHENFOLGE = ["gesamt", "kiefer", "eiche", "buche", "birke", "erle",
               "fichte", "laerche", "douglasie", "laub_kurz",
               "laub_lang", "tanne"]


def main():
    vorhanden = sorted(glob.glob(os.path.join(QUELLE, "wald_*.png")))
    if not vorhanden:
        print(f"Keine Waldbilder in {QUELLE}/.")
        print("Erst karte.py laufen lassen.")
        return

    grenzenpfad = os.path.join(QUELLE, "wald_grenzen.txt")
    if os.path.exists(grenzenpfad):
        with open(grenzenpfad, "r", encoding="utf-8") as f:
            sued, west, nord, ost = [float(x) for x in
                                     f.read().strip().split(",")]
    else:
        sued, west, nord, ost = 52.05, 10.10, 52.85, 11.15
        print("wald_grenzen.txt fehlt - nehme das Arbeitsgebiet.")

    os.makedirs(os.path.join(ZIEL, "wald"), exist_ok=True)
    for d in os.listdir(os.path.join(ZIEL, "wald")):
        os.remove(os.path.join(ZIEL, "wald", d))

    eintraege = []
    gesamt_vorher = gesamt_nachher = 0

    print(f"{'Baumart':<22}{'vorher':>9}{'nachher':>10}{'Groesse':>13}")

    for schluessel in REIHENFOLGE:
        pfad = os.path.join(QUELLE, f"wald_{schluessel}.png")
        if not os.path.exists(pfad):
            continue

        bild = Image.open(pfad)
        breite, hoehe = bild.size
        if breite > MAX_BREITE:
            bild = bild.resize(
                (MAX_BREITE, int(hoehe * MAX_BREITE / breite)),
                Image.LANCZOS)
        if bild.mode != "RGBA":
            bild = bild.convert("RGBA")

        # Maskenbilder haben wenige Farben - das druecken wir aus
        alpha = bild.split()[3]
        farbig = bild.convert("RGB").quantize(
            colors=16, method=Image.MEDIANCUT, dither=Image.NONE)
        farbig = farbig.convert("RGBA")
        farbig.putalpha(alpha)

        zieldatei = f"wald/wald_{schluessel}.png"
        farbig.save(os.path.join(ZIEL, zieldatei), "PNG", optimize=True)

        vorher = os.path.getsize(pfad) / 1024
        nachher = os.path.getsize(os.path.join(ZIEL, zieldatei)) / 1024
        gesamt_vorher += vorher
        gesamt_nachher += nachher

        print(f"{BAUMNAMEN.get(schluessel, schluessel):<22}"
              f"{vorher:>8.0f}K{nachher:>9.0f}K"
              f"{bild.size[0]:>7}x{bild.size[1]}")

        eintraege.append({
            "schluessel": schluessel,
            "name": BAUMNAMEN.get(schluessel, schluessel),
            "datei": zieldatei,
        })

    with open(os.path.join(ZIEL, "wald.json"), "w", encoding="utf-8") as f:
        json.dump({"grenzen": [[sued, west], [nord, ost]],
                   "ebenen": eintraege}, f, ensure_ascii=False)

    print(f"\n{len(eintraege)} Ebenen, "
          f"{gesamt_vorher/1024:.1f} MB -> {gesamt_nachher/1024:.1f} MB")


main()
