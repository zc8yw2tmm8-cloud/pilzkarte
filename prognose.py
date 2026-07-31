"""
Holt die Vorhersage fuer 7 Tage. Wird jeden Tag komplett ueberschrieben -
eine alte Vorhersage ist wertlos.

Nur best_match: icon_d2 reicht nur zwei Tage und liefert keine Bodenwerte.
"""
import requests
import csv
import sys
import time
import threading
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

DATEI = "wetter_prognose.csv"
PUNKTE_DATEI = "waldpunkte.csv"
TAGE_VORAUS = 6

BUENDEL = 40
ARBEITER = 4
PAUSE = 0.1

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


bremse = threading.Event()


def hole_buendel(orte, start, ende):
    """Mehrere Orte in einer Anfrage. None bei Misserfolg."""
    url = "https://api.open-meteo.com/v1/forecast"
    parameter = {
        "latitude": ",".join(f"{o[1]}" for o in orte),
        "longitude": ",".join(f"{o[2]}" for o in orte),
        "start_date": str(start), "end_date": str(ende),
        "daily": ",".join(FELDER),
        "timezone": "Europe/Berlin",
    }

    for versuch in range(4):
        while bremse.is_set():
            time.sleep(1)
        try:
            antwort = requests.get(url, params=parameter, timeout=120)
        except Exception:
            time.sleep(2 * (versuch + 1))
            continue

        if antwort.status_code == 429:
            if not bremse.is_set():
                bremse.set()
                time.sleep(20)
                bremse.clear()
            time.sleep(4 * (versuch + 1))
            continue
        if antwort.status_code != 200:
            time.sleep(2 * (versuch + 1))
            continue

        try:
            daten = antwort.json()
        except Exception:
            time.sleep(2)
            continue

        if isinstance(daten, dict):
            daten = [daten]
        if not isinstance(daten, list) or len(daten) != len(orte):
            return None

        return [d.get("daily") if isinstance(d, dict) else None
                for d in daten]

    return None


def buendel_moeglich(orte, start, ende):
    if len(orte) < 2:
        return False
    e = hole_buendel(orte[:2], start, ende)
    return e is not None and len(e) == 2


def leer(wert):
    return "" if wert is None else wert


def main():
    start = date.today()
    ende = start + timedelta(days=TAGE_VORAUS)
    orte = lade_punkte()

    print(f"Prognose {start} bis {ende} fuer {len(orte)} Punkte", flush=True)

    gebuendelt = buendel_moeglich(orte, start, ende)
    print(f"Mehrere Orte je Anfrage: "
          f"{'ja, ' + str(BUENDEL) + ' auf einmal' if gebuendelt else 'nein'}",
          flush=True)

    pakete = ([orte[i:i + BUENDEL] for i in range(0, len(orte), BUENDEL)]
              if gebuendelt else [[o] for o in orte])

    zeilen = []
    fehler = 0
    sperre = threading.Lock()
    beginn = time.time()
    erledigt = [0]

    def arbeite(paket):
        return paket, hole_buendel(paket, start, ende)

    with ThreadPoolExecutor(max_workers=ARBEITER) as pool:
        for paket, ergebnis in pool.map(arbeite, pakete):
            time.sleep(PAUSE)
            with sperre:
                erledigt[0] += 1
                if ergebnis is None:
                    fehler += len(paket)
                else:
                    for (name, lat, lon), d in zip(paket, ergebnis):
                        if not d:
                            fehler += 1
                            continue
                        n = len(d["time"])

                        def spalte(feld, d=d, n=n):
                            return d.get(feld) or [None] * n

                        for j, tag in enumerate(d["time"]):
                            regen = spalte("precipitation_sum")[j]
                            if regen is None:
                                continue
                            zeilen.append({
                                "datum": tag, "ort": name,
                                "lat": lat, "lon": lon, "regen": regen,
                                "temperatur": leer(
                                    spalte("temperature_2m_mean")[j]),
                                "bt07": leer(spalte(
                                    "soil_temperature_0_to_7cm_mean")[j]),
                                "bf07": leer(spalte(
                                    "soil_moisture_0_to_7cm_mean")[j]),
                                "bt728": leer(spalte(
                                    "soil_temperature_7_to_28cm_mean")[j]),
                                "bf728": leer(spalte(
                                    "soil_moisture_7_to_28cm_mean")[j]),
                                "et0": leer(spalte(
                                    "et0_fao_evapotranspiration")[j]),
                            })

                if erledigt[0] % 20 == 0 or erledigt[0] == len(pakete):
                    dauer = time.time() - beginn
                    rest = (len(pakete) - erledigt[0]) / max(
                        erledigt[0] / max(dauer, 0.1), 0.01)
                    print(f"  {erledigt[0]} von {len(pakete)} Anfragen, "
                          f"{len(zeilen)} Werte, {fehler} Fehler, "
                          f"noch ~{rest/60:.0f} min", flush=True)

    if not zeilen:
        print("Keine Prognosewerte erhalten - alte Datei bleibt stehen.",
              flush=True)
        sys.exit(1)

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\n{len(zeilen)} Prognosewerte in {time.time()-beginn:.0f} s.",
          flush=True)
    if fehler:
        print(f"{fehler} Punkte ohne Daten.", flush=True)


main()
