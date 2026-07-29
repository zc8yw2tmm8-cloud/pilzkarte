"""
Holt die Vorhersage fuer 7 Tage. Wird jeden Tag komplett ueberschrieben -
eine alte Vorhersage ist wertlos.

Nur best_match: icon_d2 reicht nur zwei Tage und liefert keine Bodenwerte.
"""
import requests
import csv
import time
from datetime import date, timedelta

DATEI = "wetter_prognose.csv"
PUNKTE_DATEI = "waldpunkte.csv"
TAGE_VORAUS = 6

FELDER = [
    "precipitation_sum",
    "temperature_2m_mean",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_temperature_7_to_28cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "et0_fao_evapotranspiration",
]

SPALTEN = ["datum", "ort", "lat", "lon", "regen", "temperatur",
           "bt07", "bf07", "bt728", "bf728", "et0"]


def lade_punkte():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))
    return punkte


def hole(lat, lon, start, ende):
    url = "https://api.open-meteo.com/v1/forecast"
    parameter = {
        "latitude": lat,
        "longitude": lon,
        "start_date": str(start),
        "end_date": str(ende),
        "daily": ",".join(FELDER),
        "timezone": "Europe/Berlin",
    }
    try:
        antwort = requests.get(url, params=parameter, timeout=30)
        daten = antwort.json()
    except Exception:
        return None
    if "daily" not in daten:
        return None
    return daten["daily"]


def leer(wert):
    return "" if wert is None else wert


def main():
    start = date.today()
    ende = start + timedelta(days=TAGE_VORAUS)
    orte = lade_punkte()

    print(f"Prognose {start} bis {ende} fuer {len(orte)} Punkte ...\n")

    zeilen = []
    fehler = 0

    for i, (name, lat, lon) in enumerate(orte, start=1):
        d = hole(lat, lon, start, ende)
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
            zeilen.append({
                "datum": tag, "ort": name, "lat": lat, "lon": lon,
                "regen": regen,
                "temperatur": leer(spalte("temperature_2m_mean")[j]),
                "bt07": leer(spalte("soil_temperature_0_to_7cm_mean")[j]),
                "bf07": leer(spalte("soil_moisture_0_to_7cm_mean")[j]),
                "bt728": leer(spalte("soil_temperature_7_to_28cm_mean")[j]),
                "bf728": leer(spalte("soil_moisture_7_to_28cm_mean")[j]),
                "et0": leer(spalte("et0_fao_evapotranspiration")[j]),
            })

        if i % 100 == 0:
            print(f"  {i} von {len(orte)} ...")

        time.sleep(0.15)

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\n{len(zeilen)} Prognosewerte gespeichert.")
    if fehler:
        print(f"{fehler} Punkte ohne Daten.")


main()
