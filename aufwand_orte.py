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


def sauberes_datum(rohtext):
    """
    GBIF liefert das Datum in verschiedenen Formen, teils als
    Zeitraum ("2024-09-01/2024-09-30"). Nur eindeutige Tagesangaben
    sind brauchbar.
    """
    if not rohtext:
        return None
    text = str(rohtext).strip()
    if "/" in text:
        return None
    text = text[:10]
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        return None
    try:
        from datetime import date
        date.fromisoformat(text)
    except ValueError:
        return None
    return text


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

    # WICHTIG: Genauso zusammenfassen wie funde_wetter2.py, sonst
    # sind Funde und Hintergrund nicht vergleichbar.
    #
    # Bisher stand hier jede einzelne Meldung. Ein beliebter
    # Waldrand mit 50 Meldungen zaehlte damit 50-fach, ein Fundort
    # mit drei Meldungen am selben Tag nur einfach - beliebte Orte
    # waren im Nenner ueberrepraesentiert und haben die
    # Auswahlverhaeltnisse nach unten gedrueckt.
    #
    # Schluessel: (Datum, Ort auf etwa 110 m). Dasselbe Raster wie
    # bei den Funden.
    gesehen = set()

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
            datum = sauberes_datum(t.get("eventDate"))
            if datum is None:
                verworfen += 1
                continue

            lat = round(t["decimalLatitude"], 5)
            lon = round(t["decimalLongitude"], 5)

            schluessel = (datum, round(lat, 3), round(lon, 3))
            if schluessel in gesehen:
                verworfen += 1
                continue
            gesehen.add(schluessel)

            zeilen.append({
                "gbif_id": t.get("key"),
                "lat": lat,
                "lon": lon,
                # Datum statt nur Jahr: Baum- und Bodenvergleich
                # koennen damit auf die Kernmonate der jeweiligen
                # Art eingegrenzt werden. Wer im Fruehjahr andere
                # Waelder besucht als im Herbst, verzerrt sonst den
                # Vergleich.
                "datum": datum,
                "monat": int(datum[5:7]),
                "jahr": int(datum[:4]),
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
        writer = csv.DictWriter(
            f, fieldnames=["gbif_id", "lat", "lon", "datum",
                           "monat", "jahr"])
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\n{len(zeilen)} Meldeorte in {DATEI}.")
    print(f"{verworfen} verworfen (ungenau, ohne Datum oder Dublette).")

    from collections import Counter
    nach_monat = Counter(z["monat"] for z in zeilen)
    print("\nVerteilung ueber das Jahr:")
    for m in range(1, 13):
        n = nach_monat.get(m, 0)
        balken = "#" * round(n / max(1, max(nach_monat.values())) * 30)
        print(f"  {m:>2}  {n:>6}  {balken}")
    if verworfen:
        print(f"{verworfen} wegen ungenauer Koordinaten verworfen.")
    print("\nWeiter mit: python baumarten_kalibrieren.py")


main()
