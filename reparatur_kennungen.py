"""
Behebt doppelte Kennungen in waldpunkte.csv.

waldraster_ergaenzen.py hat neue Punkte mit W0000, W0001, ...
durchnummeriert und dabei bei der ZEILENZAHL weitergezaehlt. Wurden
vorher Punkte entfernt, sind die hoechsten Kennungen aber laengst
vergeben - die neuen Punkte bekamen dann Kennungen, die es schon gab.

Zwei Folgen:
  - Beim Einlesen ueberschreibt ein Punkt den anderen. Deshalb laedt
    karte.py weniger Punkte, als in der Datei stehen.
  - Der neue Punkt erbt die Wetterdaten des alten - also Werte von
    einer ganz anderen Stelle.

Dieses Skript vergibt frische Kennungen und meldet, welche Punkte
danach neue Wetterdaten brauchen.
"""
import os
import csv
import shutil
from collections import defaultdict

DATEI = "waldpunkte.csv"
KOPIE = "waldpunkte_vor_kennungen.csv"


def main():
    with open(DATEI, "r", encoding="utf-8") as f:
        zeilen = [dict(z) for z in csv.DictReader(f)]

    nach_id = defaultdict(list)
    for z in zeilen:
        nach_id[z["id"]].append(z)

    doppelt = {k: v for k, v in nach_id.items() if len(v) > 1}

    print(f"{len(zeilen)} Zeilen, {len(nach_id)} verschiedene Kennungen")
    print(f"{len(doppelt)} Kennungen mehrfach vergeben\n")

    if not doppelt:
        print("Alles eindeutig - nichts zu tun.")
        return

    for kennung, liste in sorted(doppelt.items())[:5]:
        orte = ", ".join(f"{z['lat']}/{z['lon']}" for z in liste)
        print(f"  {kennung}: {len(liste)}x  ({orte})")
    if len(doppelt) > 5:
        print(f"  ... und {len(doppelt) - 5} weitere")

    ueberzaehlig = sum(len(v) - 1 for v in doppelt.values())
    print(f"\n{ueberzaehlig} Punkte brauchen eine neue Kennung.")
    print("Sie bekommen danach keine Wetterdaten mehr aus Versehen")
    print("von einer anderen Stelle - dafuer muessen sie neu geholt")
    print("werden.")

    print()
    if input("Neu vergeben? (j/n) ").strip().lower()[:1] != "j":
        print("Abgebrochen.")
        return

    # Hoechste vorhandene Nummer finden
    hoechste = 0
    for k in nach_id:
        ziffern = "".join(c for c in k if c.isdigit())
        if ziffern:
            hoechste = max(hoechste, int(ziffern))

    naechste = hoechste + 1
    geaendert = []

    for kennung, liste in nach_id.items():
        if len(liste) == 1:
            continue
        # Der erste behaelt seine Kennung, die uebrigen bekommen neue
        for z in liste[1:]:
            alt = z["id"]
            z["id"] = f"W{naechste:04d}"
            geaendert.append((alt, z["id"], z["lat"], z["lon"]))
            naechste += 1

    shutil.copy(DATEI, KOPIE)

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "lat", "lon"])
        writer.writeheader()
        for z in zeilen:
            writer.writerow({k: z[k] for k in ("id", "lat", "lon")})

    print(f"\n{len(geaendert)} Kennungen neu vergeben.")
    print(f"Kopie in {KOPIE}.")
    print("\nDiese Punkte haben jetzt keine Daten mehr und muessen")
    print("neu beschafft werden:")
    print("\n  python nachfuellen.py")
    print("  python baumarten.py")
    print("  python bodendaten.py    (Fundorte-Frage mit n)")
    print("  python hoehen.py")
    print("  python ortsnamen.py")


main()
