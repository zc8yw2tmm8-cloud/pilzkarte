import requests

# Kleiner Ausschnitt: Elm und Umgebung
SUED, WEST, NORD, OST = 52.10, 10.70, 52.30, 11.10

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

SERVER = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

QUERY = f"""
[out:json][timeout:120];
(
  way["landuse"="forest"]({SUED},{WEST},{NORD},{OST});
  way["natural"="wood"]({SUED},{WEST},{NORD},{OST});
);
out tags;
"""

daten = None
for url in SERVER:
    print(f"Versuche {url.split('/')[2]} ...")
    try:
        antwort = requests.post(url, data={"data": QUERY},
                                headers=HEADERS, timeout=180)
    except Exception as e:
        print("  Verbindungsfehler:", e)
        continue

    if antwort.status_code != 200:
        print(f"  HTTP {antwort.status_code}: {antwort.text[:200]}")
        continue

    try:
        daten = antwort.json()
        break
    except Exception:
        print("  Kein JSON:", antwort.text[:300])

if daten is None:
    print("Alle Server fehlgeschlagen.")
    raise SystemExit

elemente = daten.get("elements", [])
print(f"\n{len(elemente)} Waldflaechen im Testgebiet\n")

if not elemente:
    raise SystemExit

zaehler = {}
beispiel_tags = {}

for e in elemente:
    tags = e.get("tags", {})
    lt = tags.get("leaf_type", "FEHLT")
    zaehler[lt] = zaehler.get(lt, 0) + 1

    for k in tags.keys():
        beispiel_tags[k] = beispiel_tags.get(k, 0) + 1

print("leaf_type Verteilung:")
for wert, anzahl in sorted(zaehler.items(), key=lambda x: -x[1]):
    anteil = anzahl / len(elemente) * 100
    print(f"  {wert}: {anzahl}  ({round(anteil, 1)} %)")

print("\nHaeufigste Tags insgesamt:")
for k, v in sorted(beispiel_tags.items(), key=lambda x: -x[1])[:15]:
    print(f"  {k}: {v}")