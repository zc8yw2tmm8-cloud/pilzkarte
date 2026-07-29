"""
Hintergrundstichprobe: Wie sieht das Wetter in der Region UEBERHAUPT aus?

Holt fuer eine Auswahl von Waldpunkten die komplette Tagesreihe seit 2019.
Damit lassen sich Fundbedingungen mit dem Normalzustand vergleichen -
ohne diese Referenz sagt "Funde bei 31 % Bodenfeuchte" nichts aus.

Laeuft EINMAL. Ergebnis: hintergrund.csv
"""
import requests
import csv
import os
import time
from datetime import date, timedelta

PUNKTE_DATEI = "waldpunkte.csv"
DATEI = "hintergrund.csv"

ANZAHL_PUNKTE = 100          # gleichmaessig aus den 1046 gezogen
START = date(2019, 1, 1)

FELDER = [
    "precipitation_sum",
    "temperature_2m_mean",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_temperature_7_to_28cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "et0_fao_evapotranspiration",
]

SPALTEN = ["ort", "lat", "lon", "hoehe", "datum", "regen", "temp",
           "bt07", "bf07", "bt728", "bf728", "et0"]


def lade_punkte():
    alle = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            alle.append((z["id"], float(z["lat"]), float(z["lon"])))

    if len(alle) <= ANZAHL_PUNKTE:
        return alle

    # Gleichmaessig ueber die Liste greifen - die ist nach Lage sortiert,
    # deshalb ergibt das eine gute raeumliche Streuung
    schritt = len(alle) / ANZAHL_PUNKTE
    return [alle[int(i * schritt)] for i in range(ANZAHL_PUNKTE)]


def hole_reihe(lat, lon, start, ende):
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
        antwort = requests.get(url, params=parameter, timeout=120)
        daten = antwort.json()
    except Exception as e:
        print("   Fehler:", e)
        return None, None

    if "daily" not in daten:
        return None, None

    return daten["daily"], daten.get("elevation")


def leer(wert):
    return "" if wert is None else wert


def main():
    punkte = lade_punkte()
    ende = date.today() - timedelta(days=1)

    print(f"Hintergrund von {START} bis {ende}")
    print(f"{len(punkte)} Punkte, ein API-Aufruf pro Punkt\n")

    neu = not os.path.exists(DATEI)
    geschrieben = 0
    fehler = 0

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()

        for i, (name, lat, lon) in enumerate(punkte, start=1):
            d, hoehe = hole_reihe(lat, lon, START, ende)

            if d is None:
                fehler += 1
                print(f"  {name}: keine Daten")
                continue

            n = len(d["time"])

            def spalte(feld):
                return d.get(feld) or [None] * n

            reihen = zip(
                d["time"],
                spalte("precipitation_sum"),
                spalte("temperature_2m_mean"),
                spalte("soil_temperature_0_to_7cm_mean"),
                spalte("soil_moisture_0_to_7cm_mean"),
                spalte("soil_temperature_7_to_28cm_mean"),
                spalte("soil_moisture_7_to_28cm_mean"),
                spalte("et0_fao_evapotranspiration"),
            )

            for tag, regen, temp, bt07, bf07, bt728, bf728, et0 in reihen:
                if regen is None:
                    continue
                writer.writerow({
                    "ort": name, "lat": lat, "lon": lon,
                    "hoehe": leer(hoehe), "datum": tag,
                    "regen": regen, "temp": leer(temp),
                    "bt07": leer(bt07), "bf07": leer(bf07),
                    "bt728": leer(bt728), "bf728": leer(bf728),
                    "et0": leer(et0),
                })
                geschrieben += 1

            if i % 10 == 0:
                print(f"  {i} von {len(punkte)} Punkten, {geschrieben} Tage")

            time.sleep(0.4)

    print(f"\n{geschrieben} Punkt-Tage in {DATEI} gespeichert.")
    if fehler:
        print(f"{fehler} Punkte ohne Daten.")
    groesse = os.path.getsize(DATEI) / 1024 / 1024
    print(f"Dateigroesse: {round(groesse, 1)} MB")


main()
