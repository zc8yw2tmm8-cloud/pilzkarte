"""
Feinkarte der feuchten Senken aus dem 1-m-Hoehenmodell.

Erwartet DGM1-Kacheln im Ordner dgm/ (GeoTIFF, 32-Bit-Float, UTM32,
Leerwert -9999) - so wie das LGLN sie unter CC BY 4.0 herausgibt.
Die Dateinamen muessen die UTM-Kilometerkoordinaten enthalten, wie
bei "dgm1_32_605_5808_1_ni_2024.tif".

Berechnet drei Groessen und daraus einen Feuchteindex:
  Senkentiefe    - wie tief ein Punkt unter seiner Umgebung liegt
  Hangneigung    - flach haelt Wasser, steil laesst es ablaufen
  Nordexposition - Nordhaenge trocknen langsamer aus

Ergebnis: bilder/relief_feuchte.png und relief_schummerung.png
plus die Eckkoordinaten fuer die Karte.

Braucht numpy und pillow. Kein Netzzugang.
"""
import os
import glob
import math
import re
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

DGM_ORDNER = "dgm"
BILDORDNER = "bilder"

# Umgebungsradius fuer die Senkentiefe, in Metern.
# 150 m fasst eine Talmulde, 30 m nur einen Graben.
UMGEBUNG_M = 150

# Auf diese Rasterweite ausduennen. 2 m reicht fuer die Darstellung
# und viertelt den Speicherbedarf.
SPARSAM = 2

LEERWERT = -9999.0


def utm_zu_wgs84(ost, nord, zone=32):
    """UTM nach Laenge/Breite. Standardformeln, ohne Zusatzbibliothek."""
    a = 6378137.0
    f = 1 / 298.257223563
    k0 = 0.9996
    e2 = f * (2 - f)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))

    x = ost - 500000.0
    y = nord

    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))

    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu))

    n1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = e2 / (1 - e2) * math.cos(phi1) ** 2
    r1 = a * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * k0)

    breite = phi1 - (n1 * math.tan(phi1) / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * e2 / (1 - e2))
        * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2
           - 252 * e2 / (1 - e2) - 3 * c1 ** 2) * d ** 6 / 720)

    laenge = (d - (1 + 2 * t1 + c1) * d ** 3 / 6
              + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2
                 + 8 * e2 / (1 - e2) + 24 * t1 ** 2) * d ** 5 / 120
              ) / math.cos(phi1)

    mittelmeridian = (zone - 1) * 6 - 180 + 3
    return math.degrees(breite), mittelmeridian + math.degrees(laenge)


def kachelkoordinaten(pfad):
    """Sucht die UTM-Kilometerangaben im Dateinamen."""
    name = os.path.basename(pfad)
    zahlen = re.findall(r"(?<!\d)(\d{3,4})(?!\d)", name)
    kandidaten = []
    for i in range(len(zahlen) - 1):
        ost, nord = int(zahlen[i]), int(zahlen[i + 1])
        # Ost 280-920 km, Nord 5230-6110 km deckt Deutschland ab
        if 280 <= ost <= 920 and 5230 <= nord <= 6110:
            kandidaten.append((ost * 1000, nord * 1000))
    return kandidaten[0] if kandidaten else None


def lade_kacheln():
    pfade = sorted(glob.glob(os.path.join(DGM_ORDNER, "*.tif"))
                   + glob.glob(os.path.join(DGM_ORDNER, "*.tiff")))
    if not pfade:
        return None, None

    kacheln = []
    for pfad in pfade:
        ecke = kachelkoordinaten(pfad)
        if ecke is None:
            print(f"  {os.path.basename(pfad)}: keine UTM-Angabe im Namen")
            continue
        try:
            bild = np.array(Image.open(pfad)).astype(np.float32)
        except Exception as e:
            print(f"  {os.path.basename(pfad)}: nicht lesbar ({str(e)[:60]})")
            continue
        if bild.ndim == 3:
            bild = bild[:, :, 0]
        kacheln.append((ecke[0], ecke[1], bild))
        print(f"  {os.path.basename(pfad)}: {bild.shape[1]}x{bild.shape[0]} px, "
              f"Ecke {ecke[0]//1000}/{ecke[1]//1000}")

    if not kacheln:
        return None, None

    # Gemeinsames Gitter aufbauen. Kachelecke ist die SUEDWEST-Ecke,
    # im Bild liegt Norden aber oben.
    ost_min = min(k[0] for k in kacheln)
    nord_min = min(k[1] for k in kacheln)
    ost_max = max(k[0] + k[2].shape[1] for k in kacheln)
    nord_max = max(k[1] + k[2].shape[0] for k in kacheln)

    breite = ost_max - ost_min
    hoehe = nord_max - nord_min
    voll = np.full((hoehe, breite), LEERWERT, dtype=np.float32)

    for ost, nord, bild in kacheln:
        h, b = bild.shape
        x0 = ost - ost_min
        y0 = nord_max - (nord + h)
        voll[y0:y0 + h, x0:x0 + b] = bild

    rahmen = (ost_min, nord_min, ost_max, nord_max)
    return voll, rahmen


