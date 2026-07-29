"""
Prueft, ob SoilGrids den Kalk-Sand-Gegensatz in eurer Region abbildet.

Getestet werden vier Punkte mit bekanntem Untergrund:
  Elm         - Muschelkalk, Buchenwald   -> pH sollte hoch sein
  Suedheide   - glazialer Sand, Kiefer    -> pH sollte niedrig sein
  Barnbruch   - Bruchwald, Niedermoor
  Wolfsburg   - Umgebung, Vergleichswert

Wenn zwischen Elm und Suedheide keine deutliche Differenz steht,
lohnt der grosse Lauf nicht.
"""
import requests
import time

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

PUNKTE = [
    ("Elm (Muschelkalk, Buche)", 52.185, 10.880),
    ("Suedheide (Sand, Kiefer)", 52.830, 10.280),
    ("Barnbruch (Bruchwald)",    52.425, 10.675),
    ("Bei Wolfsburg",            52.420, 10.790),
]

# Was geholt wird. phh2o = pH, cec = Naehrstoffspeicher,
# sand/clay = Bodenart, soc = Humus
EIGENSCHAFTEN = ["phh2o", "cec", "sand", "clay", "soc", "nitrogen"]
TIEFEN = ["0-5cm", "5-15cm", "15-30cm"]

# SoilGrids liefert ganze Zahlen - hier die Teiler fuer echte Einheiten
TEILER = {"phh2o": 10, "cec": 10, "sand": 10, "clay": 10,
          "soc": 10, "nitrogen": 100}
EINHEIT = {"phh2o": "", "cec": " cmol/kg", "sand": " %", "clay": " %",
           "soc": " g/kg", "nitrogen": " g/kg"}


def hole(lat, lon):
    parameter = [("lon", lon), ("lat", lat), ("value", "mean")]
    for e in EIGENSCHAFTEN:
        parameter.append(("property", e))
    for t in TIEFEN:
        parameter.append(("depth", t))

    try:
        antwort = requests.get(URL, params=parameter, headers=HEADERS,
                               timeout=60)
    except Exception as e:
        print("   Verbindungsfehler:", e)
        return None

    if antwort.status_code != 200:
        print(f"   HTTP {antwort.status_code}: {antwort.text[:150]}")
        return None

    try:
        return antwort.json()
    except Exception:
        print("   Kein JSON:", antwort.text[:150])
        return None


def auswerten(daten):
    """Zieht die Mittelwerte je Eigenschaft aus der Antwort."""
    ergebnis = {}
    lagen = daten.get("properties", {}).get("layers", [])

    for lage in lagen:
        name = lage.get("name")
        werte = []
        for tiefe in lage.get("depths", []):
            w = tiefe.get("values", {}).get("mean")
            if w is not None:
                werte.append(w)
        if werte:
            ergebnis[name] = sum(werte) / len(werte) / TEILER.get(name, 1)

    return ergebnis


def main():
    print("Frage SoilGrids ab (jeder Punkt dauert ein paar Sekunden)\n")
    alle = {}

    for name, lat, lon in PUNKTE:
        print(f"{name} ...")
        daten = hole(lat, lon)
        if daten is None:
            continue

        werte = auswerten(daten)
        if not werte:
            print("   keine Werte in der Antwort")
            print("   Rohantwort:", str(daten)[:300])
            continue

        alle[name] = werte
        for e in EIGENSCHAFTEN:
            if e in werte:
                print(f"   {e:9s} {round(werte[e], 2)}{EINHEIT.get(e, '')}")
        time.sleep(2)

    # Der eigentliche Test
    print("\n" + "=" * 52)
    elm = alle.get("Elm (Muschelkalk, Buche)", {}).get("phh2o")
    heide = alle.get("Suedheide (Sand, Kiefer)", {}).get("phh2o")

    if elm is None or heide is None:
        print("Vergleich nicht moeglich - Abfrage unvollstaendig.")
        return

    print(f"pH Elm:       {round(elm, 2)}")
    print(f"pH Suedheide: {round(heide, 2)}")
    print(f"Differenz:    {round(elm - heide, 2)}")
    print()

    if elm - heide >= 0.8:
        print("Deutlicher Unterschied - SoilGrids bildet den Gegensatz ab.")
        print("Der grosse Lauf lohnt sich.")
    elif elm - heide >= 0.4:
        print("Schwacher Unterschied - grenzwertig brauchbar.")
    else:
        print("Kaum Unterschied. SoilGrids ist hier zu grob,")
        print("der grosse Lauf lohnt sich nicht.")


main()
