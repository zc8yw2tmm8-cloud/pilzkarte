"""
Misst und behebt die Gitterverschiebung.

Die urspruenglichen Waldpunkte und die spaeter ergaenzten liegen auf
zwei Gittern, die um eine halbe Zelle gegeneinander versetzt sind.
Fuer die Darstellung ist das behoben, fuer die Daten nicht: Jeder
Punkt traegt Werte fuer eine 2-km-Zelle, und benachbarte Zellen
ueberlappen sich.

Dieses Skript rechnet zuerst nach, was eine Vereinheitlichung
kosten wuerde, und aendert nichts ohne Rueckfrage.

Der Ansatz: Alle Punkte auf ein gemeinsames Gitter beziehen. Wo
mehrere in dasselbe Feld fallen, bleibt einer - der mit den meisten
Wetterdaten, weil dessen Historie am laengsten ist.

Koordinaten werden NICHT verschoben. Baumarten und Bodenwerte
wurden am tatsaechlichen Ort erhoben; sie zu verschieben waere
schlimmer als die Ueberlappung.
"""
import os
import csv
import math
import shutil
from collections import defaultdict

import historie

DATEI = "waldpunkte.csv"
KOPIE = "waldpunkte_vorher.csv"

SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
RASTER_KM = 2.0


def gitterfeld(lat, lon, schritt_lat, schritt_lon):
    """In welches Feld des gemeinsamen Gitters faellt ein Punkt?"""
    return (int(math.floor((lat - SUED) / schritt_lat)),
            int(math.floor((lon - WEST) / schritt_lon)))


def historienlaenge():
    """Wie viele Tage hat jeder Punkt?"""
    zahl = defaultdict(int)
    for z in historie.lese():
        zahl[z["ort"]] += 1
    return zahl


def main():
    with open(DATEI, "r", encoding="utf-8") as f:
        punkte = [dict(z) for z in csv.DictReader(f)]

    schritt_lat = RASTER_KM / 111.0
    mitte = (SUED + NORD) / 2
    schritt_lon = RASTER_KM / (111.0 * math.cos(math.radians(mitte)))

    felder = defaultdict(list)
    for p in punkte:
        f = gitterfeld(float(p["lat"]), float(p["lon"]),
                       schritt_lat, schritt_lon)
        felder[f].append(p)

    mehrfach = {f: liste for f, liste in felder.items() if len(liste) > 1}
    ueberzaehlig = sum(len(v) - 1 for v in mehrfach.values())

    print(f"{len(punkte)} Punkte")
    print(f"{len(felder)} verschiedene Felder im 2-km-Gitter")
    print(f"{len(mehrfach)} Felder mit mehr als einem Punkt")
    print(f"{ueberzaehlig} Punkte waeren ueberzaehlig\n")

    verteilung = defaultdict(int)
    for liste in felder.values():
        verteilung[len(liste)] += 1
    for n in sorted(verteilung):
        print(f"   {verteilung[n]:>5} Felder mit {n} Punkt"
              f"{'en' if n > 1 else ''}")

    if not mehrfach:
        print("\nKeine Ueberschneidungen - nichts zu tun.")
        return

    print(f"\nEine Vereinheitlichung wuerde {ueberzaehlig} Punkte "
          f"entfernen.")
    print(f"Es blieben {len(felder)} Punkte auf einem sauberen Gitter.")
    print("\nWas dabei verloren geht:")
    print("  - die Wetterhistorie der entfernten Punkte")
    print("  - ihre Baumarten- und Bodenwerte")
    print("Was gewonnen wird:")
    print("  - keine ueberlappenden Zellen mehr")
    print("  - Kacheln in voller Groesse statt halber")
    print("\nDie entfernten Punkte decken dieselben Waldflaechen ab")
    print("wie die verbleibenden - es geht keine Flaeche verloren,")
    print("nur die doppelte Abtastung.")

    print()
    if input("Vereinheitlichen? (j/n) ").strip().lower()[:1] != "j":
        print("Abgebrochen, nichts geaendert.")
        return

    print("\nLese Historienlaenge ...")
    laenge = historienlaenge()

    behalten = []
    entfernt = []
    for f, liste in sorted(felder.items()):
        if len(liste) == 1:
            behalten.append(liste[0])
            continue
        # Den mit den meisten Wettertagen behalten; bei Gleichstand
        # den, der naeher an der Feldmitte liegt
        mitte_lat = SUED + (f[0] + 0.5) * schritt_lat
        mitte_lon = WEST + (f[1] + 0.5) * schritt_lon

        def guete(p):
            d = math.hypot(float(p["lat"]) - mitte_lat,
                           float(p["lon"]) - mitte_lon)
            return (-laenge.get(p["id"], 0), d)

        liste.sort(key=guete)
        behalten.append(liste[0])
        entfernt.extend(liste[1:])

    shutil.copy(DATEI, KOPIE)

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "lat", "lon"])
        writer.writeheader()
        for p in behalten:
            writer.writerow({k: p[k] for k in ("id", "lat", "lon")})

    print(f"\n{len(behalten)} Punkte in {DATEI}.")
    print(f"{len(entfernt)} entfernt. Kopie in {KOPIE}.")
    print("\nDie Daten der entfernten Punkte bleiben in den anderen")
    print("Dateien liegen - sie stoeren nicht, werden aber nicht mehr")
    print("gelesen.")
    print("\nWeiter mit:")
    print("  python karte.py")
    print("  python daten_export.py")
    print("  python web_bilder.py")


main()