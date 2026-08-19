"""
Haelt fest, mit welchen Daten und Einstellungen kalibriert wurde.

Ohne das laesst sich eine Kalibrierung nicht reproduzieren: Man
sieht die Zahlen in arten.py, weiss aber nicht, aus wie vielen
Funden sie stammen, wann die von GBIF geholt wurden und welche
Einstellungen dabei galten.

Wird von kalibrieren.py und baumarten_kalibrieren.py aufgerufen.
Ergebnis: kalibrierung_protokoll.md - eine Zeile je Lauf, sodass
sich Aenderungen nachvollziehen lassen.
"""
import os
import csv
import json
import hashlib
from datetime import datetime

DATEI = "kalibrierung_protokoll.md"


def dateistand(pfad):
    """Zeilenzahl, Aenderungsdatum und Pruefsumme einer Datei."""
    if not os.path.exists(pfad):
        return None
    groesse = os.path.getsize(pfad)
    zeit = datetime.fromtimestamp(os.path.getmtime(pfad))

    with open(pfad, "rb") as f:
        pruefsumme = hashlib.md5(f.read()).hexdigest()[:8]

    zeilen = None
    if pfad.endswith(".csv"):
        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            zeilen = sum(1 for _ in f) - 1

    return {"zeilen": zeilen, "kb": round(groesse / 1024),
            "geaendert": zeit.strftime("%Y-%m-%d %H:%M"),
            "pruefsumme": pruefsumme}


def notiere(was, quellen, einstellungen, ergebnis):
    """
    Einen Lauf festhalten.

    was:           "Wetterbaender", "Baumarten", ...
    quellen:       Liste von Dateinamen
    einstellungen: Wichtige Parameter als Wörterbuch
    ergebnis:      Kurzfassung, etwa Zahl verwendeter Funde
    """
    jetzt = datetime.now().strftime("%Y-%m-%d %H:%M")

    zeilen = [f"\n## {was} — {jetzt}\n"]

    zeilen.append("**Datenquellen**\n")
    zeilen.append("| Datei | Zeilen | geändert | Prüfsumme |")
    zeilen.append("|---|---|---|---|")
    for q in quellen:
        d = dateistand(q)
        if d is None:
            zeilen.append(f"| `{q}` | fehlt | | |")
        else:
            zeilen.append(
                f"| `{q}` | {d['zeilen'] if d['zeilen'] is not None else '—'} "
                f"| {d['geaendert']} | `{d['pruefsumme']}` |")

    zeilen.append("\n**Einstellungen**\n")
    for k, v in sorted(einstellungen.items()):
        zeilen.append(f"- `{k}` = {v}")

    zeilen.append("\n**Ergebnis**\n")
    for k, v in ergebnis.items():
        zeilen.append(f"- {k}: {v}")

    neu = not os.path.exists(DATEI)
    with open(DATEI, "a", encoding="utf-8") as f:
        if neu:
            f.write("# Protokoll der Kalibrierungen\n\n"
                    "Automatisch geschrieben von `protokoll.py`. "
                    "Neueste Einträge unten.\n"
                    "\nDamit lässt sich nachvollziehen, aus welchen "
                    "Daten die Zahlen in `arten.py` stammen.\n")
        f.write("\n".join(zeilen) + "\n")

    print(f"\nIn {DATEI} festgehalten.")
