"""
Holt fehlende Wettertage fuer alle Waldpunkte nach.

Zwei Anlaesse: neue Punkte, die noch gar keine Historie haben, oder
Luecken, weil ein taeglicher Lauf ausgefallen ist.

Holt mehrere Orte in einer Anfrage und den ganzen Zeitraum auf
einmal - sonst waeren es bei 700 Punkten und 90 Tagen zehntausende
Abrufe.

Der Zwischenstand wird laufend geschrieben. Ein Abbruch kostet
nichts, ein Neustart setzt fort.
"""
import requests
import csv
import os
import sys
import time
import threading
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

import historie

PUNKTE_DATEI = "waldpunkte.csv"
SPALTEN = historie.SPALTEN

TAGE = 95

# Wie viele Orte je Anfrage. Bei langen Zeitraeumen kleiner als beim
# taeglichen Sammeln - sonst wird die Antwort zu gross.
BUENDEL = 12
ARBEITER = 3
PAUSE = 0.3

FELDER = [
    "precipitation_sum",
    "temperature_2m_mean",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_temperature_7_to_28cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "et0_fao_evapotranspiration",
]

ARCHIV = "https://archive-api.open-meteo.com/v1/archive"
VORHERSAGE = "https://api.open-meteo.com/v1/forecast"

bremse = threading.Event()


def lade_punkte():
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        return [(z["id"], float(z["lat"]), float(z["lon"]))
                for z in csv.DictReader(f)]


# Das Archiv hinkt einige Tage hinterher. Fuer alles Aeltere ist es
# die richtige Quelle, fuer die juengsten Tage der Vorhersagedienst -
# der liefert dort gemessene Werte. Ein Zeitraum, der beide Bereiche
# umfasst, muss deshalb in zwei Anfragen zerlegt werden.
ARCHIV_VERZUG = 6


def hole_zeitraum(orte, start, ende, dienst):
    """Eine Anfrage an einen Dienst. None bei Misserfolg."""
    parameter = {
        "latitude": ",".join(str(o[1]) for o in orte),
        "longitude": ",".join(str(o[2]) for o in orte),
        "start_date": str(start), "end_date": str(ende),
        "daily": ",".join(FELDER),
        "timezone": "Europe/Berlin",
    }

    for versuch in range(5):
        while bremse.is_set():
            time.sleep(2)
        try:
            antwort = requests.get(dienst, params=parameter, timeout=180)
        except Exception:
            time.sleep(4 * (versuch + 1))
            continue

        if antwort.status_code == 429:
            # Gedrosselt - alle Arbeiter anhalten, dann weiter
            if not bremse.is_set():
                bremse.set()
                print("    gedrosselt, warte 60 s", flush=True)
                time.sleep(60)
                bremse.clear()
            continue

        if antwort.status_code != 200:
            time.sleep(4 * (versuch + 1))
            continue

        try:
            daten = antwort.json()
        except Exception:
            time.sleep(3)
            continue

        if isinstance(daten, dict):
            daten = [daten]
        if not isinstance(daten, list) or len(daten) != len(orte):
            return None

        return [d.get("daily") if isinstance(d, dict) else None
                for d in daten]

    return None


def verbinde(a, b):
    """Zwei daily-Bloecke desselben Ortes aneinanderhaengen."""
    if a is None:
        return b
    if b is None:
        return a
    zusammen = {}
    for feld in set(a) | set(b):
        zusammen[feld] = (a.get(feld) or []) + (b.get(feld) or [])
    return zusammen


def hole_buendel(orte, start, ende):
    """
    Mehrere Orte, ganzer Zeitraum.

    Zerlegt den Zeitraum an der Archivgrenze und setzt die beiden
    Antworten wieder zusammen.
    """
    grenze = date.today() - timedelta(days=ARCHIV_VERZUG)

    if ende < grenze:
        return hole_zeitraum(orte, start, ende, ARCHIV)
    if start >= grenze:
        return hole_zeitraum(orte, start, ende, VORHERSAGE)

    # Beide Bereiche betroffen
    alt_teil = hole_zeitraum(orte, start, grenze - timedelta(days=1),
                             ARCHIV)
    if alt_teil is None:
        return None
    neu_teil = hole_zeitraum(orte, grenze, ende, VORHERSAGE)
    if neu_teil is None:
        # Lieber die alten Tage als gar nichts - der Rest kommt beim
        # naechsten Lauf
        return alt_teil

    return [verbinde(a, b) for a, b in zip(alt_teil, neu_teil)]


def leer(wert):
    return "" if wert is None else wert


