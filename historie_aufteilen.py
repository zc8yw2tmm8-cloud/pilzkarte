"""
Teilt wetter_historie.csv einmalig in Monatsdateien auf.

Vor dem ersten Lauf in der Cloud noetig. Die alte Datei bleibt
liegen und kann nach der Kontrolle geloescht werden.
"""
import os
import historie


def main():
    print("Teile die Wetterhistorie in Monatsdateien auf\n")

    if os.path.exists(historie.ALT):
        gross = os.path.getsize(historie.ALT) / 1024 / 1024
        print(f"Alte Datei: {historie.ALT} ({gross:.1f} MB)")
    else:
        print(f"{historie.ALT} nicht gefunden.")

    anzahl, hinweis = historie.umziehen()
    print(f"\n{anzahl} Zeilen uebernommen ({hinweis})\n")

    dateien = historie.dateien()
    if not dateien:
        print("Keine Monatsdateien entstanden.")
        return

    print(f"{len(dateien)} Monatsdateien:")
    gesamt = 0
    for pfad in dateien:
        zeilen = sum(1 for _ in open(pfad, encoding="utf-8")) - 1
        gesamt += zeilen
        print(f"  {os.path.basename(pfad):<14}{zeilen:>8} Zeilen"
              f"{os.path.getsize(pfad)/1024/1024:>8.1f} MB")

    von, bis = historie.spanne()
    print(f"\n{gesamt} Zeilen, {von} bis {bis}")
    print(f"\nKontrolliere die Zahlen. Stimmen sie, kann "
          f"{historie.ALT} geloescht werden.")
    print("Danach laufen sammeln.py, nachfuellen.py und karte.py")
    print("automatisch mit den Monatsdateien.")


main()
