"""
Bringt die Wetterhistorie mit dem Raster in Einklang.

Was repariert wird: Zeilen, deren Kennung nicht zu ihrer Koordinate
passt. Sie stammen aus der Rastererweiterung, bei der ein Block von
Kennungen zweimal vergeben wurde - pruefe_orte.py zeigt den Versatz
in fuenf zusammenhaengenden Bloecken.

Wichtig: Die Messwerte sind nicht falsch. Sie wurden fuer die
Koordinate geholt, die in der Zeile steht - nur unter der falschen
Kennung abgelegt. Deshalb wird auch nichts weggeworfen:

  - Steht fuer den richtigen Punkt an diesem Tag schon eine Zeile,
    ist unsere eine Dublette und faellt weg.
  - Sonst bekommt sie die richtige Kennung. Die Koordinaten bleiben
    wie sie sind, denn sie beschreiben, wo wirklich gemessen wurde.

Die umgekehrte Richtung waere falsch: Die Koordinaten auf die
gewuenschte Position zu setzen wuerde Messwerte umetikettieren.

Boden und Hoehen fasst dieses Skript nicht an. Seit ortsbezug.py
erkennen bodendaten.py und hoehen.py falsch verortete Zeilen selbst
als offen und holen sie neu - mitsamt den Werten, die dabei fehlen.

Aufruf:
    python ortsreparatur.py                 nur zeigen, nichts tun
    python ortsreparatur.py --ausfuehren    wirklich aendern
"""
import os
import csv
import sys
import glob

import ortsbezug

PROGNOSE = "wetter_prognose.csv"
ENDUNG = ".vor_ortsreparatur"


def dateien():
    """Monatsdateien und die Vorhersage. Sicherungen bleiben aussen vor."""
    liste = sorted(glob.glob(os.path.join("wetter_historie", "*.csv")))
    if os.path.exists(PROGNOSE):
        liste.append(PROGNOSE)
    return liste


def ziel_von(lat, lon, punkte):
    """Welche Kennung liegt an dieser Koordinate?

    None, wenn keine oder mehrere passen. Mehrere kommen vor: Im
    Raster gibt es doppelt belegte Positionen, und Naehe allein ist
    dann keine Zuordnung.
    """
    treffer = [k for k, p in punkte.items()
               if ortsbezug.abstand(lat, lon, p[0], p[1])
               <= ortsbezug.TOLERANZ_M]
    return treffer[0] if len(treffer) == 1 else None


def plane(pfad, punkte):
    """Sagt fuer eine Datei, was zu tun waere. Aendert nichts.

    Liefert (spalten, neue_zeilen, bericht).
    """
    with open(pfad, "r", encoding="utf-8") as f:
        leser = csv.DictReader(f)
        spalten = leser.fieldnames
        zeilen = list(leser)

    # Welche (Datum, Kennung) gibt es schon? Bestimmt, ob eine
    # umbenannte Zeile eine Dublette waere.
    belegt = {(z["datum"], z["ort"]) for z in zeilen}

    neu = []
    bericht = {"geprueft": len(zeilen), "entfernt": 0,
               "umbenannt": 0, "unklar": 0}

    for z in zeilen:
        kennung = z["ort"]
        if kennung not in punkte or not z.get("lat") or not z.get("lon"):
            neu.append(z)
            continue
        if ortsbezug.am_ort(z, *punkte[kennung]):
            neu.append(z)
            continue

        ziel = ziel_von(float(z["lat"]), float(z["lon"]), punkte)
        if ziel is None:
            # Nicht raten. Solche Zeilen bleiben stehen und werden
            # gemeldet - lieber sichtbar unklar als still verbogen.
            bericht["unklar"] += 1
            neu.append(z)
            continue

        if (z["datum"], ziel) in belegt:
            bericht["entfernt"] += 1
            continue

        z["ort"] = ziel
        belegt.add((z["datum"], ziel))
        bericht["umbenannt"] += 1
        neu.append(z)

    return spalten, neu, bericht


def schreibe(pfad, spalten, zeilen):
    """Sicherung anlegen, dann unteilbar ersetzen."""
    sicherung = pfad + ENDUNG
    if not os.path.exists(sicherung):
        with open(pfad, "rb") as q, open(sicherung, "wb") as z:
            z.write(q.read())

    vorlaeufig = pfad + ".neu"
    with open(vorlaeufig, "w", newline="", encoding="utf-8") as f:
        schreiber = csv.DictWriter(f, fieldnames=spalten)
        schreiber.writeheader()
        schreiber.writerows(zeilen)
    os.replace(vorlaeufig, pfad)


def main():
    echt = "--ausfuehren" in sys.argv

    punkte = ortsbezug.lade_punkte()
    if punkte is None:
        print("waldpunkte.csv fehlt - im Projektordner ausfuehren.")
        return

    print("Ortsreparatur der Wetterdaten"
          f" - {'ECHTER LAUF' if echt else 'nur Probelauf'}\n")
    print(f"{'Datei':<34}{'Zeilen':>9}{'entfernt':>10}"
          f"{'umbenannt':>11}{'unklar':>8}")
    print("-" * 72)

    summe = {"entfernt": 0, "umbenannt": 0, "unklar": 0}
    zu_schreiben = []

    for pfad in dateien():
        spalten, neu, b = plane(pfad, punkte)
        for k in summe:
            summe[k] += b[k]
        print(f"{pfad.replace(os.sep, '/'):<34}{b['geprueft']:>9}"
              f"{b['entfernt']:>10}{b['umbenannt']:>11}{b['unklar']:>8}")
        if b["entfernt"] or b["umbenannt"]:
            zu_schreiben.append((pfad, spalten, neu))

    print("-" * 72)
    print(f"{'zusammen':<34}{'':>9}{summe['entfernt']:>10}"
          f"{summe['umbenannt']:>11}{summe['unklar']:>8}\n")

    if summe["unklar"]:
        print(f"{summe['unklar']} Zeilen ohne eindeutiges Ziel bleiben "
              f"unangetastet.\nSie stehen einzeln in ortspruefung.csv.\n")

    if not zu_schreiben:
        print("Nichts zu tun.")
        return

    if not echt:
        print("Das war ein Probelauf - keine Datei wurde angefasst.")
        print("Wenn das so stimmt:  python ortsreparatur.py --ausfuehren")
        return

    for pfad, spalten, neu in zu_schreiben:
        schreibe(pfad, spalten, neu)
        print(f"  {pfad.replace(os.sep, '/')} geschrieben, "
              f"Sicherung unter {os.path.basename(pfad)}{ENDUNG}")

    print("\nFertig. Zur Kontrolle:  python pruefe_orte.py")
    print("Es sollten null falsch verortete Zeilen uebrig sein.")


main()
