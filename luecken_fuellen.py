"""
Findet leere Felder im Gitter und ergaenzt sie.

Anders als waldraster_ergaenzen.py rechnet dieses Skript mit
demselben Gitter wie die Karte - Ursprung und Schrittweite aus
daten_export.gitter_angaben(). Deshalb findet es genau die Felder,
die auf der Karte als Loch erscheinen.

Der neue Punkt wird in die Feldmitte gesetzt, nicht irgendwohin.

Danach brauchen die neuen Punkte ihre Daten.
"""
import os
import csv
import math
import shutil

DATEI = "waldpunkte.csv"
KOPIE = "waldpunkte_vor_luecken.csv"

SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
RASTER_KM = 2.0

# Die Karte rechnet mit den Werten aus web/daten.json. Damit hier
# dieselben Felder herauskommen, werden sie von dort gelesen - sonst
# fuellt dieses Skript andere Loecher, als man auf der Karte sieht.
DATEN = os.path.join("web", "daten.json")


def gitter():
    if os.path.exists(DATEN):
        import json
        with open(DATEN, "r", encoding="utf-8") as f:
            g = json.load(f).get("gitter")
        if g:
            print("Gitter aus web/daten.json - dieselben Felder wie "
                  "auf der Karte\n")
            return g["schritt_lat"], g["schritt_lon"]

    print("web/daten.json fehlt - Gitter selbst gerechnet.\n"
          "Besser erst daten_export.py laufen lassen.\n")
    schritt_lat = RASTER_KM / 111.0
    mitte = (SUED + NORD) / 2
    schritt_lon = RASTER_KM / (111.0 * math.cos(math.radians(mitte)))
    return schritt_lat, schritt_lon


def hoechste_nummer(punkte):
    hoechste = -1
    for p in punkte:
        ziffern = "".join(c for c in p["id"] if c.isdigit())
        if ziffern:
            hoechste = max(hoechste, int(ziffern))
    return hoechste


def main():
    schritt_lat, schritt_lon = gitter()

    with open(DATEI, "r", encoding="utf-8") as f:
        punkte = [dict(z) for z in csv.DictReader(f)]

    # Felder so bestimmen, wie es die Karte tut
    belegt = {}
    for p in punkte:
        zeile = math.floor((float(p["lat"]) - SUED) / schritt_lat)
        spalte = math.floor((float(p["lon"]) - WEST) / schritt_lon)
        belegt.setdefault((zeile, spalte), []).append(p["id"])

    # Gegenprobe: Welche Punkte stehen ueberhaupt in daten.json? Ein
    # Punkt ohne Kennwerte wird dort weggelassen und erscheint auf der
    # Karte als Loch, obwohl er in waldpunkte.csv steht.
    if os.path.exists(DATEN):
        import json
        with open(DATEN, "r", encoding="utf-8") as f:
            drin = {z["id"] for z in json.load(f)["zellen"]}
        fehlend = [p["id"] for p in punkte if p["id"] not in drin]
        if fehlend:
            print(f"ACHTUNG: {len(fehlend)} Punkte stehen in "
                  f"{DATEI}, aber nicht in daten.json.")
            print("Ihnen fehlen Kennwerte - sie erscheinen als Loch.")
            print(f"Beispiele: {', '.join(fehlend[:6])}")
            print("Behebung: python nachfuellen.py\n")

    zeilen = [f[0] for f in belegt]
    spalten = [f[1] for f in belegt]
    z0, z1 = min(zeilen), max(zeilen)
    s0, s1 = min(spalten), max(spalten)

    leer = [(z, s) for z in range(z0, z1 + 1)
            for s in range(s0, s1 + 1) if (z, s) not in belegt]

    mehrfach = sum(1 for v in belegt.values() if len(v) > 1)

    print(f"{len(punkte)} Punkte in {len(belegt)} Feldern")
    print(f"Rechteck: {z1-z0+1} x {s1-s0+1} = "
          f"{(z1-z0+1)*(s1-s0+1)} Felder")
    print(f"{len(leer)} leer, {mehrfach} mit mehreren Punkten\n")

    if not leer:
        print("Keine Luecken.")
        return

    print("Die neuen Punkte kommen in die Feldmitte:")
    for z, s in leer[:6]:
        lat = SUED + (z + 0.5) * schritt_lat
        lon = WEST + (s + 0.5) * schritt_lon
        print(f"   {lat:.5f}, {lon:.5f}")
    if len(leer) > 6:
        print(f"   ... und {len(leer) - 6} weitere")

    print()
    if input(f"{len(leer)} Punkte ergaenzen? (j/n) "
             ).strip().lower()[:1] != "j":
        print("Abgebrochen.")
        return

    naechste = hoechste_nummer(punkte) + 1
    shutil.copy(DATEI, KOPIE)

    with open(DATEI, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for z, s in leer:
            lat = round(SUED + (z + 0.5) * schritt_lat, 5)
            lon = round(WEST + (s + 0.5) * schritt_lon, 5)
            writer.writerow([f"W{naechste:04d}", lat, lon])
            naechste += 1

    print(f"\n{len(leer)} Punkte ergaenzt, jetzt "
          f"{len(punkte) + len(leer)} insgesamt.")
    print(f"Kopie in {KOPIE}.")
    print("\nWeiter mit:")
    print("  python nachfuellen.py")
    print("  python baumarten.py")
    print("  python bodendaten.py    (Fundorte-Frage mit n)")
    print("  python hoehen.py")
    print("  python ortsnamen.py")
    print("  python karte.py")
    print("  python daten_export.py")
    print("  python web_bilder.py")


main()