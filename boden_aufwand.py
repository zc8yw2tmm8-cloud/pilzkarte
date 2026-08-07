"""
Holt Bodenwerte fuer die Meldeorte aller Pilze.

Warum: bodenanalyse.py vergleicht Fundorte gegen zufaellige
Waldpunkte. Das misst aber auch, wo Menschen unterwegs sind - bei
den Baumarten hat sich gezeigt, dass dieser Anteil groesser ist als
die Biologie.

Der richtige Massstab sind die Orte, an denen ueberhaupt Pilze
gemeldet werden. Die stehen in aufwand_orte.csv; hier kommen ihre
Bodenwerte dazu.

Laeuft lange - rund 8.000 Abfragen bei etwa 0,2 je Sekunde, also
knapp einen Tag. Setzt fort, ein Abbruch kostet nichts.

Ergebnis: bodendaten_aufwand.csv
"""
import os
import csv
import time
import requests

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

QUELLE = "aufwand_orte.csv"
DATEI = "bodendaten_aufwand.csv"

DIENST = "https://rest.isric.org/soilgrids/v2.0/properties/query"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

FELDER = {
    "phh2o": "ph", "cec": "cec", "sand": "sand",
    "clay": "clay", "silt": "silt", "soc": "humus", "nitrogen": "stickstoff",
}
TEILER = {"ph": 10.0, "sand": 10.0, "clay": 10.0, "silt": 10.0,
          "cec": 10.0, "humus": 10.0, "stickstoff": 100.0}

SPALTEN = ["id", "lat", "lon"] + list(TEILER)

# Ein Punkt je Rasterfeld reicht - SoilGrids loest ohnehin nur
# 250 m auf. Das spart einen grossen Teil der Abfragen.
RASTER_GRAD = 0.0025      # rund 250 m


def lade_orte():
    if not os.path.exists(QUELLE):
        return []
    orte = {}
    with open(QUELLE, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                lat, lon = float(z["lat"]), float(z["lon"])
            except (ValueError, KeyError):
                continue
            # Auf das Raster runden und nur einen je Feld behalten
            schluessel = (round(lat / RASTER_GRAD), round(lon / RASTER_GRAD))
            if schluessel not in orte:
                orte[schluessel] = (
                    f"A{schluessel[0]}_{schluessel[1]}",
                    round(schluessel[0] * RASTER_GRAD, 5),
                    round(schluessel[1] * RASTER_GRAD, 5))
    return list(orte.values())


def lade_vorhandene():
    if not os.path.exists(DATEI):
        return {}
    with open(DATEI, "r", encoding="utf-8") as f:
        return {z["id"]: z for z in csv.DictReader(f)}


def hole(lat, lon):
    parameter = [("lat", lat), ("lon", lon), ("depth", "0-5cm"),
                 ("value", "mean")]
    for feld in FELDER:
        parameter.append(("property", feld))

    for versuch in range(3):
        try:
            a = requests.get(DIENST, params=parameter, headers=HEADERS,
                             timeout=60)
            if a.status_code == 429:
                time.sleep(20 * (versuch + 1))
                continue
            if a.status_code != 200:
                time.sleep(3 * (versuch + 1))
                continue
            daten = a.json()
        except Exception:
            time.sleep(3 * (versuch + 1))
            continue

        ergebnis = {}
        for schicht in daten.get("properties", {}).get("layers", []):
            name = FELDER.get(schicht.get("name"))
            if not name:
                continue
            werte = [t["values"].get("mean")
                     for t in schicht.get("depths", [])
                     if t.get("values", {}).get("mean") is not None]
            if werte:
                ergebnis[name] = round(
                    sum(werte) / len(werte) / TEILER.get(name, 1), 2)

        return ergebnis if ergebnis else None

    return None


def schreibe(vorhanden):
    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        for z in vorhanden.values():
            writer.writerow({k: z.get(k, "") for k in SPALTEN})


def main():
    orte = lade_orte()
    if not orte:
        print(f"{QUELLE} fehlt oder ist leer.")
        print("Erst aufwand_orte.py laufen lassen.")
        return

    vorhanden = lade_vorhandene()
    offen = [o for o in orte if o[0] not in vorhanden]

    print(f"{len(orte)} verschiedene Rasterfelder aus {QUELLE}")
    print(f"{len(vorhanden)} schon geholt, {len(offen)} offen\n")

    if not offen:
        print("Nichts zu tun.")
        return

    print(f"Geschaetzt {len(offen) * 5 / 3600:.1f} Stunden.")
    print("Abbruch ist unkritisch - beim Neustart wird fortgesetzt.\n")
    if input("Starten? (j/n) ").strip().lower()[:1] != "j":
        return

    beginn = time.time()
    ohne = 0

    for i, (kennung, lat, lon) in enumerate(offen, start=1):
        werte = hole(lat, lon)
        if werte is None:
            ohne += 1
        else:
            eintrag = {"id": kennung, "lat": lat, "lon": lon}
            eintrag.update(werte)
            vorhanden[kennung] = eintrag

        if i % 50 == 0 or i == len(offen):
            schreibe(vorhanden)
            dauer = time.time() - beginn
            rest = (len(offen) - i) / max(i / max(dauer, 0.1), 0.01) / 60
            print(f"  {i} von {len(offen)}  "
                  f"({i/max(dauer,0.1):.2f}/s, noch ~{rest:.0f} min, "
                  f"{len(vorhanden)} gespeichert)", flush=True)

        time.sleep(0.15)

    schreibe(vorhanden)
    print(f"\n{len(vorhanden)} Meldeorte mit Bodenwerten in {DATEI}.")
    if ohne:
        print(f"{ohne} ohne Werte (Siedlung oder Wasser).")

    werte = sorted(float(z["ph"]) for z in vorhanden.values()
                   if z.get("ph"))
    if werte:
        print(f"\npH an Meldeorten: {werte[0]:.2f} bis {werte[-1]:.2f}, "
              f"Median {werte[len(werte)//2]:.2f}")
    print("\nWeiter mit: python bodenanalyse.py")


main()
