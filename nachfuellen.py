"""
Fuellt die Historie rueckwirkend auf - jetzt 90 Tage,
damit die 60-Tage-Wasserbilanz sofort funktioniert.

Quelle: Archive-API (ERA5, ~11 km). Ein Aufruf pro Punkt.
"""
import requests
import csv
import os
import time
from datetime import date, timedelta

import historie

PUNKTE_DATEI = "waldpunkte.csv"
TAGE = 90

FELDER = [
    "precipitation_sum",
    "temperature_2m_mean",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_temperature_7_to_28cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "et0_fao_evapotranspiration",
]

SPALTEN = historie.SPALTEN


def lade_punkte():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))
    return punkte


def hole_zeitraum(lat, lon, start, ende):
    url = "https://archive-api.open-meteo.com/v1/archive"
    parameter = {
        "latitude": lat,
        "longitude": lon,
        "start_date": str(start),
        "end_date": str(ende),
        "daily": ",".join(FELDER),
        "timezone": "Europe/Berlin",
    }
    try:
        antwort = requests.get(url, params=parameter, timeout=60)
        daten = antwort.json()
    except Exception:
        return None
    if "daily" not in daten:
        return None
    return daten["daily"]


def leer(wert):
    return "" if wert is None else wert


def main():
    ende = date.today() - timedelta(days=1)
    start = ende - timedelta(days=TAGE - 1)

    orte = lade_punkte()
    vorhanden = historie.vorhandene(start)

    print(f"Fuelle {start} bis {ende} an {len(orte)} Punkten auf ...\n")

    neue = []
    uebersprungen = 0
    fehler = 0

    for i, (name, lat, lon) in enumerate(orte, start=1):
        d = hole_zeitraum(lat, lon, start, ende)
        if d is None:
            fehler += 1
            continue

        n = len(d["time"])

        def spalte(feld):
            return d.get(feld) or [None] * n

        for j, tag in enumerate(d["time"]):
            regen = spalte("precipitation_sum")[j]
            if regen is None:
                continue
            if (tag, name) in vorhanden:
                uebersprungen += 1
                continue

            neue.append({
                "datum": tag, "ort": name, "lat": lat, "lon": lon,
                "regen_icon": "",
                "regen_era5": regen,
                "temperatur": leer(spalte("temperature_2m_mean")[j]),
                "bt07": leer(spalte("soil_temperature_0_to_7cm_mean")[j]),
                "bf07": leer(spalte("soil_moisture_0_to_7cm_mean")[j]),
                "bt728": leer(spalte("soil_temperature_7_to_28cm_mean")[j]),
                "bf728": leer(spalte("soil_moisture_7_to_28cm_mean")[j]),
                "et0": leer(spalte("et0_fao_evapotranspiration")[j]),
                "quelle": "era5",
            })

        if i % 100 == 0:
            print(f"  {i} von {len(orte)} ...")

        time.sleep(0.15)

    historie.anhaengen(neue)

    print(f"\n{len(neue)} Eintraege ergaenzt.")
    if uebersprungen:
        print(f"{uebersprungen} bereits vorhanden.")
    if fehler:
        print(f"{fehler} Punkte ohne Daten.")


main()
