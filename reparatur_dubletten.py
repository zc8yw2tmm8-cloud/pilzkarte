"""
Entfernt doppelte Zeilen aus der Wetterhistorie.

Nach einem Verschmelzungskonflikt stehen zwei Fassungen desselben
Zeitraums hintereinander in der Datei - jeder Tag ist dann doppelt
erfasst.

Massgeblich ist das Paar (datum, ort). Bei Dubletten bleibt die
Zeile mit den meisten ausgefuellten Feldern; bei Gleichstand die
erste.

Legt vorher Kopien an.
"""
import os
import csv
import glob
import shutil

ORDNER = "wetter_historie"


def guete(zeile):
    """Wie vollstaendig ist eine Zeile?"""
    return sum(1 for wert in zeile.values()
               if wert not in (None, "", "nan"))


def main():
    if not os.path.isdir(ORDNER):
        print(f"{ORDNER}/ fehlt.")
        return

    dateien = sorted(glob.glob(os.path.join(ORDNER, "*.csv")))
    print(f"{len(dateien)} Monatsdateien\n")

    gesamt_weg = 0
    betroffen = []

    for pfad in dateien:
        with open(pfad, "r", encoding="utf-8") as f:
            leser = csv.DictReader(f)
            spalten = leser.fieldnames
            zeilen = [dict(z) for z in leser]

        beste = {}
        reihenfolge = []
        for z in zeilen:
            schluessel = (z.get("datum"), z.get("ort"))
            if schluessel not in beste:
                beste[schluessel] = z
                reihenfolge.append(schluessel)
            elif guete(z) > guete(beste[schluessel]):
                beste[schluessel] = z

        weg = len(zeilen) - len(beste)
        if weg:
            betroffen.append((pfad, spalten, reihenfolge, beste,
                              len(zeilen)))
            gesamt_weg += weg
            print(f"{os.path.basename(pfad)}: {len(zeilen)} Zeilen, "
                  f"{weg} doppelt")

    if not gesamt_weg:
        print("Keine Dubletten gefunden.")
        return

    print(f"\n{gesamt_weg} doppelte Zeilen insgesamt.")
    if input("Entfernen? (j/n) ").strip().lower()[:1] != "j":
        print("Abgebrochen.")
        return

    for pfad, spalten, reihenfolge, beste, vorher in betroffen:
        shutil.copy(pfad, pfad + ".vor_dublettenpruefung")
        with open(pfad, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=spalten)
            writer.writeheader()
            for s in reihenfolge:
                writer.writerow(beste[s])
        print(f"  {os.path.basename(pfad)}: {vorher} -> {len(beste)}")

    print("\nFertig. Weiter mit:")
    print("  python karte.py")
    print("  python daten_export.py")
    print("  python web_bilder.py")


main()