def kastenmittel(feld, gueltig, radius):
    """
    Mittelwert im Quadrat um jeden Punkt, ueber Summenbilder.
    Beruecksichtigt nur gueltige Werte - schnell und ohne scipy.
    """
    werte = np.where(gueltig, feld, 0.0).astype(np.float64)
    zahl = gueltig.astype(np.float64)

    def summenbild(a):
        s = np.zeros((a.shape[0] + 1, a.shape[1] + 1), dtype=np.float64)
        s[1:, 1:] = a.cumsum(axis=0).cumsum(axis=1)
        return s

    sw = summenbild(werte)
    sz = summenbild(zahl)

    h, b = feld.shape
    y, x = np.ogrid[:h, :b]
    y0 = np.clip(y - radius, 0, h)
    y1 = np.clip(y + radius + 1, 0, h)
    x0 = np.clip(x - radius, 0, b)
    x1 = np.clip(x + radius + 1, 0, b)

    def bereich(s):
        return (s[y1, x1] - s[y0, x1] - s[y1, x0] + s[y0, x0])

    summe = bereich(sw)
    anzahl = bereich(sz)
    ergebnis = np.zeros_like(feld)
    hat = anzahl > 0
    ergebnis[hat] = (summe[hat] / anzahl[hat]).astype(np.float32)
    return ergebnis, hat


def faerbe(wert, gueltig, skala, dateiname, deckkraft=190):
    """wert: 0..1. skala: Liste von (position, (r,g,b))."""
    h, b = wert.shape
    stufen = np.clip(wert * 255, 0, 255).astype(np.uint8)

    tabelle = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        p = i / 255.0
        for j in range(len(skala) - 1):
            p0, c0 = skala[j]
            p1, c1 = skala[j + 1]
            if p0 <= p <= p1:
                t = (p - p0) / (p1 - p0) if p1 > p0 else 0
                tabelle[i] = [int(c0[k] + (c1[k] - c0[k]) * t)
                              for k in range(3)]
                break

    rgb = tabelle[stufen]
    alpha = np.where(gueltig, (wert * deckkraft).astype(np.uint8), 0)
    bild = np.dstack([rgb, alpha[:, :, None]])

    os.makedirs(BILDORDNER, exist_ok=True)
    pfad = os.path.join(BILDORDNER, dateiname)
    Image.fromarray(bild.astype(np.uint8), mode="RGBA").save(
        pfad, optimize=True)
    return pfad.replace(os.sep, "/")


def schummerung(dem, gueltig, dateiname):
    """Schraeglichtschattierung - macht jede Mulde sichtbar."""
    gy, gx = np.gradient(dem.astype(np.float32))
    azimut = math.radians(315.0)
    hoehenwinkel = math.radians(45.0)

    neigung = np.arctan(np.sqrt(gx ** 2 + gy ** 2))
    richtung = np.arctan2(-gx, gy)

    helligkeit = (math.sin(hoehenwinkel) * np.cos(neigung)
                  + math.cos(hoehenwinkel) * np.sin(neigung)
                  * np.cos(azimut - richtung))
    helligkeit = np.clip(helligkeit, 0, 1)

    grau = (helligkeit * 255).astype(np.uint8)
    alpha = np.where(gueltig, 150, 0).astype(np.uint8)
    bild = np.dstack([grau, grau, grau, alpha])

    os.makedirs(BILDORDNER, exist_ok=True)
    pfad = os.path.join(BILDORDNER, dateiname)
    Image.fromarray(bild, mode="RGBA").save(pfad, optimize=True)
    return pfad.replace(os.sep, "/")


