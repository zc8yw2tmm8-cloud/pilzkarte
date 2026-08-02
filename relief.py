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
import csv
import math
import re
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

DGM_ORDNER = "dgm"
BILDORDNER = "bilder"
GRENZEN_DATEI = "relief_grenzen.csv"

# Umgebungsradius fuer die Senkentiefe, in Metern.
# 150 m fasst eine Talmulde, 30 m nur einen Graben.
UMGEBUNG_M = 150

# Nur Waldflaechen einfaerben. Ohne das laufen die Farben ueber
# Aecker, Ortschaften und den Mittellandkanal - und behaupten dort
# feuchte Senken, wo keine Pilze wachsen.
NUR_WALD = True

# Umkreis um einen Waldpunkt, der als Wald gilt (in Metern).
# Die Waldpunkte stehen im 2-km-Raster, deshalb grosszuegig.
WALD_UMKREIS_M = 1400

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


def lade_kacheln(ordner=DGM_ORDNER):
    pfade = sorted(glob.glob(os.path.join(ordner, "*.tif"))
                   + glob.glob(os.path.join(ordner, "*.tiff")))
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


def lade_waldpunkte():
    """Waldpunkte als UTM-Koordinaten, fuer die Maske."""
    import csv as _csv
    punkte = []
    quelle = ("baumarten.csv" if os.path.exists("baumarten.csv")
              else "waldpunkte.csv" if os.path.exists("waldpunkte.csv")
              else None)
    if quelle is None:
        return []

    with open(quelle, "r", encoding="utf-8") as f:
        for z in _csv.DictReader(f):
            if quelle == "baumarten.csv":
                try:
                    if float(z.get("waldanteil") or 0) < 0.05:
                        continue
                except ValueError:
                    continue
            punkte.append(wgs84_zu_utm(float(z["lat"]), float(z["lon"])))
    return punkte


def wgs84_zu_utm(lat, lon):
    e, n = 600000.0, 5800000.0
    for _ in range(40):
        b, l = utm_zu_wgs84(e, n)
        n += (lat - b) * 111000
        e += (lon - l) * 111000 * math.cos(math.radians(lat))
    return e, n


def waldmaske(form, rahmen, waldpunkte, schritt):
    """
    True, wo Wald ist. Ein Kreis je Waldpunkt, gerastert.
    """
    if not NUR_WALD or not waldpunkte:
        return np.ones(form, dtype=bool)

    hoehe, breite = form
    ost_min, nord_min, ost_max, nord_max = rahmen
    maske = np.zeros(form, dtype=bool)
    radius = int(WALD_UMKREIS_M / schritt)

    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    kreis = (x * x + y * y) <= radius * radius

    for e, n in waldpunkte:
        if not (ost_min - WALD_UMKREIS_M <= e <= ost_max + WALD_UMKREIS_M):
            continue
        if not (nord_min - WALD_UMKREIS_M <= n <= nord_max + WALD_UMKREIS_M):
            continue

        px = int((e - ost_min) / schritt)
        py = int((nord_max - n) / schritt)

        y0, y1 = max(0, py - radius), min(hoehe, py + radius + 1)
        x0, x1 = max(0, px - radius), min(breite, px + radius + 1)
        if y0 >= y1 or x0 >= x1:
            continue

        ky0 = y0 - (py - radius)
        kx0 = x0 - (px - radius)
        maske[y0:y1, x0:x1] |= kreis[ky0:ky0 + (y1 - y0),
                                     kx0:kx0 + (x1 - x0)]

    return maske


