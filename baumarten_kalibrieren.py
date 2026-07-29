"""
Misst, welche Baumarten die Pilze tatsaechlich bevorzugen.

Bisher sind die Gewichte in arten.py aus der Pilzliteratur geschaetzt.
Dieses Skript vergleicht die Baumarten AN DEN FUNDORTEN mit denen in
der Region - dieselbe Methode wie bei Wetter und Boden.

Braucht nur, was schon da ist:
  kacheln/          die Baumartenkacheln von baumarten.py
  funde_arten.csv   die GBIF-Fundmeldungen

Ergebnis: Tabelle im Terminal und baumarten_gewichte.txt zum Einsetzen.
"""
import os
import csv
import math
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

KACHELORDNER = "kacheln"
FUNDE_DATEI = "funde_arten.csv"
AUFWAND_DATEI = "aufwand_orte.csv"
AUSGABE = "baumarten_gewichte.txt"

# Gleiche Grenzen wie baumarten.py
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
KACHELN_X, KACHELN_Y = 4, 4

# Fenster um einen Fundort, in Bildpunkten (10 m). 5 = 50 x 50 m.
# GBIF-Koordinaten sind selten punktgenau, ein Fenster faengt das ab.
FENSTER = 5

MAX_UNSICHERHEIT = 500     # ungenauere Fundorte weglassen
MINDEST_FUNDE = 40         # weniger sagt nichts

KLASSEN = {
    2: "birke", 3: "buche", 4: "douglasie", 5: "eiche", 6: "erle",
    8: "fichte", 9: "kiefer", 10: "laerche", 14: "tanne",
    16: "laub_lang", 17: "laub_kurz",
}

NAMEN = {
    "birke": "Birke", "buche": "Buche", "douglasie": "Douglasie",
    "eiche": "Eiche", "erle": "Erle", "fichte": "Fichte",
    "kiefer": "Kiefer", "laerche": "Laerche", "tanne": "Tanne",
    "laub_lang": "sonst. Laubholz lang", "laub_kurz": "sonst. Laubholz kurz",
}


def lade_raster():
    """Setzt die Kacheln zu einem Bild zusammen."""
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
            teile[(iy, ix)] = bild
            hoehen[iy] = max(hoehen[iy], bild.shape[0])
            breiten[ix] = max(breiten[ix], bild.shape[1])

    voll = np.zeros((sum(hoehen), sum(breiten)), dtype=np.uint8)
    for iy in range(KACHELN_Y):
        for ix in range(KACHELN_X):
            bild = teile[(iy, ix)]
            # Kachelzeile 0 liegt im Sueden, im Bild also unten
            y = sum(hoehen[KACHELN_Y - 1 - j] for j in range(KACHELN_Y - 1 - iy))
            x = sum(breiten[:ix])
            voll[y:y + bild.shape[0], x:x + bild.shape[1]] = bild
    return voll


def bildpunkt(lat, lon, form):
    hoehe, breite = form
    x = int((lon - WEST) / (OST - WEST) * breite)
    y = int((NORD - lat) / (NORD - SUED) * hoehe)
    if 0 <= x < breite and 0 <= y < hoehe:
        return y, x
    return None


