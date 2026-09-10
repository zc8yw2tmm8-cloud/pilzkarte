"""
Erzeugt aus den heruntergeladenen Baumartenkacheln durchsichtige
Bildebenen: eine je Baumart plus eine fuer "Wald gesamt".

Grundlage sind die Dateien in kacheln/, die baumarten.py geholt hat.
Es wird nichts nachgeladen.

Ergebnis: bilder/wald_gesamt.png, bilder/wald_kiefer.png usw.
Wird von karte.py aufgerufen, laeuft aber auch allein.
"""
import os
import numpy as np



KACHELORDNER = "kacheln"
BILDORDNER = "bilder"

# Gleiche Grenzen wie in baumarten.py
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
KACHELN_X, KACHELN_Y = 4, 4


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


def erzeuge():
    import tempfile
    import rasterio
    from rasterio.shutil import copy as rasterkopie
    from pathlib import Path
    from wald_geo import pruefe_kachel, zielraster, anteilsfenster, geografische_grenzen

    pfade = [Path(KACHELORDNER) / f"k_{iy}_{ix}.tif"
             for iy in range(KACHELN_Y) for ix in range(KACHELN_X)]
    for pfad in pfade:
        pruefe_kachel(pfad)
    transform, breite, hoehe = zielraster((SUED, WEST, NORD, OST))
    grenzen = geografische_grenzen(transform, breite, hoehe)
    ausgaben = [(None, "gesamt", "Wald gesamt", (60, 110, 60))]
    ausgaben += [(k, *v) for k, v in sorted(KLASSEN.items())]
    zaehler = np.zeros(len(ausgaben), dtype=np.int64)
    os.makedirs(BILDORDNER, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=BILDORDNER) as tmp:
        anteilspfad = Path(tmp) / "anteile.tif"
        profil = dict(driver="GTiff", width=breite, height=hoehe,
                      count=len(ausgaben), dtype="uint8", crs="EPSG:3857",
                      transform=transform, tiled=True, compress="deflate")
        with rasterio.open(anteilspfad, "w", **profil) as dst:
            for fenster, klassen in anteilsfenster(pfade, transform, breite, hoehe):
                h, w = int(fenster.height), int(fenster.width)
                for i, (klasse, _, _, _) in enumerate(ausgaben):
                    maske = klassen > 0 if klasse is None else klassen == klasse
                    zaehler[i] += int(maske.sum())
                    anteile = maske.reshape(h, 2, w, 2).mean(axis=(1, 3))
                    dst.write(np.rint(anteile * DECKKRAFT).astype(np.uint8), i+1, window=fenster)
        if zaehler[0] == 0:
            raise ValueError("Keine Waldflaechen im Ausgabegebiet")
        ebenen = []
        with rasterio.open(anteilspfad) as src:
            for i, (_, schluessel, name, farbe) in enumerate(ausgaben):
                anteil = zaehler[i] / zaehler[0]
                if i and anteil < MINDESTANTEIL:
                    continue
                rgba = Path(tmp) / "rgba.tif"
                profil.update(count=4)
                with rasterio.open(rgba, "w", **profil) as dst:
                    dst.colorinterp = (rasterio.enums.ColorInterp.red, rasterio.enums.ColorInterp.green,
                                       rasterio.enums.ColorInterp.blue, rasterio.enums.ColorInterp.alpha)
                    for _, win in src.block_windows(1):
                        alpha = src.read(i+1, window=win)
                        bild = np.empty((4, *alpha.shape), dtype=np.uint8)
                        for kanal in range(3): bild[kanal].fill(farbe[kanal])
                        bild[3] = alpha
                        dst.write(bild, window=win)
                datei = f"wald_{schluessel}.png"
                rasterkopie(rgba, Path(tmp) / datei, driver="PNG", ZLEVEL=6)
                titel = name if i == 0 else f"{name} ({anteil*100:.1f} %)"
                ebenen.append((titel, str(Path(BILDORDNER) / datei).replace(os.sep, "/"), round(anteil*100, 1)))
        # Erst nach vollstaendiger Erzeugung den bisherigen Bestand ersetzen.
        for _, pfad, _ in ebenen:
            os.replace(Path(tmp) / Path(pfad).name, pfad)
        namen = {Path(e[1]).name for e in ebenen}
        for alt in Path(BILDORDNER).glob("wald_*.png"):
            if alt.name not in namen: alt.unlink()
        with open(Path(BILDORDNER) / "wald_grenzen.txt", "w", encoding="utf-8") as f:
            f.write(f"{grenzen[0][0]},{grenzen[0][1]},{grenzen[1][0]},{grenzen[1][1]}\n")
    return [ebenen[0]] + sorted(ebenen[1:], key=lambda e: -e[2]), grenzen


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
