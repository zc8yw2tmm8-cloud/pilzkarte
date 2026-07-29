import requests
import json

# Gleiche Bounding Box wie waldraster.py
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15

DATEI = "schutzgebiete.geojson"

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

SERVER = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

QUERY = f"""
[out:json][timeout:180];
(
  way["leisure"="nature_reserve"]({SUED},{WEST},{NORD},{OST});
  relation["leisure"="nature_reserve"]({SUED},{WEST},{NORD},{OST});
  way["boundary"="protected_area"]({SUED},{WEST},{NORD},{OST});
  relation["boundary"="protected_area"]({SUED},{WEST},{NORD},{OST});
);
out geom;
"""


def hole_daten():
    for url in SERVER:
        print(f"Versuche {url.split('/')[2]} ...")
        try:
            antwort = requests.post(url, data={"data": QUERY},
                                    headers=HEADERS, timeout=300)
        except Exception as e:
            print("  Verbindungsfehler:", e)
            continue

        if antwort.status_code != 200:
            print(f"  HTTP {antwort.status_code}: {antwort.text[:150]}")
            continue

        try:
            return antwort.json()
        except Exception:
            print("  Kein JSON:", antwort.text[:200])

    return None


def einstufung(tags):
    """streng = Sammeln verboten, mild = meist erlaubt."""
    pc = tags.get("protect_class", "")
    grenze = tags.get("boundary", "")
    leisure = tags.get("leisure", "")

    # Nationalpark, Naturschutzgebiet, Naturdenkmal
    if pc in ("1", "2", "3", "4"):
        return "streng"
    if leisure == "nature_reserve" and pc == "":
        return "streng"
    if grenze == "national_park":
        return "streng"

    # Landschaftsschutz, Natura2000, Biosphaerenreservat
    return "mild"


def ring_zu_koordinaten(geometry):
    """OSM-Geometrie in GeoJSON-Reihenfolge: [lon, lat]"""
    return [[p["lon"], p["lat"]] for p in geometry]


def main():
    daten = hole_daten()
    if daten is None:
        print("Abfrage fehlgeschlagen.")
        return

    features = []
    zaehler = {"streng": 0, "mild": 0}

    for element in daten.get("elements", []):
        tags = element.get("tags", {})
        stufe = einstufung(tags)
        name = tags.get("name", "ohne Namen")

        ringe = []

        if element.get("type") == "way" and "geometry" in element:
            ring = ring_zu_koordinaten(element["geometry"])
            if len(ring) >= 4:
                ringe.append(ring)

        elif element.get("type") == "relation":
            for member in element.get("members", []):
                if member.get("role") == "outer" and "geometry" in member:
                    ring = ring_zu_koordinaten(member["geometry"])
                    if len(ring) >= 4:
                        ringe.append(ring)

        for ring in ringe:
            # Polygon muss geschlossen sein
            if ring[0] != ring[-1]:
                ring.append(ring[0])

            features.append({
                "type": "Feature",
                "properties": {
                    "name": name,
                    "stufe": stufe,
                    "art": tags.get("protection_title", tags.get("leisure", "")),
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]}
            })
            zaehler[stufe] += 1

    geojson = {"type": "FeatureCollection", "features": features}

    with open(DATEI, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"\n{len(features)} Flaechen gespeichert.")
    print(f"  streng (Sammeln verboten): {zaehler['streng']}")
    print(f"  mild (meist erlaubt): {zaehler['mild']}")


main()