def main():
    if not os.path.isdir(DGM_ORDNER):
        print(f"Ordner {DGM_ORDNER}/ fehlt.")
        print("Dort die DGM1-Kacheln ablegen, dann nochmal starten.")
        return

    print(f"Lese Kacheln aus {DGM_ORDNER}/ ...")
    dem, rahmen = lade_kacheln()
    if dem is None:
        print("Keine brauchbare Kachel gefunden.")
        return

    ost_min, nord_min, ost_max, nord_max = rahmen
    print(f"\nGesamtgitter: {dem.shape[1]} x {dem.shape[0]} m")

    dem = dem[::SPARSAM, ::SPARSAM]
    gueltig = dem > LEERWERT + 1
    if not gueltig.any():
        print("Nur Leerwerte.")
        return

    hoehen = dem[gueltig]
    print(f"Hoehe {round(float(hoehen.min()), 1)} bis "
          f"{round(float(hoehen.max()), 1)} m NHN, "
          f"Spanne {round(float(hoehen.max() - hoehen.min()), 1)} m")

    # --- Senkentiefe ---
    radius = max(1, int(UMGEBUNG_M / SPARSAM))
    umgebung, hat = kastenmittel(dem, gueltig, radius)
    tiefe = np.where(gueltig & hat, umgebung - dem, 0.0)
    tiefe = np.clip(tiefe, 0, None)

    # --- Hangneigung in Grad ---
    # Luecken mit dem Umgebungsmittel fuellen. Sonst erzeugt jeder
    # Datenrand einen scheinbaren Steilhang.
    geglaettet = np.where(gueltig, dem, umgebung).astype(np.float32)
    gy, gx = np.gradient(geglaettet, float(SPARSAM))
    neigung = np.degrees(np.arctan(np.sqrt(gx ** 2 + gy ** 2)))
    neigung = np.clip(neigung, 0, 60)

    # --- Nordexposition: 1 = Norden, 0 = Sueden ---
    richtung = np.arctan2(gx, gy)
    nordanteil = (np.cos(richtung) + 1) / 2

    # --- Feuchteindex ---
    t_teil = np.clip(tiefe / 3.0, 0, 1)                    # 3 m = voll
    n_teil = np.clip(1 - neigung / 12.0, 0, 1)             # ab 12 Grad null
    nord_teil = np.where(neigung > 2, nordanteil, 0.5)

    feuchte = 0.60 * t_teil + 0.28 * n_teil + 0.12 * nord_teil
    feuchte = np.where(gueltig, feuchte, 0.0)

    print(f"\nSenkentiefe: Median "
          f"{round(float(np.median(tiefe[gueltig])), 2)} m, "
          f"tiefste Stelle {round(float(tiefe[gueltig].max()), 1)} m")
    print(f"Hangneigung: Median "
          f"{round(float(np.median(neigung[gueltig])), 1)} Grad, "
          f"steilste {round(float(neigung[gueltig].max()), 1)} Grad")

    for grenze in (0.5, 0.6, 0.7):
        anteil = float((feuchte[gueltig] >= grenze).mean()) * 100
        print(f"Feuchteindex ueber {grenze}: {round(anteil, 1)} % der Flaeche")

    skala = [(0.0, (250, 250, 235)), (0.45, (200, 220, 180)),
             (0.65, (120, 180, 170)), (0.82, (50, 130, 165)),
             (1.0, (20, 60, 120))]
    p1 = faerbe(feuchte, gueltig, skala, "relief_feuchte.png")
    p2 = schummerung(geglaettet, gueltig, "relief_schummerung.png")

    sued, west = utm_zu_wgs84(ost_min, nord_min)
    nord, ost = utm_zu_wgs84(ost_max, nord_max)

    print(f"\n{p1}")
    print(f"{p2}")
    print(f"\nEckkoordinaten fuer die Karte:")
    print(f"  RELIEF_GRENZEN = [[{round(sued, 6)}, {round(west, 6)}], "
          f"[{round(nord, 6)}, {round(ost, 6)}]]")

    with open("relief_grenzen.txt", "w", encoding="utf-8") as f:
        f.write(f"{sued},{west},{nord},{ost}\n")
    print("\nAuch in relief_grenzen.txt gespeichert - karte.py liest das.")


if __name__ == "__main__":
    main()
