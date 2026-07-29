"""
Holt die Hoehenlage fuer alle Waldpunkte.

Open-Meteo hat eine eigene Hoehen-API, die bis zu 100 Koordinaten
pro Aufruf annimmt - fuer 1046 Punkte also rund 11 Aufrufe.

Laeuft EINMAL. Ergebnis: hoehen.csv
"""
import requests
import csv
import time

PUNKTE_DATEI = "waldpunkte.csv"
DATEI = "hoehen.csv"
BLOCK = 100


def lade_punkte():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))
    return punkte


def hole_hoehen(teil):
    url = "https://api.open-meteo.com/v1/elevation"
    parameter = {
        "latitude": ",".join(str(p[1]) for p in teil),
        "longitude": ",".join(str(p[2]) for p in teil),
    }
    try:
        antwort = requests.get(url, params=parameter, timeout=60)
        daten = antwort.json()
    except Exception as e:
        print("  Fehler:", e)
        return None

    return daten.get("elevation")


def main():
    punkte = lade_punkte()
    print(f"{len(punkte)} Punkte in Bloecken von {BLOCK}\n")

    zeilen = []

    for start in range(0, len(punkte), BLOCK):
        teil = punkte[start:start + BLOCK]
        hoehen = None
        for versuch in range(3):
            hoehen = hole_hoehen(teil)
            if hoehen is not None:
                break
            print(f"  Block ab {start}: Versuch {versuch + 1} fehlgeschlagen, warte ...")
            time.sleep(5)

        if hoehen is None or len(hoehen) != len(teil):
            print(f"  Block ab {start}: fehlgeschlagen")
            continue

        for (name, lat, lon), h in zip(teil, hoehen):
            zeilen.append({"id": name, "lat": lat, "lon": lon, "hoehe": h})

        print(f"  {len(zeilen)} von {len(punkte)} ...")
        time.sleep(0.5)

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "lat", "lon", "hoehe"])
        writer.writeheader()
        writer.writerows(zeilen)

    if zeilen:
        werte = sorted(z["hoehe"] for z in zeilen)
        print(f"\n{len(zeilen)} Hoehen gespeichert.")
        print(f"Von {werte[0]} bis {werte[-1]} m, "
              f"Median {werte[len(werte) // 2]} m")


main()
