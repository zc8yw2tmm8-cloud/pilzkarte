"""
Erzeugt aus den heruntergeladenen Baumartenkacheln durchsichtige
Bildebenen: eine je Baumart plus eine fuer "Wald gesamt".

Grundlage sind die Dateien in kacheln/, die baumarten.py geholt hat.
Es wird nichts nachgeladen.

Ergebnis: bilder/wald_gesamt.png, bilder/wald_kiefer.png usw.
Wird von karte.py aufgerufen, laeuft aber auch allein.
"""
import os
import math
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

KACHELORDNER = "kacheln"
BILDORDNER = "bilder"

# Gleiche Grenzen wie in baumarten.py
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
KACHELN_X, KACHELN_Y = 4, 4

# Jeder vierte Bildpunkt - 40 m statt 10 m. Fuer eine Uebersichtsebene,
# die man ein- und ausblendet, reicht das voellig. Bei 2 statt 4 werden
# die elf Masken viermal so gross und die Erzeugung dauert viermal
# so lange.
SPARSAM = 4

# Klassenwerte der Thuenen-Karte
KLASSEN = {
    2: ("birke", "Birke", (201, 180, 88)),
    3: ("buche", "Buche", (214, 137, 16)),
    4: ("douglasie", "Douglasie", (56, 142, 60)),
    5: ("eiche", "Eiche", (160, 82, 45)),
    6: ("erle", "Erle", (93, 138, 168)),
    8: ("fichte", "Fichte", (27, 94, 32)),
    9: ("kiefer", "Kiefer", (106, 153, 78)),
    10: ("laerche", "Laerche", (139, 195, 74)),
    14: ("tanne", "Tanne", (46, 125, 50)),
    16: ("laub_lang", "sonst. Laubholz langlebig", (181, 101, 29)),
    17: ("laub_kurz", "sonst. Laubholz kurzlebig", (205, 170, 125)),
}

DECKKRAFT = 165
MINDESTANTEIL = 0.004      # Arten unter 0,4 % der Waldflaeche weglassen


def lade_gesamtbild():
    """Setzt die 16 Kacheln zu einem Bild zusammen."""
    if not os.path.isdir(KACHELORDNER):
        return None

    km_lat = 111.0
    km_lon = 111.0 * math.cos(math.radians((SUED + NORD) / 2))

    teile = {}
    breiten = [0] * KACHELN_X
    hoehen = [0] * KACHELN_Y

    for iy in range(KACHELN_Y):
        for ix in range(KACHELN_X):
            pfad = os.path.join(KACHELORDNER, f"k_{iy}_{ix}.tif")
            if not os.path.exists(pfad):
                return None
            bild = np.array(Image.open(pfad))
            if bild.ndim == 3:
                bild = bild[:, :, 0]
            bild = bild[::SPARSAM, ::SPARSAM]
            teile[(iy, ix)] = bild
            hoehen[iy] = max(hoehen[iy], bild.shape[0])
            breiten[ix] = max(breiten[ix], bild.shape[1])

    gesamt_h = sum(hoehen)
    gesamt_b = sum(breiten)
    voll = np.zeros((gesamt_h, gesamt_b), dtype=np.uint8)

    # Kachelzeile 0 liegt im Sueden, im Bild aber unten
    for iy in range(KACHELN_Y):
        for ix in range(KACHELN_X):
            bild = teile[(iy, ix)]
            y_oben = sum(hoehen[KACHELN_Y - 1 - j] for j in range(KACHELN_Y - 1 - iy))
            x_links = sum(breiten[:ix])
            voll[y_oben:y_oben + bild.shape[0],
                 x_links:x_links + bild.shape[1]] = bild

    return voll


def speichere_maske(maske, farbe, dateiname):
    hoehe, breite = maske.shape
    bild = np.zeros((hoehe, breite, 4), dtype=np.uint8)
    bild[maske, 0] = farbe[0]
    bild[maske, 1] = farbe[1]
    bild[maske, 2] = farbe[2]
    bild[maske, 3] = DECKKRAFT

    os.makedirs(BILDORDNER, exist_ok=True)
    pfad = os.path.join(BILDORDNER, dateiname)
    Image.fromarray(bild, mode="RGBA").save(pfad, compress_level=6)
    return pfad.replace(os.sep, "/")


def erzeuge():
    """
    Rueckgabe: (liste, grenzen)
    liste: [(anzeigename, pfad, anteil_prozent), ...]
    grenzen: [[sued, west], [nord, ost]] fuer ImageOverlay
    """
    voll = lade_gesamtbild()
    if voll is None:
        return [], None

    grenzen = [[SUED, WEST], [NORD, OST]]
    ebenen = []

    wald = voll > 0
    gesamt = int(wald.sum())
    if gesamt == 0:
        return [], None

    pfad = speichere_maske(wald, (60, 110, 60), "wald_gesamt.png")
    ebenen.append(("Wald gesamt", pfad, 100.0))

    for wert, (schluessel, name, farbe) in sorted(
            KLASSEN.items(), key=lambda x: x[0]):
        maske = voll == wert
        n = int(maske.sum())
        anteil = n / gesamt
        if anteil < MINDESTANTEIL:
            continue
        pfad = speichere_maske(maske, farbe, f"wald_{schluessel}.png")
        ebenen.append((f"{name} ({round(anteil * 100, 1)} %)", pfad,
                       round(anteil * 100, 1)))

    # Nach Flaeche sortieren, "Wald gesamt" bleibt vorn
    kopf, rest = ebenen[0], ebenen[1:]
    rest.sort(key=lambda e: -e[2])
    return [kopf] + rest, grenzen


if __name__ == "__main__":
    ebenen, grenzen = erzeuge()
    if not ebenen:
        print(f"Keine Kacheln in {KACHELORDNER}/ gefunden.")
        print("Erst baumarten.py laufen lassen.")
    else:
        print(f"{len(ebenen)} Ebenen erzeugt:\n")
        for name, pfad, anteil in ebenen:
            groesse = os.path.getsize(pfad) / 1024
            print(f"  {name:38s} {round(groesse):5d} KB")
        print(f"\nGrenzen: {grenzen}")
