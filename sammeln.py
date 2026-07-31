"""
Taeglicher Lauf: holt den Vortag fuer alle Waldpunkte.

Regen und Lufttemperatur aus icon_d2 (2 km),
Bodenwerte und Verdunstung aus best_match (icon_d2 liefert die nicht).
"""
import requests
import csv
import sys
import time
import threading
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

import historie

PUNKTE_DATEI = "waldpunkte.csv"

# Open-Meteo kann mehrere Orte in einer Anfrage beantworten. Ob das
# hier klappt, wird beim Start geprueft - sonst wird einzeln geholt.
BUENDEL = 50
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

SPALTEN = historie.SPALTEN


def lade_punkte():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))
    return punkte


bremse = threading.Event()


def _werte(d, suffix=""):
    """Zieht die Messwerte aus einem daily-Block."""
    def wert(feld, modell):
        liste = d.get(f"{feld}_{modell}")
        if not liste or liste[0] is None:
            return None
        return liste[0]

    regen = wert("precipitation_sum", "icon_d2")
    temp = wert("temperature_2m_mean", "icon_d2")
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
        "bt728": leer(wert("soil_temperature_7_to_28cm_mean", "best_match")),
        "bf728": leer(wert("soil_moisture_7_to_28cm_mean", "best_match")),
        "et0": leer(wert("et0_fao_evapotranspiration", "best_match")),
        "quelle": "icon_d2",
    }


def hole_buendel(orte, tag):
    """
    Holt mehrere Orte in einer Anfrage.

    Rueckgabe: Liste in derselben Reihenfolge wie orte, Eintraege
    koennen None sein. Bei Misserfolg None.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    parameter = {
        "latitude": ",".join(f"{o[1]}" for o in orte),
        "longitude": ",".join(f"{o[2]}" for o in orte),
        "start_date": str(tag), "end_date": str(tag),
        "daily": ",".join(FELDER),
        "models": "icon_d2,best_match",
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

        # Bei mehreren Orten antwortet der Dienst mit einer Liste
        if isinstance(daten, dict):
            daten = [daten]
        if not isinstance(daten, list) or len(daten) != len(orte):
            return None

        return [(_werte(d["daily"]) if isinstance(d, dict) and "daily" in d
                 else None) for d in daten]

    return None


def buendel_moeglich(orte, tag):
    """Kurzer Test, ob der Dienst zwei Orte in einer Anfrage beantwortet."""
    if len(orte) < 2:
        return False
    ergebnis = hole_buendel(orte[:2], tag)
    return ergebnis is not None and len(ergebnis) == 2


def main():
    tag = date.today() - timedelta(days=1)
    orte = lade_punkte()
    vorhanden = historie.vorhandene(tag - timedelta(days=40))

    offen = [o for o in orte if (str(tag), o[0]) not in vorhanden]
    print(f"Sammle {tag} an {len(orte)} Punkten, {len(offen)} offen",
          flush=True)

    if not offen:
        print("Nichts zu tun.", flush=True)
        return

    gebuendelt = buendel_moeglich(offen, tag)
    print(f"Mehrere Orte je Anfrage: "
          f"{'ja, ' + str(BUENDEL) + ' auf einmal' if gebuendelt else 'nein'}",
          flush=True)

    pakete = ([offen[i:i + BUENDEL] for i in range(0, len(offen), BUENDEL)]
              if gebuendelt else [[o] for o in offen])

    neue = []
    fehler = 0
    sperre = threading.Lock()
    beginn = time.time()
    erledigt = [0]

    def arbeite(paket):
        ergebnis = hole_buendel(paket, tag)
        time.sleep(PAUSE)
        return paket, ergebnis

    with ThreadPoolExecutor(max_workers=ARBEITER) as pool:
        for paket, ergebnis in pool.map(arbeite, pakete):
            with sperre:
                erledigt[0] += 1
                if ergebnis is None:
                    fehler += len(paket)
                else:
                    for (name, lat, lon), werte in zip(paket, ergebnis):
                        if werte is None:
                            fehler += 1
                            continue
                        zeile = {"datum": str(tag), "ort": name,
                                 "lat": lat, "lon": lon}
                        zeile.update(werte)
                        neue.append(zeile)

                if erledigt[0] % 20 == 0 or erledigt[0] == len(pakete):
                    dauer = time.time() - beginn
                    rest = (len(pakete) - erledigt[0]) / max(
                        erledigt[0] / max(dauer, 0.1), 0.01)
                    print(f"  {erledigt[0]} von {len(pakete)} Anfragen, "
                          f"{len(neue)} Werte, {fehler} Fehler, "
                          f"noch ~{rest/60:.0f} min", flush=True)

    historie.anhaengen(neue)

    print(f"\n{len(neue)} neue Eintraege in {time.time()-beginn:.0f} s.",
          flush=True)
    if fehler:
        print(f"{fehler} Punkte ohne Daten.", flush=True)
        if fehler > len(orte) * 0.5:
            print("Mehr als die Haelfte fehlt - vermutlich gedrosselt.",
                  flush=True)
            sys.exit(1)


main()
