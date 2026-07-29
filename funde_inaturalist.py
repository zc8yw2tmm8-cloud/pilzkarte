"""
Holt Beobachtungen direkt von iNaturalist.

Ueber GBIF kommen nur die als "research grade" bestaetigten Meldungen
an. Direkt bei iNaturalist gibt es zusaetzlich:
  needs_id  - noch in Bestimmung, oft trotzdem richtig
  casual    - ohne Foto, ohne Datum oder aus Kultur

Ergebnis: funde_inat.csv, gleiche Spalten wie funde_arten.csv, damit
sich beide zusammenfuegen lassen. Wird NICHT automatisch gemischt -
erst schauen, dann entscheiden.
"""
import requests
import csv
import os
import time

ARTEN = {
    "steinpilz": "Boletus edulis",
    "sommersteinpilz": "Boletus reticulatus",
    "marone": "Imleria badia",
    "pfifferling": "Cantharellus cibarius",
    "birkenpilz": "Leccinum scabrum",
    "schwefelporling": "Laetiporus sulphureus",
    "parasol": "Macrolepiota procera",
}

SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
JAHR_VON, JAHR_BIS = 2015, 2026

# Welche Pruefstufen. "research" allein entspricht dem, was ihr schon
# ueber GBIF habt - dann lohnt der Lauf nicht.
STUFEN = ["research", "needs_id"]

MAX_UNSICHERHEIT = 500
DATEI = "funde_inat.csv"
VERGLEICH = "funde_arten.csv"

BASIS = "https://api.inaturalist.org/v1"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

SPALTEN = ["art", "gbif_id", "datum", "lat", "lon", "unsicherheit_m", "ort"]


def taxon_id(name):
    try:
        antwort = requests.get(f"{BASIS}/taxa", params={"q": name, "rank": "species"},
                               headers=HEADERS, timeout=45)
        for t in antwort.json().get("results", []):
            if t.get("name", "").lower() == name.lower():
                return t["id"], t.get("preferred_common_name") or t["name"]
        ergebnisse = antwort.json().get("results", [])
        if ergebnisse:
            return ergebnisse[0]["id"], ergebnisse[0].get("name")
    except Exception as e:
        print("   ", str(e)[:100])
    return None, None


def hole_art(tid):
    """Alle Beobachtungen einer Art im Gebiet. Blaettert ueber id_above."""
    zeilen = []
    letzte_id = 0
    verworfen = {"unscharf": 0, "verschleiert": 0, "ohne_datum": 0}

    while True:
        parameter = {
            "taxon_id": tid,
            "nelat": NORD, "nelng": OST, "swlat": SUED, "swlng": WEST,
            "quality_grade": ",".join(STUFEN),
            "geo": "true", "has": "geo",
            "d1": f"{JAHR_VON}-01-01", "d2": f"{JAHR_BIS}-12-31",
            "per_page": 200,
            "order_by": "id", "order": "asc",
            "id_above": letzte_id,
        }
        try:
            antwort = requests.get(f"{BASIS}/observations", params=parameter,
                                   headers=HEADERS, timeout=90)
            daten = antwort.json()
        except Exception as e:
            print("   Fehler:", str(e)[:100])
            break

        treffer = daten.get("results", [])
        if not treffer:
            break

        for t in treffer:
            letzte_id = max(letzte_id, t["id"])

            # Verschleierte Koordinaten sind zufaellig verschoben
            if t.get("obscured") or t.get("geoprivacy") == "obscured":
                verworfen["verschleiert"] += 1
                continue

            datum = (t.get("observed_on") or "")[:10]
            if len(datum) != 10:
                verworfen["ohne_datum"] += 1
                continue

            u = t.get("positional_accuracy")
            if u is not None and u > MAX_UNSICHERHEIT:
                verworfen["unscharf"] += 1
                continue

            ort_text = t.get("geojson", {}).get("coordinates")
            if not ort_text:
                continue
            lon, lat = ort_text[0], ort_text[1]

            zeilen.append({
                "gbif_id": f"inat{t['id']}",
                "datum": datum,
                "lat": round(float(lat), 5),
                "lon": round(float(lon), 5),
                "unsicherheit_m": "" if u is None else u,
                "ort": (t.get("place_guess") or "").replace(",", " ")[:60],
                "stufe": t.get("quality_grade", ""),
            })

        time.sleep(1.0)      # iNaturalist bittet um hoechstens 60/Minute

    return zeilen, verworfen


def lade_vorhandene():
    """Was schon ueber GBIF da ist - fuer den Ueberschneidungsvergleich."""
    vorhanden = set()
    if not os.path.exists(VERGLEICH):
        return vorhanden
    with open(VERGLEICH, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                vorhanden.add((z["art"], z["datum"],
                               round(float(z["lat"]), 3),
                               round(float(z["lon"]), 3)))
            except (ValueError, KeyError):
                continue
    return vorhanden


def main():
    print(f"Gebiet {SUED}-{NORD} Nord, {WEST}-{OST} Ost")
    print(f"Pruefstufen: {', '.join(STUFEN)}\n")

    vorhanden = lade_vorhandene()
    if vorhanden:
        print(f"{len(vorhanden)} Funde bereits ueber GBIF vorhanden\n")

    alle = []
    print(f"{'Art':<18}{'gefunden':>10}{'davon neu':>11}{'research':>10}"
          f"{'needs_id':>10}")

    for schluessel, name in ARTEN.items():
        tid, gefunden = taxon_id(name)
        if tid is None:
            print(f"{schluessel:<18}nicht gefunden")
            continue

        zeilen, verworfen = hole_art(tid)
        for z in zeilen:
            z["art"] = schluessel

        neu = sum(1 for z in zeilen
                  if (schluessel, z["datum"], round(z["lat"], 3),
                      round(z["lon"], 3)) not in vorhanden)
        research = sum(1 for z in zeilen if z["stufe"] == "research")
        needs = sum(1 for z in zeilen if z["stufe"] == "needs_id")

        print(f"{schluessel:<18}{len(zeilen):>10}{neu:>11}"
              f"{research:>10}{needs:>10}")
        alle.extend(zeilen)

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN + ["stufe"])
        writer.writeheader()
        writer.writerows(alle)

    gesamt_neu = sum(1 for z in alle
                     if (z["art"], z["datum"], round(z["lat"], 3),
                         round(z["lon"], 3)) not in vorhanden)

    print(f"\n{len(alle)} Beobachtungen in {DATEI}, davon "
          f"{gesamt_neu} noch nicht in {VERGLEICH}.")
    print()
    print("Zum Zusammenfuegen - erst pruefen, ob sich der Zuwachs lohnt:")
    print("  python funde_zusammenfuegen.py")
    print()
    print("Hinweis: needs_id heisst, dass die Bestimmung noch nicht")
    print("bestaetigt ist. Bei Schwefelporling, Parasol und Pfifferling")
    print("ist das Verwechslungsrisiko gering, beim Sommersteinpilz")
    print("dagegen hoch - er wird oft als Steinpilz gemeldet.")


main()