def ein_gebiet(schluessel, ordner, titel, waldpunkte=None):
    """Rechnet ein Gebiet durch. Rueckgabe: Zeile fuer die Grenzendatei."""
    print(f"\n=== {titel} ===")
    dem, rahmen = lade_kacheln(ordner)
    if dem is None:
        print("  keine brauchbare Kachel")
        return None

    ost_min, nord_min, ost_max, nord_max = rahmen
    print(f"  Gitter {dem.shape[1]} x {dem.shape[0]} m")

    dem = dem[::SPARSAM, ::SPARSAM]
    gueltig = dem > LEERWERT + 1
    if not gueltig.any():
        print("  nur Leerwerte")
        return None

    hoehen = dem[gueltig]
    print(f"  Hoehe {round(float(hoehen.min()), 1)} bis "
          f"{round(float(hoehen.max()), 1)} m, Spanne "
          f"{round(float(hoehen.max() - hoehen.min()), 1)} m")

    radius = max(1, int(UMGEBUNG_M / SPARSAM))
    umgebung, hat = kastenmittel(dem, gueltig, radius)
    tiefe = np.clip(np.where(gueltig & hat, umgebung - dem, 0.0), 0, None)

    geglaettet = np.where(gueltig, dem, umgebung).astype(np.float32)
    gy, gx = np.gradient(geglaettet, float(SPARSAM))
    neigung = np.clip(np.degrees(np.arctan(np.sqrt(gx ** 2 + gy ** 2))), 0, 60)
    richtung = np.arctan2(gx, gy)
    nordanteil = (np.cos(richtung) + 1) / 2

    t_teil = np.clip(tiefe / 3.0, 0, 1)
    n_teil = np.clip(1 - neigung / 12.0, 0, 1)
    nord_teil = np.where(neigung > 2, nordanteil, 0.5)
    feuchte = np.where(gueltig,
                       0.60 * t_teil + 0.28 * n_teil + 0.12 * nord_teil, 0.0)

    # Nur ueber Wald einfaerben
    maske = waldmaske(dem.shape, rahmen, waldpunkte or [],
                      float(SPARSAM))
    gueltig = gueltig & maske
    feuchte = np.where(gueltig, feuchte, 0.0)
    anteil_wald = float(maske.mean()) * 100
    print(f"  Waldanteil im Ausschnitt: {anteil_wald:.0f} %")

    print(f"  Senkentiefe Median "
          f"{round(float(np.median(tiefe[gueltig])), 2)} m, tiefste "
          f"{round(float(tiefe[gueltig].max()), 1)} m")
    for grenze in (0.6, 0.7):
        anteil = float((feuchte[gueltig] >= grenze).mean()) * 100
        print(f"  Feuchteindex ueber {grenze}: {round(anteil, 1)} %")

    skala = [(0.0, (250, 250, 235)), (0.45, (200, 220, 180)),
             (0.65, (120, 180, 170)), (0.82, (50, 130, 165)),
             (1.0, (20, 60, 120))]
    faerbe(feuchte, gueltig, skala, f"relief_{schluessel}_feuchte.png")
    schummerung(geglaettet, gueltig, f"relief_{schluessel}_schummerung.png")

    sued, west = utm_zu_wgs84(ost_min, nord_min)
    nord, ost = utm_zu_wgs84(ost_max, nord_max)
    return {"gebiet": schluessel, "titel": titel,
            "sued": round(sued, 6), "west": round(west, 6),
            "nord": round(nord, 6), "ost": round(ost, 6)}


def main():
    if not os.path.isdir(DGM_ORDNER):
        print(f"Ordner {DGM_ORDNER}/ fehlt.")
        return

    try:
        import gebiete
        bekannt = gebiete.aktive()
    except ImportError:
        bekannt = {}

    # Unterordner je Gebiet, oder flache Kacheln als ein Gebiet
    unterordner = [d for d in sorted(os.listdir(DGM_ORDNER))
                   if os.path.isdir(os.path.join(DGM_ORDNER, d))]
    if unterordner:
        aufgaben = [(d, os.path.join(DGM_ORDNER, d),
                     bekannt.get(d, {}).get("name", d)) for d in unterordner]
    else:
        aufgaben = [("gebiet", DGM_ORDNER, "Gelaende")]

    waldpunkte = lade_waldpunkte()
    if NUR_WALD:
        print(f"{len(waldpunkte)} Waldpunkte fuer die Maske"
              if waldpunkte else
              "Keine Waldpunkte gefunden - es wird alles eingefaerbt")

    zeilen = []
    for schluessel, ordner, titel in aufgaben:
        ergebnis = ein_gebiet(schluessel, ordner, titel, waldpunkte)
        if ergebnis:
            zeilen.append(ergebnis)

    if not zeilen:
        print("\nNichts erzeugt.")
        return

    with open(GRENZEN_DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["gebiet", "titel", "sued",
                                              "west", "nord", "ost"])
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\n{len(zeilen)} Gebiete in {GRENZEN_DATEI}.")
    print("Weiter mit: python karte.py")


if __name__ == "__main__":
    main()