def lade_funde():
    funde = defaultdict(list)
    if not os.path.exists(FUNDE_DATEI):
        return funde
    with open(FUNDE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                lat, lon = float(z["lat"]), float(z["lon"])
            except (ValueError, KeyError):
                continue
            if not (SUED <= lat <= NORD and WEST <= lon <= OST):
                continue
            u = z.get("unsicherheit_m", "")
            if u not in ("", None):
                try:
                    if float(u) > MAX_UNSICHERHEIT:
                        continue
                except ValueError:
                    pass
            funde[z["art"]].append((lat, lon))
    return funde


def orte_auszaehlen(raster, orte):
    """Baumarten in einem Fenster um jeden Ort zaehlen."""
    treffer = Counter()
    ohne_wald = 0
    im_bild = 0

    for lat, lon in orte:
        p = bildpunkt(lat, lon, raster.shape)
        if p is None:
            continue
        im_bild += 1
        y, x = p
        y0, y1 = max(0, y - FENSTER), min(raster.shape[0], y + FENSTER + 1)
        x0, x1 = max(0, x - FENSTER), min(raster.shape[1], x + FENSTER + 1)
        fenster = raster[y0:y1, x0:x1]
        wald = fenster[fenster > 0]
        if wald.size == 0:
            ohne_wald += 1
            continue
        for w, n in zip(*np.unique(wald, return_counts=True)):
            if int(w) in KLASSEN:
                treffer[KLASSEN[int(w)]] += int(n)

    return treffer, im_bild, ohne_wald


def lade_aufwandsorte():
    """Fundorte aller Pilzmeldungen - der Massstab fuer Sammlerdichte."""
    if not os.path.exists(AUFWAND_DATEI):
        return []
    orte = []
    with open(AUFWAND_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                orte.append((float(z["lat"]), float(z["lon"])))
            except (ValueError, KeyError):
                continue
    return orte


def main():
    print("Lese Baumartenkacheln ...")
    raster = lade_raster()
    if raster is None:
        print(f"Kacheln in {KACHELORDNER}/ fehlen. Erst baumarten.py.")
        return
    print(f"  {raster.shape[1]} x {raster.shape[0]} Bildpunkte")

    # Hintergrund: alle Waldpunkte der Region
    werte, anzahl = np.unique(raster[raster > 0], return_counts=True)
    hintergrund = Counter()
    for w, n in zip(werte.tolist(), anzahl.tolist()):
        if w in KLASSEN:
            hintergrund[KLASSEN[w]] += n
    gesamt_hg = sum(hintergrund.values())

    print(f"  {gesamt_hg} Waldbildpunkte in der Region\n")
    print("Baumarten in der Region:")
    for art, n in hintergrund.most_common():
        print(f"  {NAMEN[art]:24s}{n / gesamt_hg * 100:6.1f} %")

    # Wenn Meldeorte aller Pilze vorliegen, sind DIE der Massstab.
    # Sonst misst der Vergleich nur, wo Menschen spazieren gehen.
    massstab_text = "in Region"
    aufwandsorte = lade_aufwandsorte()
    if aufwandsorte:
        a_treffer, a_im_bild, a_ohne = orte_auszaehlen(raster, aufwandsorte)
        if sum(a_treffer.values()) > 10000:
            hintergrund = a_treffer
            gesamt_hg = sum(hintergrund.values())
            massstab_text = "bei Sammlern"
            print(f"\nMassstab: {a_im_bild} Meldeorte aller Pilze "
                  f"({a_ohne} ausserhalb des Waldes)")
            print("Baumarten an Meldeorten:")
            for art, n in hintergrund.most_common():
                print(f"  {NAMEN[art]:24s}{n / gesamt_hg * 100:6.1f} %")
        else:
            print("\nZu wenige Meldeorte - vergleiche gegen die Region.")
    else:
        print(f"\n{AUFWAND_DATEI} fehlt - vergleiche gegen die Region.")
        print("ACHTUNG: Dann misst das Ergebnis zum grossen Teil, wo")
        print("Menschen unterwegs sind. Erst aufwand_orte.py laufen lassen.")

    funde = lade_funde()
    if not funde:
        print(f"\nKeine Funde in {FUNDE_DATEI} im Gebiet.")
        return

    zeilen_aus = []
    print("\n" + "=" * 66)
    if massstab_text == "bei Sammlern":
        print("Auswahlverhaeltnis: Baumart am Fundort gegen die Baumarten")
        print("an ALLEN Pilzmeldeorten - Sammlerdichte ist herausgerechnet")
    else:
        print("Auswahlverhaeltnis: Baumart am Fundort gegen Region")
        print("ACHTUNG: OHNE Aufwandskorrektur - erst aufwand_orte.py")
    print("1.00 = kein Signal, 2.00 = doppelt so haeufig wie zufaellig")
    print("=" * 66)

    for pilzart in sorted(funde):
        orte = funde[pilzart]
        treffer, im_bild, ohne_wald = orte_auszaehlen(raster, orte)

        gesamt = sum(treffer.values())
        if gesamt == 0 or im_bild - ohne_wald < MINDEST_FUNDE:
            print(f"\n{pilzart.upper()}: nur "
                  f"{im_bild - ohne_wald} Fundorte im Wald, zu wenig")
            continue

        print(f"\n{pilzart.upper()}  ({im_bild - ohne_wald} Fundorte im "
              f"Wald, {ohne_wald} ausserhalb)")
        print(f"  {'Baumart':<24}{'am Fundort':>12}{massstab_text:>13}"
              f"{'Verhaeltnis':>13}")

        verhaeltnisse = {}
        for art in sorted(hintergrund, key=lambda a: -hintergrund[a]):
            h_anteil = hintergrund[art] / gesamt_hg
            f_anteil = treffer.get(art, 0) / gesamt
            if h_anteil < 0.002:
                continue
            v = f_anteil / h_anteil if h_anteil else 0
            verhaeltnisse[art] = v
            marke = ("  <<<" if v >= 1.5 else "  <" if v >= 1.15
                     else "  --" if v <= 0.6 else "")
            print(f"  {NAMEN[art]:<24}{f_anteil*100:11.1f}%"
                  f"{h_anteil*100:12.1f}%{v:12.2f}{marke}")

        # Gewichte: hoechstes Verhaeltnis wird 1.0
        hoechstes = max(verhaeltnisse.values()) if verhaeltnisse else 1
        gewichte = {a: round(max(0.05, min(1.0, v / hoechstes)), 2)
                    for a, v in verhaeltnisse.items()}
        # Arten ohne genug Hintergrund neutral ergaenzen
        for a in NAMEN:
            gewichte.setdefault(a, 0.5)

        text = ('        "baumarten": {'
                + ", ".join(f'"{a}": {gewichte[a]}' for a in
                            sorted(gewichte, key=lambda x: -gewichte[x]))
                + "},")
        zeilen_aus.append(f"# {pilzart}\n{text}\n")

    if zeilen_aus:
        kopf = (f"# Massstab: {massstab_text}\n"
                f"# {'MIT' if massstab_text == 'bei Sammlern' else 'OHNE'} "
                f"Aufwandskorrektur\n\n")
        with open(AUSGABE, "w", encoding="utf-8") as f:
            f.write(kopf + "\n".join(zeilen_aus))
        print(f"\n\nGewichte zum Einsetzen liegen in {AUSGABE}.")
        print("Vorher lesen - Beobachterverzerrung ist hier besonders")
        print("wahrscheinlich, weil Eichenwaelder oft naeher an Ortschaften")
        print("liegen als Kiefernforste.")


main()