import requests
import csv
import time

# Bounding Box der Region: Sued, West, Nord, Ost
# deckt Braunschweig / Wolfsburg / Elm / Gifhorn / suedliche Heide ab
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15

RASTER_KM = 2.0
DATEI = "waldpunkte.csv"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

# Overpass-Abfrage: alle Waldflaechen in der Box
QUERY = f"""
[out:json][timeout:180];
(
  way["landuse"="forest"]({SUED},{WEST},{NORD},{OST});
  way["natural"="wood"]({SUED},{WEST},{NORD},{OST});
  relation["landuse"="forest"]({SUED},{WEST},{NORD},{OST});
  relation["natural"="wood"]({SUED},{WEST},{NORD},{OST});
);
out geom;
"""


SERVER = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


SERVER = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}


def hole_waldflaechen():
    """Fragt Waldpolygone von der Overpass-API ab, mit Wiederholung."""
    daten = None

    for versuch in range(1, 4):
        for url in SERVER:
            print(f"Versuch {versuch} bei {url.split('/')[2]} ...")
            try:
                antwort = requests.post(url, data={"data": QUERY},
                                        headers=HEADERS, timeout=300)
            except Exception as e:
                print("  Verbindungsfehler:", e)
                continue

            if antwort.status_code != 200:
                print(f"  HTTP {antwort.status_code}")
                print("  Antwort:", antwort.text[:200])
                continue

            try:
                daten = antwort.json()
                break
            except Exception:
                print("  Kein JSON. Serverantwort:")
                print("  ", antwort.text[:300])
                continue

        if daten is not None:
            break

        print("Warte 30 Sekunden ...\n")
        time.sleep(30)

    if daten is None:
        print("\nAlle Versuche fehlgeschlagen.")
        return []

    polygone = []
    for element in daten.get("elements", []):
        if element.get("type") == "way" and "geometry" in element:
            ring = [(p["lat"], p["lon"]) for p in element["geometry"]]
            if len(ring) >= 3:
                polygone.append(ring)
        elif element.get("type") == "relation":
            for member in element.get("members", []):
                if member.get("role") == "outer" and "geometry" in member:
                    ring = [(p["lat"], p["lon"]) for p in member["geometry"]]
                    if len(ring) >= 3:
                        polygone.append(ring)

    print(f"{len(polygone)} Waldflaechen gefunden.")
    return polygone


def punkt_in_polygon(lat, lon, ring):
    """Ray-Casting: liegt der Punkt innerhalb des Polygons?"""
    drin = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        lat_i, lon_i = ring[i]
        lat_j, lon_j = ring[j]
        if (lon_i > lon) != (lon_j > lon):
            schnitt = (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i
            if lat < schnitt:
                drin = not drin
        j = i
    return drin


def bounding_box(ring):
    """Schnelle Vorabpruefung: Umschliessendes Rechteck eines Polygons."""
    lats = [p[0] for p in ring]
    lons = [p[1] for p in ring]
    return min(lats), min(lons), max(lats), max(lons)


def main():
    polygone = hole_waldflaechen()
    if not polygone:
        print("Keine Daten erhalten. Spaeter nochmal versuchen.")
        return

    boxen = [bounding_box(r) for r in polygone]

    schritt_lat = RASTER_KM / 111.0
    schritt_lon = RASTER_KM / (111.0 * 0.61)

    # Halbe Zellgroesse - fuer die Eckpunkte
    h_lat = schritt_lat / 2
    h_lon = schritt_lon / 2

    punkte = []
    lat = SUED
    zeile = 0

    print("Erzeuge Rasterpunkte (5 Pruefpunkte je Zelle) ...")
    while lat <= NORD:
        lon = WEST
        while lon <= OST:
            # Mitte plus vier Ecken der Zelle
            pruefpunkte = [
                (lat, lon),
                (lat - h_lat * 0.8, lon - h_lon * 0.8),
                (lat - h_lat * 0.8, lon + h_lon * 0.8),
                (lat + h_lat * 0.8, lon - h_lon * 0.8),
                (lat + h_lat * 0.8, lon + h_lon * 0.8),
            ]

            treffer = False
            for p_lat, p_lon in pruefpunkte:
                for ring, (min_lat, min_lon, max_lat, max_lon) in zip(polygone, boxen):
                    if not (min_lat <= p_lat <= max_lat and min_lon <= p_lon <= max_lon):
                        continue
                    if punkt_in_polygon(p_lat, p_lon, ring):
                        treffer = True
                        break
                if treffer:
                    break

            if treffer:
                punkte.append((round(lat, 4), round(lon, 4)))

            lon += schritt_lon
        lat += schritt_lat
        zeile += 1
        if zeile % 10 == 0:
            print(f"  ... {len(punkte)} Punkte bisher")

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "lat", "lon"])
        for i, (la, lo) in enumerate(punkte, start=1):
            writer.writerow([f"W{i:04d}", la, lo])

    print(f"\nFertig. {len(punkte)} Waldpunkte in {DATEI} gespeichert.")


main()