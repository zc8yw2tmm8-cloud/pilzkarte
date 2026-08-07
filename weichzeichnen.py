"""
Erzeugt aus den Zellwerten ein weich verlaufendes Bild statt harter Quadrate.
 
Verfahren: Ueber das Gebiet wird ein feines Raster gelegt (etwa 250 m).
Jeder Rasterpunkt bekommt einen gewichteten Mittelwert der umliegenden
Zellen - nahe Zellen zaehlen stark, ferne kaum. Das ergibt einen weichen
Verlauf ohne Kanten.
 
Wichtig: Ausserhalb der Waldzellen wird das Bild durchsichtig, damit
keine Farbe ueber Aecker und Ortschaften laeuft.
 
Braucht numpy und pillow:  pip install numpy pillow
"""
import os
import math
import numpy as np
from PIL import Image, ImageFilter
 
import farben
 
# Rasterweite des Bildes in Kilometern. Kleiner = weicher, aber groessere
# Datei. 0.25 ist ein guter Kompromiss.
BILD_KM = 0.25
 
# Wie weit eine Zelle ausstrahlt. Bei 2 km Zellabstand sorgen 1.3 km
# fuer sanfte Uebergaenge ohne Verwaschen.
# Wie weit eine Zelle in ihre Umgebung ausstrahlt.
#
# Muss zum Punktabstand passen. Bei 2 km Raster reichen 0,9 km nicht
# von Reihe zu Reihe - dazwischen bleiben dunkle Streifen. Etwa
# zwei Drittel des Abstands ist die Untergrenze, mehr schadet nicht.
STREUUNG_KM = 1.6
 
# Ab welcher Entfernung zur naechsten Zelle das Bild durchsichtig wird
VOLL_KM = 1.8
AUS_KM = 3.3
 
ORDNER = "bilder"
BILDORDNER = ORDNER
 
 
def _farbtabelle(dunkel):
    """256 Farbstufen vorberechnen - viel schneller als pro Pixel."""
    tabelle = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        tabelle[i] = farben.rgb(i / 255.0 * 100.0, dunkel)
    return tabelle
 
 
TABELLEN = {}
 
 
def farbtabelle(dunkel):
    if dunkel not in TABELLEN:
        TABELLEN[dunkel] = _farbtabelle(dunkel)
    return TABELLEN[dunkel]
 
 
