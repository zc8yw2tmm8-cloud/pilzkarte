"""
Holt Fundmeldungen fuer alle fuenf Startarten von GBIF.

Zusaetzlich: die monatliche Zahl ALLER Pilzmeldungen in derselben Region.
Das ist die Aufwandskorrektur - im Oktober sind mehr Sammler unterwegs,
also steigen alle Zahlen. Nur das Verhaeltnis Art/Alle sagt etwas ueber
die Art aus.

Laeuft EINMAL (bzw. einmal pro Saison neu).
Ergebnis: funde_arten.csv und aufwand.csv
"""
import requests
import csv
import time
from concurrent.futures import ThreadPoolExecutor

ARTEN = {
    "steinpilz": "Boletus edulis",
    "sommersteinpilz": "Boletus reticulatus",
    "marone": "Imleria badia",
    "pfifferling": "Cantharellus cibarius",
    "birkenpilz": "Leccinum scabrum",
    "schwefelporling": "Laetiporus sulphureus",
    "parasol": "Macrolepiota procera",
    "hexenroehrling": "Neoboletus erythropus",
    "netzhexe": "Suillellus luridus",
    "reizker": "Lactarius deliciosus",
    "krauseglucke": "Sparassis crispa",
}

# Grosszuegiger als das eigene Raster - sonst zu wenige Funde
SUED, NORD = 51.5, 53.5
WEST, OST = 9.0, 12.0

JAHR_VON, JAHR_BIS = 2015, 2026

# Bezugsgruppe fuer die Aufwandskorrektur - wie viele Menschen suchen
# gerade ueberhaupt Pilze?
#
# "Fungi" ist zu breit: zaehlt Flechten und holzbewohnende Winterarten
#   mit, die im Januar gemeldet werden.
# "Boletales" ist zu eng: der Steinpilz IST ein Boletales. Ihn durch
#   alle Roehrlinge zu teilen entfernt genau die Saisonalitaet, die man
#   messen will - und der Schwefelporling gehoert gar nicht dazu.
# "Agaricomycetes" liegt dazwischen: alle Staenderpilze mit Fruchtkoerper,
#   also Roehrlinge, Blaetterpilze, Porlinge und Leistlinge - aber keine
#   Flechten und keine Schimmelpilze.
AUFWAND_GRUPPE = "Agaricomycetes"

DATEI = "funde_arten.csv"
AUFWAND_DATEI = "aufwand.csv"

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}
BASIS = "https://api.gbif.org/v1"

SPALTEN = ["art", "gbif_id", "datum", "lat", "lon", "unsicherheit_m", "ort"]


def taxonkey(name):
    antwort = requests.get(f"{BASIS}/species/match", params={"name": name},
                           headers=HEADERS, timeout=30)
    d = antwort.json()
    return d.get("usageKey"), d.get("scientificName")


def sauberes_datum(rohtext):
    if not rohtext:
        return None
    text = str(rohtext).split("/")[0][:10]
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        return None
    return text


def hole_funde(key):
    zeilen = []
    offset = 0

    while True:
        parameter = {
            "taxonKey": key,
            "country": "DE",
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "decimalLatitude": f"{SUED},{NORD}",
            "decimalLongitude": f"{WEST},{OST}",
            "year": f"{JAHR_VON},{JAHR_BIS}",
            "limit": 300,
            "offset": offset,
        }
        antwort = requests.get(f"{BASIS}/occurrence/search", params=parameter,
                               headers=HEADERS, timeout=90)
        daten = antwort.json()
        treffer = daten.get("results", [])

        if not treffer:
            break

        for t in treffer:
            datum = sauberes_datum(t.get("eventDate"))
            if datum is None:
                continue
            zeilen.append({
                "gbif_id": t.get("key"),
                "datum": datum,
                "lat": round(t["decimalLatitude"], 5),
                "lon": round(t["decimalLongitude"], 5),
                "unsicherheit_m": t.get("coordinateUncertaintyInMeters", ""),
                "ort": (t.get("locality") or "").replace("\n", " ")[:60],
            })

        if daten.get("endOfRecords"):
            break
        offset += 300
        time.sleep(0.4)

    return zeilen


def _monatszahl(pilz_key, jahr, monat):
    letzter = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
               7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}[monat]
    parameter = {
        "taxonKey": pilz_key,
        "country": "DE",
        "hasCoordinate": "true",
        "decimalLatitude": f"{SUED},{NORD}",
        "decimalLongitude": f"{WEST},{OST}",
        "eventDate": f"{jahr}-{monat:02d}-01,{jahr}-{monat:02d}-{letzter}",
        "limit": 0,
    }
    for _ in range(3):
        try:
            antwort = requests.get(f"{BASIS}/occurrence/search",
                                   params=parameter, headers=HEADERS,
                                   timeout=60)
            return jahr, monat, antwort.json().get("count", 0)
        except Exception:
            time.sleep(2)
    return jahr, monat, ""


def hole_aufwand():
    """Zahl ALLER Pilzmeldungen je Jahr und Monat. Laeuft parallel."""
    pilz_key, name = taxonkey(AUFWAND_GRUPPE)
    print(f"Aufwandsreferenz: {name} (Key {pilz_key})")

    paare = [(j, m) for j in range(JAHR_VON, JAHR_BIS + 1)
             for m in range(1, 13)]

    zeilen = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        auftraege = [pool.submit(_monatszahl, pilz_key, j, m)
                     for j, m in paare]
        for a in auftraege:
            jahr, monat, anzahl = a.result()
            zeilen.append({"jahr": jahr, "monat": monat, "anzahl": anzahl})

    zeilen.sort(key=lambda z: (z["jahr"], z["monat"]))

    for jahr in range(JAHR_VON, JAHR_BIS + 1):
        summe = sum(z["anzahl"] for z in zeilen
                    if z["jahr"] == jahr and z["anzahl"] != "")
        print(f"  {jahr}: {summe} Meldungen")

    with open(AUFWAND_DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["jahr", "monat", "anzahl"])
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"Aufwand in {AUFWAND_DATEI} gespeichert.\n")


def main():
    alle = []

    def eine_art(schluessel, wissenschaftlich):
        key, name = taxonkey(wissenschaftlich)
        if key is None:
            return schluessel, wissenschaftlich, None, []
        funde = hole_funde(key)
        for f in funde:
            f["art"] = schluessel
        return schluessel, name, key, funde

    with ThreadPoolExecutor(max_workers=4) as pool:
        auftraege = [pool.submit(eine_art, s, w) for s, w in ARTEN.items()]
        for a in auftraege:
            schluessel, name, key, funde = a.result()
            if key is None:
                print(f"{schluessel}: Art nicht gefunden ({name})")
                continue
            alle.extend(funde)
            print(f"{schluessel:16s} {name:32s} {len(funde):5d} Funde")

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        writer.writerows(alle)

    print(f"\n{len(alle)} Funde in {DATEI} gespeichert.\n")

    hole_aufwand()


main()
