"""
Zeigt, welche Werte in arten.py gemessen und welche geschaetzt sind.

Anlass: In arten.py stehen sieben GESCHAETZT-Markierungen, in
CLAUDE.md steht "alle Faktoren gemessen". Beides kann nicht stimmen -
und ohne Uebersicht weiss niemand, welchem Wert er trauen kann.

Prueft je Art und Faktor, ob es dazu gemessene Fundzahlen gibt.
"""
import os
import csv
from collections import Counter

import arten

FUNDE = "funde_wetter2.csv"
BODEN_FUNDE = "bodendaten_funde.csv"

# Ab wann ein Faktor als gemessen gilt
MINDEST_WETTER = 60
MINDEST_BAUM = 40
MINDEST_BODEN = 40


def fundzahlen():
    if not os.path.exists(FUNDE):
        return Counter()
    with open(FUNDE, "r", encoding="utf-8") as f:
        return Counter(z["art"] for z in csv.DictReader(f))


def main():
    zahlen = fundzahlen()

    print("Herkunft der Werte in arten.py\n")
    print("gemessen   = aus GBIF-Funden gerechnet")
    print("geschaetzt = aus der Literatur, nicht geprueft")
    print("neutral    = kein Faktor, weil zu wenige Daten\n")

    if not zahlen:
        print(f"ACHTUNG: {FUNDE} fehlt - ohne die Fundzahlen laesst")
        print("sich nicht sagen, was gemessen ist.")
        print("Erst funde_arten.py und funde_wetter2.py laufen lassen.\n")

    kopf = (f"{'Art':<32}{'Funde':>7}  {'Wetter':<11}{'Saison':<11}"
            f"{'Baeume':<11}{'Boden':<9}")
    print(kopf)
    print("-" * len(kopf))

    offen = []

    for art, e in arten.ARTEN.items():
        n = zahlen.get(art, 0)

        wetter = "gemessen" if n >= MINDEST_WETTER else "geschaetzt"
        saison = "gemessen" if n >= 40 else "geschaetzt"

        # Baumarten: gleichmaessige Werte deuten auf Schaetzung
        bm = e.get("baumarten") or {}
        werte = sorted(bm.values())
        baum = "geschaetzt"
        if n >= MINDEST_BAUM and werte:
            # Gemessene Gewichte haben krumme Zahlen, geschaetzte
            # meist runde wie 0.5, 1.0, 0.25
            krumm = sum(1 for v in werte
                        if round(v * 100) % 5 != 0)
            baum = "gemessen" if krumm >= 2 else "geschaetzt"

        # Boden: neutral, wenn nur ein Band ohne Grenzen
        ph = e.get("boden_ph") or []
        if len(ph) == 1 and ph[0][0] is None and ph[0][1] is None:
            boden = "neutral"
        elif n >= MINDEST_BODEN:
            boden = "gemessen"
        else:
            boden = "geschaetzt"

        print(f"{e['name']:<32}{n:>7}  {wetter:<11}{saison:<11}"
              f"{baum:<11}{boden:<9}")

        for feld, stand in (("Wetter", wetter), ("Saison", saison),
                            ("Baeume", baum), ("Boden", boden)):
            if stand == "geschaetzt":
                offen.append((e["name"], feld, n))

    print()
    if offen:
        print(f"{len(offen)} Faktoren beruhen auf Schaetzungen:\n")
        for name, feld, n in offen:
            fehlt = max(0, MINDEST_WETTER - n)
            hinweis = (f"braucht noch ~{fehlt} Funde"
                       if fehlt else "Werte pruefen")
            print(f"  {name:<32}{feld:<9}{hinweis}")
        print("\nDiese Werte stammen aus der Pilzliteratur. Bei den")
        print("ersten sieben Arten haben sich plausible Annahmen")
        print("zehnmal als falsch erwiesen - entsprechend vorsichtig")
        print("damit umgehen.")
    else:
        print("Alle Faktoren sind gemessen.")

    print(f"\nSchwellen: Wetter {MINDEST_WETTER}, "
          f"Baeume {MINDEST_BAUM}, Boden {MINDEST_BODEN} Funde")


main()
