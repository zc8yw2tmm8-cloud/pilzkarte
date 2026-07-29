"""
Holt die Fundorte ALLER Pilzmeldungen der Region von GBIF.

Damit laesst sich die Beobachterverzerrung raeumlich herausrechnen:
Wo Menschen ueberhaupt Pilze melden, ist der Massstab - nicht, wo
zufaellig Wald steht.

Ohne das misst die Baumartenkalibrierung nur, dass Eichenwaelder
naeher an Ortschaften liegen als Kiefernforste.

Ergebnis: aufwand_orte.csv
"""
import requests
import csv
import time

SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
JAHR_VON, JAHR_BIS = 2015, 2026

GRUPPE = "Agaricomycetes"
DATEI = "aufwand_orte.csv"
MAX_UNSICHERHEIT = 500

BASIS = "https://api.gbif.org/v1"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}


def taxonkey(name):
    a = requests.get(f"{BASIS}/species/match", params={"name": name},
                     headers=HEADERS, timeout=30).json()
    return a.get("usageKey"), a.get("scientificName")


def main():
    key, name = taxonkey(GRUPPE)
    if key is None:
        print(f"{GRUPPE} nicht gefunden.")
        return
    print(f"Bezugsgruppe: {name} (Key {key})")
    print(f"Gebiet: {SUED}-{NORD} Nord, {WEST}-{OST} Ost\n")

    zeilen = []
    offset = 0
    verworfen = 0

    while True:
        parameter = {
            "taxonKey": key, "country": "DE",
            "hasCoordinate": "true", "hasGeospatialIssue": "false",
            "decimalLatitude": f"{SUED},{NORD}",
            "decimalLongitude": f"{WEST},{OST}",
            "year": f"{JAHR_VON},{JAHR_BIS}",
            "limit": 300, "offset": offset,
        }
        try:
            daten = requests.get(f"{BASIS}/occurrence/search",
                                 params=parameter, headers=HEADERS,
                                 timeout=90).json()
        except Exception as e:
            print("Fehler:", str(e)[:100])
            break

        treffer = daten.get("results", [])
        if not treffer:
            break

        for t in treffer:
            u = t.get("coordinateUncertaintyInMeters")
            if u is not None and u > MAX_UNSICHERHEIT:
                verworfen += 1
                continue
            zeilen.append({
                "gbif_id": t.get("key"),
                "lat": round(t["decimalLatitude"], 5),
                "lon": round(t["decimalLongitude"], 5),
                "jahr": t.get("year", ""),
            })

        if len(zeilen) % 3000 < 300:
            print(f"  {len(zeilen)} Meldungen ...")

        if daten.get("endOfRecords"):
            break
        offset += 300
        if offset >= 100000:      # GBIF-Grenze fuer offset
            print("  GBIF-Grenze erreicht, das reicht als Stichprobe")
            break
        time.sleep(0.3)

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["gbif_id", "lat", "lon", "jahr"])
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\n{len(zeilen)} Meldeorte in {DATEI}.")
    if verworfen:
        print(f"{verworfen} wegen ungenauer Koordinaten verworfen.")
    print("\nWeiter mit: python baumarten_kalibrieren.py")


main()
