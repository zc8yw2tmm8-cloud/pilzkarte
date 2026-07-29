import requests
from collections import Counter

ART = "Boletus edulis"          # Steinpilz

# Groesserer Ausschnitt als dein Waldraster - sonst zu wenige Funde
SUED, NORD = 51.5, 53.5
WEST, OST = 9.0, 12.0

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}


def hole_taxonkey(name):
    """GBIF-interne ID der Art nachschlagen."""
    url = "https://api.gbif.org/v1/species/match"
    antwort = requests.get(url, params={"name": name},
                           headers=HEADERS, timeout=30)
    daten = antwort.json()
    print(f"Art erkannt als: {daten.get('scientificName')} "
          f"(Rang {daten.get('rank')}, Treffer {daten.get('matchType')})")
    return daten.get("usageKey")


def hole_funde(taxonkey, limit=300):
    """Fundmeldungen mit Koordinaten abfragen."""
    url = "https://api.gbif.org/v1/occurrence/search"
    parameter = {
        "taxonKey": taxonkey,
        "country": "DE",
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "decimalLatitude": f"{SUED},{NORD}",
        "decimalLongitude": f"{WEST},{OST}",
        "limit": limit,
    }
    antwort = requests.get(url, params=parameter, headers=HEADERS, timeout=60)
    return antwort.json()


def main():
    key = hole_taxonkey(ART)
    if key is None:
        print("Art nicht gefunden.")
        return

    daten = hole_funde(key)
    gesamt = daten.get("count", 0)
    treffer = daten.get("results", [])

    print(f"\nGesamt im Suchgebiet: {gesamt} Funde")
    print(f"Geladen zur Pruefung: {len(treffer)}\n")

    if not treffer:
        return

    mit_datum = 0
    genauigkeit = []
    jahre = Counter()
    monate = Counter()
    quellen = Counter()

    for t in treffer:
        if t.get("eventDate"):
            mit_datum += 1
        if t.get("year"):
            jahre[t["year"]] += 1
        if t.get("month"):
            monate[t["month"]] += 1
        if t.get("coordinateUncertaintyInMeters") is not None:
            genauigkeit.append(t["coordinateUncertaintyInMeters"])
        quellen[t.get("datasetName", "unbekannt")[:45]] += 1

    print(f"Mit Funddatum: {mit_datum} von {len(treffer)}")

    if genauigkeit:
        genauigkeit.sort()
        mitte = genauigkeit[len(genauigkeit) // 2]
        print(f"Koordinaten-Unsicherheit: Median {mitte} m, "
              f"Bereich {min(genauigkeit)}-{max(genauigkeit)} m "
              f"({len(genauigkeit)} Angaben)")
    else:
        print("Keine Angaben zur Koordinaten-Unsicherheit")

    print("\nFunde pro Monat:")
    for m in range(1, 13):
        if monate[m]:
            print(f"  {m:2d}: {'#' * (monate[m] // 2)} {monate[m]}")

    print("\nJuengste Jahre:")
    for j in sorted(jahre, reverse=True)[:8]:
        print(f"  {j}: {jahre[j]}")

    print("\nWichtigste Quellen:")
    for q, n in quellen.most_common(5):
        print(f"  {n:4d}  {q}")

    print("\nBeispiel-Fund:")
    b = treffer[0]
    for feld in ["eventDate", "decimalLatitude", "decimalLongitude",
                 "coordinateUncertaintyInMeters", "locality", "datasetName"]:
        print(f"  {feld}: {b.get(feld)}")


main()