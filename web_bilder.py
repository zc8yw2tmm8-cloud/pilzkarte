"""
Erzeugt die weichgezeichneten Kartenbilder fuer die Website.

Genau dasselbe Verfahren wie in der oertlichen Karte: ueber das Gebiet
wird ein feines Raster gelegt, jeder Bildpunkt bekommt einen
gewichteten Mittelwert der umliegenden Zellen. Nahe Zellen zaehlen
stark, ferne kaum - das ergibt einen durchgehenden Verlauf ohne
sichtbare Mittelpunkte.

Im Browser laesst sich das nicht nachbauen: Uebereinandergelegte
halbdurchsichtige Flaechen addieren sich auf, statt sich zu mitteln -
in der Zellmitte stapeln sich dann zwei Dutzend Schichten.

Ergebnis: web/karten/<art>_t<tag>.png und web/karten.json
Laeuft im taeglichen Bauvorgang mit, nichts davon wird eingecheckt.
"""
import os
import json
from datetime import date, timedelta

import weichzeichnen
import arten as artenmodul

QUELLE = os.path.join("web", "daten.json")
ORDNER = os.path.join("web", "karten")
INDEX = os.path.join("web", "karten.json")

DUNKEL = True


def main():
    if not os.path.exists(QUELLE):
        print(f"{QUELLE} fehlt. Erst daten_export.py laufen lassen.")
        return

    with open(QUELLE, "r", encoding="utf-8") as f:
        daten = json.load(f)

    zellen = daten["zellen"]
    tage = daten["tage"]
    arten = daten["arten"]

    os.makedirs(ORDNER, exist_ok=True)
    # Alte Bilder weg - sonst bleiben Reste von gestern liegen
    for d in os.listdir(ORDNER):
        if d.endswith(".png"):
            os.remove(os.path.join(ORDNER, d))

    # Der Zeichner legt seine Bilder in einen eigenen Ordner
    weichzeichnen.BILDORDNER = ORDNER

    eintraege = {}
    grenzen = None
    gesamt = 0

    print(f"{len(zellen)} Zellen, {len(arten)} Arten, {len(tage)} Tage\n")

    for art in arten:
        for i, tag in enumerate(tage):
            werte = [(z["lat"], z["lon"], z["scores"][art][i])
                     for z in zellen
                     if z["scores"][art][i] is not None]
            if len(werte) < 3:
                continue

            dateiname = f"{art}_t{i}.png"
            pfad, rahmen = weichzeichnen.erzeuge(werte, dateiname,
                                                 dunkel=DUNKEL)
            if not pfad:
                continue

            grenzen = rahmen
            eintraege.setdefault(art, {})[str(i)] = f"karten/{dateiname}"
            gesamt += os.path.getsize(pfad)

        print(f"  {arten[art]['name']:<18}{len(tage)} Bilder")

    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump({"grenzen": grenzen, "bilder": eintraege},
                  f, ensure_ascii=False)

    anzahl = sum(len(v) for v in eintraege.values())
    print(f"\n{anzahl} Bilder, zusammen {gesamt/1024/1024:.1f} MB")
    print(f"Je Ansicht laedt der Browser eines, etwa "
          f"{gesamt/anzahl/1024:.0f} KB")


main()
