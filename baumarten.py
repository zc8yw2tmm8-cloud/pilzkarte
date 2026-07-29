"""
Holt die Baumartenkarte des Thuenen-Instituts als Raster und wertet sie
lokal aus.

Quelle: Blickensdoerfer et al. 2024 - Sentinel-1/2 plus Bundeswaldinventur,
10 m Aufloesung, Referenzjahr 2017/2018.
Nutzung nach den Geodaten-Nutzungsbestimmungen des Bundes.

Statt tausender Einzelabfragen wird das Gebiet in wenigen Kacheln
heruntergeladen. Danach zaehlt das Skript fuer jede 2-km-Zelle ALLE
enthaltenen Bildpunkte aus - rund 40.000 statt neun.

Braucht numpy und pillow:  pip install numpy pillow truststore

Laeuft EINMAL. Ergebnis: baumarten.csv
Heruntergeladene Kacheln bleiben in kacheln/ liegen, ein Neustart
benutzt sie wieder.
"""
import requests
import csv
import os
import io
import math
from collections import Counter

import numpy as np
from PIL import Image

try:
    import truststore
    truststore.inject_into_ssl()
    ZERTIFIKATE = "Windows-Speicher (truststore)"
except ImportError:
    ZERTIFIKATE = "certifi (Standard)"

Image.MAX_IMAGE_PIXELS = None      # grosse Kacheln zulassen

BASIS = "https://atlas.thuenen.de/geoserver/ows"
EBENE = "geonode:Dominant_Species_Class"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

PUNKTE_DATEI = "waldpunkte.csv"
DATEI = "baumarten.csv"
KACHELORDNER = "kacheln"

# Gebiet - gleiche Grenzen wie waldraster.py
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15

RASTER_KM = 2.0
AUFLOESUNG_M = 10
KACHELN_X, KACHELN_Y = 4, 4       # 16 Kacheln, je etwa 4 MB

KLASSEN = {}


def legende_aus_datei():
    """Falls legende.py schon klassen.csv geschrieben hat."""
    if not os.path.exists("klassen.csv"):
        return {}
    klassen = {}
    with open("klassen.csv", "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                klassen[int(z["wert"])] = z["name"].strip()
            except (ValueError, KeyError):
                pass
    return klassen


def lade_klassen_datei():
    """klassen.csv, falls legende.py sie erzeugt hat."""
    if not os.path.exists("klassen.csv"):
        return {}
    klassen = {}
    with open("klassen.csv", "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                klassen[int(z["wert"])] = z["name"].strip()
            except (ValueError, KeyError):
                pass
    return klassen


def hole_legende():
    parameter = {"service": "WMS", "version": "1.1.1",
                 "request": "GetLegendGraphic", "layer": EBENE,
                 "format": "application/json"}
    try:
        daten = requests.get(BASIS, params=parameter, headers=HEADERS,
                             timeout=60).json()
    except Exception as e:
        print("  Legende nicht abrufbar:", str(e)[:120])
        return {}

    klassen = {}
    for legende in daten.get("Legend", []):
        for regel in legende.get("rules", []):
            name = regel.get("title") or regel.get("name") or ""
            filt = str(regel.get("filter", ""))
            zahlen = [t for t in filt.replace("[", " ").replace("]", " ")
                      .replace("=", " ").split() if t.isdigit()]
            if zahlen and name:
                klassen[int(zahlen[0])] = name
    return klassen


def hole_kachel(sued, west, nord, ost, breite, hoehe, pfad):
    """
    WCS GetCoverage. Probiert mehrere Fassungen durch, weil je nach
    Serverkonfiguration eine andere funktioniert.
    """
    if os.path.exists(pfad) and os.path.getsize(pfad) > 1000:
        return True, "aus Zwischenspeicher"

    versuche = [
        ("WCS 1.0.0", {
            "service": "WCS", "version": "1.0.0", "request": "GetCoverage",
            "coverage": EBENE, "crs": "EPSG:4326",
            "bbox": f"{west},{sued},{ost},{nord}",
            "format": "GeoTIFF", "width": breite, "height": hoehe,
        }),
        ("WCS 1.1.1", {
            "service": "WCS", "version": "1.1.1", "request": "GetCoverage",
            "identifier": EBENE,
            "BoundingBox": f"{west},{sued},{ost},{nord},urn:ogc:def:crs:EPSG::4326",
            "format": "image/tiff", "GridBaseCRS": "urn:ogc:def:crs:EPSG::4326",
        }),
        ("WMS GetMap", {
            "service": "WMS", "version": "1.1.1", "request": "GetMap",
            "layers": EBENE, "srs": "EPSG:4326",
            "bbox": f"{west},{sued},{ost},{nord}",
            "width": breite, "height": hoehe,
            "format": "image/geotiff",
        }),
    ]

    for name, parameter in versuche:
        try:
            antwort = requests.get(BASIS, params=parameter, headers=HEADERS,
                                   timeout=300)
        except Exception as e:
            continue

        typ = antwort.headers.get("Content-Type", "")
        if antwort.status_code != 200 or "xml" in typ:
            continue
        if len(antwort.content) < 1000:
            continue

        try:
            Image.open(io.BytesIO(antwort.content)).verify()
        except Exception:
            continue

        with open(pfad, "wb") as f:
            f.write(antwort.content)
        return True, name

    return False, "alle Fassungen fehlgeschlagen"


def lade_punkte():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))
    return punkte


