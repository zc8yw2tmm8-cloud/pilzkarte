"""
Prueft, ob die STAC-API des LGLN nutzbar ist.

Wenn ja, entfaellt der GeoJSON-Export aus dem Portal - dgm_holen.py
holt die Kachelliste dann selbst.
"""
import requests
import json

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

STAC = "https://dgm.stac.lgln.niedersachsen.de"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

# Kleiner Ausschnitt: Stadtforst Wolfsburg
RECHTECK = "10.75,52.38,10.82,52.43"


def zeige(titel, url, parameter=None):
    print(f"\n=== {titel} ===")
    print(f"   {url}")
    try:
        a = requests.get(url, params=parameter, headers=HEADERS, timeout=90)
    except Exception as e:
        print("   Verbindungsfehler:", str(e)[:120])
        return None

    print(f"   HTTP {a.status_code}")
    if a.status_code != 200:
        print("   ", a.text[:200])
        return None

    try:
        return a.json()
    except Exception:
        print("   Kein JSON:", a.text[:200])
        return None


def main():
    # 1. Wurzel
    d = zeige("Wurzel", STAC)
    if d:
        print(f"   Titel: {d.get('title', '?')}")
        arten = [v.get("rel") for v in d.get("links", [])]
        print(f"   Verweise: {', '.join(sorted(set(a for a in arten if a)))}")

    # 2. Sammlungen
    d = zeige("Sammlungen", f"{STAC}/collections")
    if d:
        for c in d.get("collections", [])[:8]:
            print(f"   {c.get('id')}  -  {str(c.get('title'))[:50]}")

    # 3. Suche im Rechteck
    d = zeige("Suche im Gebiet", f"{STAC}/search",
              {"bbox": RECHTECK, "limit": 5})
    if not d:
        print("\nSuche fehlgeschlagen. Vielleicht anderer Pfad -")
        print("schick mir die Ausgabe von oben.")
        return

    treffer = d.get("features", [])
    print(f"   {len(treffer)} Treffer auf dieser Seite")
    if "numberMatched" in d:
        print(f"   insgesamt: {d['numberMatched']}")

    if not treffer:
        return

    e = treffer[0]
    print(f"\n   Beispielkachel: {e.get('id')}")
    print("   Assets:")
    for name, a in (e.get("assets") or {}).items():
        print(f"     {name}: {str(a.get('href'))[:95]}")
    if e.get("properties"):
        schluessel = list(e["properties"].keys())[:8]
        print(f"   Eigenschaften: {', '.join(schluessel)}")

    print("\n" + "=" * 58)
    print("Wenn hier Kacheln mit .tif-Adressen stehen, kann")
    print("dgm_holen.py die Liste selbst holen - kein Export noetig.")


main()
