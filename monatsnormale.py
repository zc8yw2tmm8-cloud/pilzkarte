"""
Erzeugt die Monatsnormale der Wetterpunkte fuer arten.py.

Warum: Die Wetterpunkte sind im Herbst systematisch hoeher, weil der
Boden dann feuchter und kuehler ist. Der Saisonfaktor sagt das aber
schon - er wurde aus Fundmeldungen je Aufwand und Monat gerechnet und
enthaelt den Wettereffekt des Monats bereits.

Multipliziert man beides, zaehlt der Herbst zweimal. Gemessen hat das
bei vier Arten den Hoehepunkt um einen Monat nach hinten verschoben.

Dieses Skript rechnet aus dem Hintergrund, wie hoch die Wetterpunkte
in jedem Monat normalerweise liegen. In score() wird daran geteilt,
sodass das Wetter nur noch die Abweichung vom gewoehnlichen Tag
desselben Monats ausdrueckt.

Neu laufen lassen, wenn sich die Wetterbaender in arten.py aendern.
Gibt die Tabelle zum Einsetzen aus.
"""
import os
import csv
import time
from datetime import date
from collections import defaultdict

import arten
from kennwerte import berechne, zahl

QUELLE = "hintergrund.csv"
AUSGABE = "monatsnormale.txt"

# Jeden n-ten Tag auswerten - 31.000 Tage sind mehr als genug
SCHRITT = 3

# Vergleichsbedingungen: Bestand und Boden spielen keine Rolle,
# weil nur die Wetterpunkte gebraucht werden
BODEN = {"ph": 5.4, "clay": 19.0}
BESTAND = {"anteile": {"kiefer": 0.5, "eiche": 0.3, "buche": 0.2},
           "waldanteil": 0.5}


def lade():
    punkte = defaultdict(list)
    with open(QUELLE, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte[z["ort"]].append({
                "tag": date.fromisoformat(z["datum"]),
                "regen": zahl(z.get("regen")),
                "temp": zahl(z.get("temp")),
                "bt07": zahl(z.get("bt07")),
                "bf07": zahl(z.get("bf07")),
                "bt728": zahl(z.get("bt728")),
                "bf728": zahl(z.get("bf728")),
                "et0": zahl(z.get("et0")),
            })
    for o in punkte:
        punkte[o].sort(key=lambda r: r["tag"])
    return punkte


def main():
    if not os.path.exists(QUELLE):
        print(f"{QUELLE} fehlt. Erst hintergrund.py laufen lassen.")
        return

    print(f"Lese {QUELLE} ...", flush=True)
    punkte = lade()

    # Kennwerte je Stichtag
    tage = []
    for r in punkte.values():
        for i in range(62, len(r), SCHRITT):
            t = r[i]["tag"]
            k = berechne(r[i - 62:i + 1], t)
            if k:
                tage.append((t, k))

    print(f"{len(tage)} Vergleichstage\n", flush=True)

    # WICHTIG: ohne Monatsausgleich rechnen, sonst waere es zirkulaer
    vorher = arten.MONATSAUSGLEICH
    arten.MONATSAUSGLEICH = False

    ergebnis = {}
    monatsnamen = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

    print(f"{'Art':<32}" + "".join(f"{m:>6}" for m in monatsnamen))

    for art, e in arten.ARTEN.items():
        nach_monat = defaultdict(list)
        for t, k in tage:
            r = arten.score(k, art, t, "misch", BODEN, BESTAND)
            nach_monat[t.month].append(r[1])

        mittel = {m: sum(v) / len(v) for m, v in nach_monat.items()}
        jahr = sum(mittel.values()) / len(mittel)
        faktoren = {m: round(mittel[m] / jahr, 3) for m in sorted(mittel)}
        ergebnis[art] = faktoren

        print(f"{e['name']:<32}"
              + "".join(f"{faktoren.get(m, 1.0):>6.2f}"
                        for m in range(1, 13)))

    arten.MONATSAUSGLEICH = vorher

    zeilen = ["MONATSNORMALE = {"]
    for art in sorted(ergebnis):
        f = ergebnis[art]
        eintraege = ", ".join(f"{m}: {f[m]}" for m in sorted(f))
        zeilen.append(f'    "{art}": {{{eintraege}}},')
    zeilen.append("}")

    with open(AUSGABE, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")

    print(f"\nZum Einsetzen in arten.py: {AUSGABE}")
    print("Der Block MONATSNORMALE dort ersetzen.")


if __name__ == "__main__":
    main()
