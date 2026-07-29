"""
Wetterhistorie in Monatsdateien.

Warum nicht eine grosse Datei: Sie waechst um rund 1.000 Zeilen am
Tag. Wird sie taeglich ins Repository eingecheckt, speichert Git jedes
Mal eine vollstaendige Kopie - nach einem Jahr sind das mehrere
Gigabyte Versionsgeschichte fuer 40 MB Nutzdaten.

Mit Monatsdateien waechst nur die des laufenden Monats. Alte Monate
bleiben unveraendert und belasten die Versionsgeschichte nicht mehr.

Aufbau:
    wetter_historie/2026-06.csv
    wetter_historie/2026-07.csv
    wetter_historie/2026-08.csv
"""
import os
import csv
from datetime import date

ORDNER = "wetter_historie"
ALT = "wetter_historie.csv"      # alte Einzeldatei, nur zum Umziehen

SPALTEN = ["datum", "ort", "lat", "lon", "regen_icon", "regen_era5",
           "temperatur", "bt07", "bf07", "bt728", "bf728", "et0", "quelle"]


def monatsdatei(datum):
    """datum als date oder als Text 'JJJJ-MM-TT'."""
    text = datum if isinstance(datum, str) else datum.isoformat()
    return os.path.join(ORDNER, f"{text[:7]}.csv")


def dateien(ab_datum=None):
    """Alle Monatsdateien, optional erst ab einem Datum."""
    if not os.path.isdir(ORDNER):
        return []
    namen = sorted(d for d in os.listdir(ORDNER) if d.endswith(".csv"))
    if ab_datum is not None:
        grenze = (ab_datum if isinstance(ab_datum, str)
                  else ab_datum.isoformat())[:7]
        namen = [d for d in namen if d[:7] >= grenze]
    return [os.path.join(ORDNER, d) for d in namen]


def lese(ab_datum=None):
    """Liest alle Zeilen. Mit ab_datum werden alte Monate uebersprungen."""
    for pfad in dateien(ab_datum):
        with open(pfad, "r", encoding="utf-8") as f:
            for zeile in csv.DictReader(f):
                yield zeile


def vorhandene(ab_datum=None):
    """Menge der schon gespeicherten (datum, ort)-Paare."""
    return {(z["datum"], z["ort"]) for z in lese(ab_datum)}


def anhaengen(zeilen):
    """Neue Zeilen in die jeweilige Monatsdatei schreiben."""
    if not zeilen:
        return 0

    os.makedirs(ORDNER, exist_ok=True)
    nach_monat = {}
    for z in zeilen:
        nach_monat.setdefault(monatsdatei(z["datum"]), []).append(z)

    geschrieben = 0
    for pfad, teil in nach_monat.items():
        neu = not os.path.exists(pfad)
        with open(pfad, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SPALTEN)
            if neu:
                writer.writeheader()
            writer.writerows(teil)
        geschrieben += len(teil)

    return geschrieben


def spanne():
    """Erstes und letztes Datum in der Historie."""
    tage = [z["datum"] for z in lese()]
    if not tage:
        return None, None
    return min(tage), max(tage)


def umziehen():
    """Einmalig: alte Einzeldatei in Monatsdateien aufteilen."""
    if not os.path.exists(ALT):
        return 0, "keine alte Datei vorhanden"

    with open(ALT, "r", encoding="utf-8") as f:
        leser = csv.DictReader(f)
        fehlend = [s for s in SPALTEN if s not in (leser.fieldnames or [])]
        if fehlend:
            return 0, f"Spalten fehlen: {', '.join(fehlend)}"
        zeilen = [dict(z) for z in leser]

    if not zeilen:
        return 0, "alte Datei ist leer"

    schon_da = vorhandene()
    neu = [z for z in zeilen if (z["datum"], z["ort"]) not in schon_da]
    anhaengen(neu)
    return len(neu), f"{len(zeilen) - len(neu)} waren schon vorhanden"
