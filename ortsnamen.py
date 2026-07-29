"""
Gibt jedem Waldpunkt einen lesbaren Namen.

Zwei Quellen aus OpenStreetMap, in EINER Overpass-Abfrage je Art:
  1. Namen von Waldflaechen  -> "Elm", "Barnbruch", "Lappwald"
  2. Namen von Ortschaften   -> "Wald bei Velpke, 2.1 km"

Liegt ein Punkt in einem benannten Wald, gewinnt dieser Name.
Sonst wird die naechste Ortschaft genannt.

Laeuft EINMAL. Ergebnis: ortsnamen.csv
"""
import requests
import csv
import math
import time

SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15

PUNKTE_DATEI = "waldpunkte.csv"
DATEI = "ortsnamen.csv"

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}
SERVER = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

WALD_QUERY = f"""
[out:json][timeout:180];
(
  way["landuse"="forest"]["name"]({SUED},{WEST},{NORD},{OST});
  way["natural"="wood"]["name"]({SUED},{WEST},{NORD},{OST});
  relation["landuse"="forest"]["name"]({SUED},{WEST},{NORD},{OST});
  relation["natural"="wood"]["name"]({SUED},{WEST},{NORD},{OST});
);
out geom;
"""

ORT_QUERY = f"""
[out:json][timeout:120];
(
  node["place"~"^(city|town|village|hamlet|suburb|isolated_dwelling)$"]
      ({SUED},{WEST},{NORD},{OST});
);
out;
"""


def frage(query):
    for url in SERVER:
        print(f"  Versuche {url.split('/')[2]} ...")
        try:
            antwort = requests.post(url, data={"data": query},
                                    headers=HEADERS, timeout=300)
        except Exception as e:
            print("   Verbindungsfehler:", e)
            continue

        if antwort.status_code != 200:
            print(f"   HTTP {antwort.status_code}")
            time.sleep(5)
            continue

        try:
            return antwort.json()
        except Exception:
            print("   Kein JSON:", antwort.text[:150])
    return None


def punkt_in_polygon(lat, lon, ring):
    drin = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        lat_i, lon_i = ring[i]
        lat_j, lon_j = ring[j]
        if (lon_i > lon) != (lon_j > lon):
            schnitt = (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i
            if lat < schnitt:
                drin = not drin
        j = i
    return drin


def kasten(ring):
    lats = [p[0] for p in ring]
    lons = [p[1] for p in ring]
    return min(lats), min(lons), max(lats), max(lons)


def entfernung_km(lat1, lon1, lat2, lon2):
    dlat = (lat2 - lat1) * 111.0
    dlon = (lon2 - lon1) * 111.0 * math.cos(math.radians(lat1))
    return math.sqrt(dlat * dlat + dlon * dlon)


def hole_waelder():
    print("Waldnamen abfragen ...")
    daten = frage(WALD_QUERY)
    if daten is None:
        return []

    waelder = []
    for e in daten.get("elements", []):
        name = e.get("tags", {}).get("name")
        if not name:
            continue

        ringe = []
        if e.get("type") == "way" and "geometry" in e:
            ringe.append([(p["lat"], p["lon"]) for p in e["geometry"]])
        elif e.get("type") == "relation":
            for m in e.get("members", []):
                if m.get("role") == "outer" and "geometry" in m:
                    ringe.append([(p["lat"], p["lon"]) for p in m["geometry"]])

        for ring in ringe:
            if len(ring) >= 3:
                waelder.append((name, ring, kasten(ring)))

    namen = {w[0] for w in waelder}
    print(f"  {len(waelder)} benannte Flaechen, {len(namen)} verschiedene Namen")
    return waelder


def hole_orte():
    print("Ortsnamen abfragen ...")
    daten = frage(ORT_QUERY)
    if daten is None:
        return []

    orte = []
    for e in daten.get("elements", []):
        name = e.get("tags", {}).get("name")
        if name and e.get("lat") is not None:
            orte.append((name, e["lat"], e["lon"]))

    print(f"  {len(orte)} Ortschaften")
    return orte


def main():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))

    waelder = hole_waelder()
    orte = hole_orte()

    if not waelder and not orte:
        print("Keine Daten erhalten. Spaeter nochmal versuchen.")
        return

    print(f"\nOrdne {len(punkte)} Punkten Namen zu ...")
    zeilen = []
    mit_wald = 0

    for kennung, lat, lon in punkte:
        waldname = ""
        for name, ring, (mlat, mlon, xlat, xlon) in waelder:
            if not (mlat <= lat <= xlat and mlon <= lon <= xlon):
                continue
            if punkt_in_polygon(lat, lon, ring):
                waldname = name
                break

        ortname = ""
        abstand = ""
        if orte:
            beste = min(orte, key=lambda o: entfernung_km(lat, lon, o[1], o[2]))
            ortname = beste[0]
            abstand = round(entfernung_km(lat, lon, beste[1], beste[2]), 1)

        if waldname:
            mit_wald += 1
            titel = waldname
            if ortname:
                titel += f" bei {ortname}"
        elif ortname:
            titel = f"Wald bei {ortname}"
        else:
            titel = kennung

        zeilen.append({
            "id": kennung, "titel": titel, "wald": waldname,
            "ort": ortname, "abstand_km": abstand,
        })

    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "titel", "wald", "ort", "abstand_km"])
        writer.writeheader()
        writer.writerows(zeilen)

    print(f"\n{len(zeilen)} Namen in {DATEI}.")
    print(f"{mit_wald} Punkte liegen in einem benannten Wald.")

    from collections import Counter
    haeufig = Counter(z["wald"] for z in zeilen if z["wald"])
    if haeufig:
        print("\nGroesste benannte Waelder:")
        for name, n in haeufig.most_common(12):
            print(f"  {n:4d} Zellen  {name}")


main()