def main():
    print(f"Zertifikatspruefung ueber: {ZERTIFIKATE}")
    if "certifi" in ZERTIFIKATE:
        print("Falls es scheitert:  pip install truststore")

    print("\nLese Legende ...")
    global KLASSEN
    KLASSEN = legende_aus_datei() or hole_legende()
    if KLASSEN:
        for wert in sorted(KLASSEN):
            print(f"   {wert:3d}  {KLASSEN[wert]}")
    else:
        print("   keine - Klassen bleiben Zahlen")

    os.makedirs(KACHELORDNER, exist_ok=True)

    km_lat = 111.0
    km_lon = 111.0 * math.cos(math.radians((SUED + NORD) / 2))

    print(f"\nLade {KACHELN_X * KACHELN_Y} Kacheln ...")
    kacheln = []

    for iy in range(KACHELN_Y):
        for ix in range(KACHELN_X):
            s = SUED + (NORD - SUED) * iy / KACHELN_Y
            n = SUED + (NORD - SUED) * (iy + 1) / KACHELN_Y
            w = WEST + (OST - WEST) * ix / KACHELN_X
            o = WEST + (OST - WEST) * (ix + 1) / KACHELN_X

            breite = int((o - w) * km_lon * 1000 / AUFLOESUNG_M)
            hoehe = int((n - s) * km_lat * 1000 / AUFLOESUNG_M)

            pfad = os.path.join(KACHELORDNER, f"k_{iy}_{ix}.tif")
            ok, wie = hole_kachel(s, w, n, o, breite, hoehe, pfad)

            if not ok:
                print(f"  Kachel {iy}/{ix}: {wie}")
                continue

            groesse = os.path.getsize(pfad) / 1024 / 1024
            print(f"  Kachel {iy}/{ix}: {breite}x{hoehe} px, "
                  f"{round(groesse, 1)} MB ({wie})")
            kacheln.append((s, w, n, o, breite, hoehe, pfad))

    if not kacheln:
        print("\nKeine Kachel geladen. Der Dienst bietet WCS offenbar nicht an.")
        print("Sag Bescheid - dann bauen wir auf Einzelabfragen zurueck.")
        return

    print(f"\n{len(kacheln)} Kacheln geladen. Werte Zellen aus ...")

    punkte = lade_punkte()
    d_lat = RASTER_KM / km_lat / 2
    d_lon = RASTER_KM / km_lon / 2

    ergebnisse = {}

    for s, w, n, o, breite, hoehe, pfad in kacheln:
        bild = np.array(Image.open(pfad))
        if bild.ndim == 3:
            bild = bild[:, :, 0]
        hoehe_px, breite_px = bild.shape

        for kennung, lat, lon in punkte:
            if not (s <= lat <= n and w <= lon <= o):
                continue

            # Zellgrenzen in Bildkoordinaten. Zeile 0 ist Norden.
            x0 = int((lon - d_lon - w) / (o - w) * breite_px)
            x1 = int((lon + d_lon - w) / (o - w) * breite_px)
            y0 = int((n - (lat + d_lat)) / (n - s) * hoehe_px)
            y1 = int((n - (lat - d_lat)) / (n - s) * hoehe_px)

            x0, x1 = max(0, x0), min(breite_px, x1)
            y0, y1 = max(0, y0), min(hoehe_px, y1)
            if x1 <= x0 or y1 <= y0:
                continue

            ausschnitt = bild[y0:y1, x0:x1].ravel()
            if ausschnitt.size == 0:
                continue

            werte, anzahl = np.unique(ausschnitt, return_counts=True)
            zaehler = Counter(dict(zip(werte.tolist(), anzahl.tolist())))

            # Zellen koennen auf zwei Kacheln liegen - zusammenzaehlen
            if kennung in ergebnisse:
                ergebnisse[kennung]["zaehler"] += zaehler
            else:
                ergebnisse[kennung] = {"lat": lat, "lon": lon,
                                       "zaehler": zaehler}

    zeilen = []
    for kennung, e in ergebnisse.items():
        z = e["zaehler"]
        gesamt = sum(z.values())
        ohne_null = Counter({k: v for k, v in z.items() if k != 0})
        wald = sum(ohne_null.values())

        if not ohne_null:
            zeilen.append({"id": kennung, "lat": e["lat"], "lon": e["lon"],
                           "haupt": "kein_wald", "haupt_anteil": 0.0,
                           "waldanteil": 0.0, "pixel": gesamt,
                           "verteilung": ""})
            continue

        haupt, n_haupt = ohne_null.most_common(1)[0]
        verteilung = ";".join(
            f"{KLASSEN.get(k, k)}:{round(v / wald, 3)}"
            for k, v in ohne_null.most_common(6) if v / wald >= 0.02)

        zeilen.append({
            "id": kennung, "lat": e["lat"], "lon": e["lon"],
            "haupt": KLASSEN.get(haupt, str(haupt)),
            "haupt_anteil": round(n_haupt / wald, 3),
            "waldanteil": round(wald / gesamt, 3),
            "pixel": gesamt,
            "verteilung": verteilung,
        })

    zeilen.sort(key=lambda z: z["id"])
    spalten = ["id", "lat", "lon", "haupt", "haupt_anteil", "waldanteil",
               "pixel", "verteilung"]
    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=spalten)
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\n{len(zeilen)} Zellen in {DATEI}.")
    if zeilen:
        print(f"Im Schnitt {round(sum(z['pixel'] for z in zeilen)/len(zeilen))}"
              f" Bildpunkte je Zelle.")

    print("\nHauptbaumart je Zelle:")
    for name, n in Counter(z["haupt"] for z in zeilen).most_common():
        print(f"  {n:5d}  {name}")

    hoch = [z for z in zeilen if z["waldanteil"] >= 0.5]
    print(f"\n{len(hoch)} Zellen mit ueber 50 % Waldanteil.")
    print(f"Kacheln liegen in {KACHELORDNER}/ - koennen nach dem Lauf")
    print("geloescht werden.")


main()
