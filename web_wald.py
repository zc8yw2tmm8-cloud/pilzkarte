"""
Bereitet die Waldkarte fuer die Website auf.

waldebenen.py erzeugt aus den Thuenen-Kacheln Maskenbilder je Baumart.
Ergebnis: web/wald/*.png und web/wald.json mit transparenten
Farbflächen je Baumart.
"""
import os
import json
import glob
import tempfile
import hashlib
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

QUELLE = "bilder"
ZIEL = "web"


BAUMNAMEN = {
    "gesamt": "Gesamter Wald", "kiefer": "Kiefer", "eiche": "Eiche",
    "buche": "Buche", "birke": "Birke", "fichte": "Fichte",
    "laerche": "Laerche", "douglasie": "Douglasie", "erle": "Erle",
    "tanne": "Tanne", "laub_lang": "sonst. Laubholz",
    "laub_kurz": "Weide, Pappel, Aspe",
}

BAUMFARBEN = {
    "gesamt": "#344b70", "kiefer": "#007fa8", "eiche": "#e38b18",
    "buche": "#834dc4", "birke": "#e6c938", "erle": "#98634b",
    "fichte": "#2547a8", "laerche": "#cf5eac", "douglasie": "#55bde0",
    "laub_kurz": "#bba0e8", "laub_lang": "#9b7b20", "tanne": "#456773",
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
        raise ValueError("wald_grenzen.txt fehlt; keine geschaetzten Bildgrenzen verwenden")

    os.makedirs(os.path.join(ZIEL, "wald"), exist_ok=True)

    with tempfile.TemporaryDirectory(dir=ZIEL) as tmp:
        eintraege = []
        gesamt_vorher = gesamt_nachher = 0

        print(f"{'Baumart':<22}{'vorher':>9}{'nachher':>10}{'Groesse':>13}")

        for schluessel in REIHENFOLGE:
            pfad = os.path.join(QUELLE, f"wald_{schluessel}.png")
            if not os.path.exists(pfad):
                continue

            with Image.open(pfad) as quelle:
                alpha = quelle.convert("RGBA").getchannel("A")
            bild = Image.new("RGBA", alpha.size, BAUMFARBEN[schluessel])
            bild.putalpha(alpha)
            zieldatei = f"wald/wald_{schluessel}.png"
            bild.save(os.path.join(tmp, os.path.basename(zieldatei)), "PNG", optimize=True)

            vorher = os.path.getsize(pfad) / 1024
            nachher = os.path.getsize(os.path.join(tmp, os.path.basename(zieldatei))) / 1024
            gesamt_vorher += vorher
            gesamt_nachher += nachher

            print(f"{BAUMNAMEN.get(schluessel, schluessel):<22}"
                  f"{vorher:>8.0f}K{nachher:>9.0f}K"
                  f"{bild.size[0]:>7}x{bild.size[1]}")

            eintraege.append({
                "schluessel": schluessel,
                "name": BAUMNAMEN.get(schluessel, schluessel),
                "datei": zieldatei,
                "farbe": BAUMFARBEN[schluessel],
            })

        with open(os.path.join(tmp, "wald.json"), "w", encoding="utf-8") as f:
            version = hashlib.sha256()
            for e in eintraege:
                with open(os.path.join(tmp, os.path.basename(e["datei"])), "rb") as bilddatei:
                    for teil in iter(lambda: bilddatei.read(1024 * 1024), b""):
                        version.update(teil)
            json.dump({"grenzen": [[sued, west], [nord, ost]],
                       "version": version.hexdigest()[:12], "ebenen": eintraege}, f, ensure_ascii=False)
        for e in eintraege:
            os.replace(os.path.join(tmp, os.path.basename(e["datei"])), os.path.join(ZIEL, e["datei"]))
        os.replace(os.path.join(tmp, "wald.json"), os.path.join(ZIEL, "wald.json"))

    print(f"\n{len(eintraege)} Ebenen, "
          f"{gesamt_vorher/1024:.1f} MB -> {gesamt_nachher/1024:.1f} MB")


if __name__ == "__main__":
    main()
