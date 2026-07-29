"""
Taeglicher Lauf: holt den Vortag fuer alle Waldpunkte.

Regen und Lufttemperatur aus icon_d2 (2 km),
Bodenwerte und Verdunstung aus best_match (icon_d2 liefert die nicht).
"""
import requests
import csv
import time
from datetime import date, timedelta

import historie

PUNKTE_DATEI = "waldpunkte.csv"

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


def hole_tag(lat, lon, tag):
    """icon_d2 fuer Regen und Lufttemperatur, best_match fuer Bodenwerte."""
    url = "https://api.open-meteo.com/v1/forecast"
    parameter = {
        "latitude": lat,
        "longitude": lon,
        "start_date": str(tag),
        "end_date": str(tag),
        "daily": ",".join(FELDER),
        "models": "icon_d2,best_match",
        "timezone": "Europe/Berlin",
    }

    for versuch in range(4):
        try:
            antwort = requests.get(url, params=parameter, timeout=30)
            daten = antwort.json()
        except Exception:
            time.sleep(3 * (versuch + 1))
            continue

        if "daily" not in daten:
            time.sleep(3 * (versuch + 1))
            continue

        d = daten["daily"]

        def wert(feld, modell):
            liste = d.get(f"{feld}_{modell}")
            if not liste or liste[0] is None:
                return None
            return liste[0]

        regen = wert("precipitation_sum", "icon_d2")
        temp = wert("temperature_2m_mean", "icon_d2")

        # icon_d2 hat Luecken - dann das Standardmodell nehmen
        if regen is None:
            regen = wert("precipitation_sum", "best_match")
        if temp is None:
            temp = wert("temperature_2m_mean", "best_match")
        if regen is None or temp is None:
            return None

        def leer(w):
            return "" if w is None else w

        return {
            "regen_icon": regen,
            "regen_era5": "",
            "temperatur": temp,
            "bt07": leer(wert("soil_temperature_0_to_7cm_mean", "best_match")),
            "bf07": leer(wert("soil_moisture_0_to_7cm_mean", "best_match")),
            "bt728": leer(wert("soil_temperature_7_to_28cm_mean",
                               "best_match")),
            "bf728": leer(wert("soil_moisture_7_to_28cm_mean", "best_match")),
            "et0": leer(wert("et0_fao_evapotranspiration", "best_match")),
            "quelle": "icon_d2",
        }

    return None


def main():
    tag = date.today() - timedelta(days=1)
    orte = lade_punkte()
    # Nur die letzten Monate pruefen - alte koennen keine
    # Dubletten fuer gestern enthalten
    vorhanden = historie.vorhandene(tag - timedelta(days=40))

    neue = []
    uebersprungen = 0
    fehler = 0

    print(f"Sammle {tag} an {len(orte)} Punkten ...\n")

    for i, (name, lat, lon) in enumerate(orte, start=1):
        if (str(tag), name) in vorhanden:
            uebersprungen += 1
            continue

        werte = hole_tag(lat, lon, tag)
        if werte is None:
            fehler += 1
            continue

        zeile = {"datum": str(tag), "ort": name, "lat": lat, "lon": lon}
        zeile.update(werte)
        neue.append(zeile)

        if i % 100 == 0:
            print(f"  {i} von {len(orte)} ...")

        time.sleep(0.15)

    historie.anhaengen(neue)

    print(f"\n{len(neue)} neue Eintraege.")
    if uebersprungen:
        print(f"{uebersprungen} bereits vorhanden.")
    if fehler:
        print(f"{fehler} ohne Daten.")


main()