_GEOMETRIE = {}
 
 
def erzeuge(werte, dateiname, rand_km=3.0, dunkel=False):
    """
    werte: Liste von (lat, lon, score)
    Rueckgabe: (pfad, bounds) fuer folium.raster_layers.ImageOverlay
               oder (None, None) bei zu wenig Daten
    """
    if len(werte) < 3:
        return None, None
 
    os.makedirs(BILDORDNER, exist_ok=True)
 
    lats = np.array([w[0] for w in werte], dtype=np.float64)
    lons = np.array([w[1] for w in werte], dtype=np.float64)
    scores = np.array([w[2] for w in werte], dtype=np.float64)
 
    mitte_lat = float(lats.mean())
    km_pro_grad_lat = 111.0
    km_pro_grad_lon = 111.0 * math.cos(math.radians(mitte_lat))
 
    rand_lat = rand_km / km_pro_grad_lat
    rand_lon = rand_km / km_pro_grad_lon
 
    sued = lats.min() - rand_lat
    nord = lats.max() + rand_lat
    west = lons.min() - rand_lon
    ost = lons.max() + rand_lon
 
    schritt_lat = BILD_KM / km_pro_grad_lat
    schritt_lon = BILD_KM / km_pro_grad_lon
 
    hoehe = int((nord - sued) / schritt_lat) + 1
    breite = int((ost - west) / schritt_lon) + 1
 
    # Sicherheitsgrenze gegen versehentlich riesige Bilder
    if hoehe * breite > 12_000_000:
        return None, None
 
    # Die Punktlage aendert sich zwischen den Bildern nie - Gewichte,
    # Naehe und Fensterlagen also nur einmal rechnen und merken.
    schluessel = (round(sued, 5), round(west, 5), hoehe, breite, len(werte))
 
    if schluessel not in _GEOMETRIE:
        gewicht = np.zeros((hoehe, breite), dtype=np.float32)
        naehe = np.zeros((hoehe, breite), dtype=np.float32)
 
        sigma_px = STREUUNG_KM / BILD_KM
        fenster = int(math.ceil(3.0 * sigma_px))
 
        dy = np.arange(-fenster, fenster + 1).reshape(-1, 1)
        dx = np.arange(-fenster, fenster + 1).reshape(1, -1)
        kern = np.exp(-((dy / sigma_px) ** 2
                        + (dx / sigma_px) ** 2)).astype(np.float32)
 
        abstand_km = np.sqrt((dy * BILD_KM) ** 2 + (dx * BILD_KM) ** 2)
        naehe_kern = np.clip((AUS_KM - abstand_km) / (AUS_KM - VOLL_KM),
                             0.0, 1.0).astype(np.float32)
 
        fenster_lage = []
        for lat, lon in zip(lats, lons):
            zy = int(round((lat - sued) / schritt_lat))
            zx = int(round((lon - west) / schritt_lon))
            y0, y1 = max(0, zy - fenster), min(hoehe, zy + fenster + 1)
            x0, x1 = max(0, zx - fenster), min(breite, zx + fenster + 1)
            if y0 >= y1 or x0 >= x1:
                fenster_lage.append(None)
                continue
            ky0 = y0 - (zy - fenster)
            kx0 = x0 - (zx - fenster)
            teil = kern[ky0:ky0 + (y1 - y0), kx0:kx0 + (x1 - x0)]
            fenster_lage.append((y0, y1, x0, x1, teil))
 
            gewicht[y0:y1, x0:x1] += teil
            np.maximum(naehe[y0:y1, x0:x1],
                       naehe_kern[ky0:ky0 + (y1 - y0), kx0:kx0 + (x1 - x0)],
                       out=naehe[y0:y1, x0:x1])
 
        _GEOMETRIE[schluessel] = (fenster_lage, gewicht, naehe)
 
    fenster_lage, gewicht, naehe = _GEOMETRIE[schluessel]
 
    summe = np.zeros((hoehe, breite), dtype=np.float32)
    for lage, s in zip(fenster_lage, scores):
        if lage is None:
            continue
        y0, y1, x0, x1, teil = lage
        summe[y0:y1, x0:x1] += teil * np.float32(s)
 
    hat_daten = gewicht > 1e-6
    mittel = np.zeros_like(summe)
    mittel[hat_daten] = summe[hat_daten] / gewicht[hat_daten]
 
    # Bild aufbauen. Zeile 0 ist im Bild oben, also Norden -> umdrehen.
    stufen = np.clip(mittel / 100.0 * 255.0, 0, 255).astype(np.uint8)
    rgb = farbtabelle(dunkel)[stufen]
    deckkraft = farben.thema(dunkel)["kachel_deckkraft"]
    alpha = (np.clip(naehe, 0, 1) * deckkraft).astype(np.uint8)
 
    bild = np.dstack([rgb, alpha[:, :, None]])
    bild = np.flipud(bild)
 
    ergebnis = Image.fromarray(bild, mode="RGBA")
    # Letzter Schliff: nimmt die Restkanten der Alpha-Maske
    ergebnis = ergebnis.filter(ImageFilter.GaussianBlur(radius=1.2))
 
    pfad = os.path.join(BILDORDNER, dateiname)
    ergebnis.save(pfad, compress_level=6)
 
    grenzen = [[float(sued), float(west)], [float(nord), float(ost)]]
    return pfad.replace(os.sep, "/"), grenzen