def zeilen_aus(ort, lat, lon, d, vorhanden):
    """Aus einem daily-Block die noch fehlenden Tage machen."""
    if not d or "time" not in d:
        return []

    n = len(d["time"])

    def spalte(feld):
        return d.get(feld) or [None] * n

    regen = spalte("precipitation_sum")
    temp = spalte("temperature_2m_mean")
    bt07 = spalte("soil_temperature_0_to_7cm_mean")
    bf07 = spalte("soil_moisture_0_to_7cm_mean")
    bt728 = spalte("soil_temperature_7_to_28cm_mean")
    bf728 = spalte("soil_moisture_7_to_28cm_mean")
    et0 = spalte("et0_fao_evapotranspiration")

    neu = []
    for i, tag in enumerate(d["time"]):
        if (tag, ort) in vorhanden:
            continue
        if regen[i] is None or temp[i] is None:
            continue
        neu.append({
            "datum": tag, "ort": ort, "lat": lat, "lon": lon,
            "regen_icon": regen[i], "regen_era5": "",
            "temperatur": temp[i],
            "bt07": leer(bt07[i]), "bf07": leer(bf07[i]),
            "bt728": leer(bt728[i]), "bf728": leer(bf728[i]),
            "et0": leer(et0[i]), "quelle": "nachgefuellt",
        })
    return neu


def main():
    ende = date.today() - timedelta(days=1)
    start = ende - timedelta(days=TAGE - 1)

    orte = lade_punkte()
    print(f"{len(orte)} Punkte, Zeitraum {start} bis {ende}", flush=True)

    print("Lese vorhandene Historie ...", flush=True)
    vorhanden = historie.vorhandene(start)
    print(f"{len(vorhanden)} Eintraege schon da\n", flush=True)

    # Wie viele Tage fehlen je Ort? Wer vollstaendig ist, faellt weg.
    tage_gesamt = (ende - start).days + 1
    offen = []
    for ort, lat, lon in orte:
        fehlt = sum(1 for i in range(tage_gesamt)
                    if ((start + timedelta(days=i)).isoformat(), ort)
                    not in vorhanden)
        if fehlt:
            offen.append((ort, lat, lon, fehlt))

    if not offen:
        print("Keine Luecken.")
        return

    luecken = sum(x[3] for x in offen)
    print(f"{len(offen)} Punkte mit Luecken, {luecken} fehlende Tage")

    pakete = [offen[i:i + BUENDEL] for i in range(0, len(offen), BUENDEL)]
    print(f"{len(pakete)} Anfragen a {BUENDEL} Orte, geschaetzt "
          f"{len(pakete)*3/ARBEITER/60:.0f} Minuten\n", flush=True)

    sperre = threading.Lock()
    beginn = time.time()
    erledigt = [0]
    geschrieben = [0]
    fehler = [0]

    def arbeite(paket):
        orte_kurz = [(o, la, lo) for o, la, lo, _ in paket]
        ergebnis = hole_buendel(orte_kurz, start, ende)
        time.sleep(PAUSE)

        with sperre:
            erledigt[0] += 1
            if ergebnis is None:
                fehler[0] += len(paket)
            else:
                neue = []
                for (ort, lat, lon, _), d in zip(paket, ergebnis):
                    neue.extend(zeilen_aus(ort, lat, lon, d, vorhanden))
                if neue:
                    # Sofort schreiben - ein Abbruch kostet dann nur
                    # das laufende Paket
                    historie.anhaengen(neue)
                    geschrieben[0] += len(neue)

            if erledigt[0] % 5 == 0 or erledigt[0] == len(pakete):
                dauer = time.time() - beginn
                rest = (len(pakete) - erledigt[0]) / max(
                    erledigt[0] / max(dauer, 0.1), 0.01) / 60
                print(f"  {erledigt[0]} von {len(pakete)} Anfragen, "
                      f"{geschrieben[0]} Tage geschrieben, "
                      f"noch ~{rest:.0f} min, {fehler[0]} Fehler",
                      flush=True)

    with ThreadPoolExecutor(max_workers=ARBEITER) as pool:
        list(pool.map(arbeite, pakete))

    dauer = time.time() - beginn
    print(f"\n{geschrieben[0]} Tage in {dauer/60:.0f} Minuten.",
          flush=True)

    if fehler[0]:
        print(f"{fehler[0]} Punkte ohne Daten - nochmal starten, "
              f"es wird fortgesetzt.")

    von, bis = historie.spanne()
    print(f"Historie umfasst jetzt {von} bis {bis}.")
    print("\nWeiter mit:")
    print("  python baumarten.py")
    print("  python bodendaten.py")
    print("  python hoehen.py")
    print("  python ortsnamen.py")


main()