"""
Holt die Hoehenlage fuer alle Waldpunkte.

Open-Meteo nimmt bis zu 100 Koordinaten pro Aufruf an.

Setzt fort: Vorhandene Hoehen bleiben stehen, es werden nur fehlende
geholt. Schlaegt ein Block fehl, gehen keine alten Daten verloren -
frueher wurde die Datei komplett neu geschrieben, und ein
gescheiterter Lauf hat den halben Bestand geloescht.

Ergebnis: hoehen.csv
"""
import os
import csv
import time
import requests

PUNKTE_DATEI = "waldpunkte.csv"
DATEI = "hoehen.csv"
BLOCK = 100
ANLAEUFE = 4


def lade_punkte():
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        return [(z["id"], float(z["lat"]), float(z["lon"]))
                for z in csv.DictReader(f)]


def lade_vorhandene():
    """Was schon da ist - id -> Zeile."""
    if not os.path.exists(DATEI):
        return {}
    with open(DATEI, "r", encoding="utf-8") as f:
        return {z["id"]: z for z in csv.DictReader(f)
                if (z.get("hoehe") or "").strip()}


def hole_hoehen(teil):
    url = "https://api.open-meteo.com/v1/elevation"
    parameter = {
        "latitude": ",".join(str(p[1]) for p in teil),
        "longitude": ",".join(str(p[2]) for p in teil),
    }

    for anlauf in range(1, ANLAEUFE + 1):
        try:
            antwort = requests.get(url, params=parameter, timeout=90)
            if antwort.status_code == 429:
                wartezeit = 30 * anlauf
                print(f"    gedrosselt, warte {wartezeit} s", flush=True)
                time.sleep(wartezeit)
                continue
            if antwort.status_code != 200:
                print(f"    HTTP {antwort.status_code}", flush=True)
                time.sleep(5 * anlauf)
                continue
            hoehen = antwort.json().get("elevation")
            if hoehen and len(hoehen) == len(teil):
                return hoehen
        except Exception as e:
            print(f"    {str(e)[:60]}", flush=True)
        time.sleep(5 * anlauf)

    return None


def schreibe(vorhanden):
    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "lat", "lon", "hoehe"])
        writer.writeheader()
        for z in vorhanden.values():
            writer.writerow({k: z[k] for k in
                             ("id", "lat", "lon", "hoehe")})


def main():
    punkte = lade_punkte()
    vorhanden = lade_vorhandene()

    offen = [p for p in punkte if p[0] not in vorhanden]

    print(f"{len(punkte)} Punkte, {len(vorhanden)} schon bekannt, "
          f"{len(offen)} offen\n", flush=True)

    if not offen:
        print("Nichts zu holen.")
        return

    fehler = 0
    for start in range(0, len(offen), BLOCK):
        teil = offen[start:start + BLOCK]
        hoehen = hole_hoehen(teil)

        if hoehen is None:
            print(f"  Block ab {start}: fehlgeschlagen, "
                  f"beim naechsten Lauf nochmal", flush=True)
            fehler += len(teil)
            continue

        for (name, lat, lon), h in zip(teil, hoehen):
            vorhanden[name] = {"id": name, "lat": lat, "lon": lon,
                               "hoehe": h}

        # Nach jedem Block sichern - ein Abbruch kostet dann nur den
        # laufenden Block
        schreibe(vorhanden)
        print(f"  {len(vorhanden)} von {len(punkte)} ...", flush=True)
        time.sleep(0.5)

    schreibe(vorhanden)

    werte = sorted(float(z["hoehe"]) for z in vorhanden.values())
    print(f"\n{len(vorhanden)} Hoehen in {DATEI}.")
    if werte:
        print(f"Von {werte[0]:.0f} bis {werte[-1]:.0f} m, "
              f"Median {werte[len(werte) // 2]:.0f} m")
    if fehler:
        print(f"{fehler} Punkte offen - nochmal starten, "
              f"es wird fortgesetzt.")


main()
