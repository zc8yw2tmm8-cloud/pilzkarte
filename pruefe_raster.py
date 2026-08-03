"""
Prueft, ob alle Waldpunkte auf demselben Gitter liegen.

Verdacht: Die urspruenglichen 1046 Punkte stammen aus waldraster.py,
die 695 neuen aus waldraster_ergaenzen.py. Wenn beide Skripte das
Gitter minimal anders berechnet haben, liegen zwei gegeneinander
versetzte Gitter vor - und die Rechtecke auf der Karte ueberlappen
sich.
"""
import csv
import math
from collections import Counter

DATEI = "waldpunkte.csv"
RASTER_KM = 2.0


def main():
    with open(DATEI, "r", encoding="utf-8") as f:
        punkte = [(z["id"], float(z["lat"]), float(z["lon"]))
                  for z in csv.DictReader(f)]

    print(f"{len(punkte)} Punkte\n")

    lats = sorted({round(p[1], 5) for p in punkte})
    lons = sorted({round(p[2], 5) for p in punkte})

    print(f"{len(lats)} verschiedene Breitengrade")
    print(f"{len(lons)} verschiedene Laengengrade")

    schritt_lat = RASTER_KM / 111.0
    mitte = (min(lats) + max(lats)) / 2
    schritt_lon = RASTER_KM / (111.0 * math.cos(math.radians(mitte)))

    print(f"\nErwarteter Schritt: {schritt_lat:.5f} Breite, "
          f"{schritt_lon:.5f} Laenge")

    # Wie viele verschiedene Reste bleiben beim Teilen durch den
    # Schritt? Auf einem sauberen Gitter waere es genau einer.
    def reste(werte, schritt):
        r = Counter(round((w / schritt) % 1, 3) for w in werte)
        return r

    r_lat = reste(lats, schritt_lat)
    r_lon = reste(lons, schritt_lon)

    print(f"\nBreite: {len(r_lat)} verschiedene Gitterlagen")
    for wert, n in r_lat.most_common(5):
        versatz_m = wert * schritt_lat * 111000
        print(f"   Rest {wert:.3f} -> {n} Werte, "
              f"Versatz {versatz_m:.0f} m")

    print(f"\nLaenge: {len(r_lon)} verschiedene Gitterlagen")
    for wert, n in r_lon.most_common(5):
        versatz_m = wert * schritt_lon * 111000 * math.cos(
            math.radians(mitte))
        print(f"   Rest {wert:.3f} -> {n} Werte, "
              f"Versatz {versatz_m:.0f} m")

    # Kleinster Abstand zwischen zwei Punkten
    nach_lat = {}
    for _, la, lo in punkte:
        nach_lat.setdefault(round(la, 5), []).append(lo)

    abstaende = []
    for la, liste in nach_lat.items():
        liste = sorted(liste)
        for a, b in zip(liste, liste[1:]):
            abstaende.append(b - a)

    if abstaende:
        abstaende.sort()
        km = 111.0 * math.cos(math.radians(mitte))
        print(f"\nAbstaende in Ost-West-Richtung:")
        print(f"   kleinster: {abstaende[0]*km*1000:.0f} m")
        print(f"   Median:    {abstaende[len(abstaende)//2]*km*1000:.0f} m")
        print(f"   erwartet:  {RASTER_KM*1000:.0f} m")

    if len(r_lat) > 2 or len(r_lon) > 2:
        print("\n=== BEFUND ===")
        print("Die Punkte liegen NICHT auf einem einheitlichen Gitter.")
        print("Deshalb ueberlappen sich die Rechtecke auf der Karte.")
        print("Behebung: python raster_ausrichten.py")
    else:
        print("\nGitter sieht einheitlich aus.")


main()
