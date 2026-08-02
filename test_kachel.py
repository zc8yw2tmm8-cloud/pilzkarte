"""
Laedt EINE Kachel ueber die STAC-API und prueft, ob sie lesbar ist.

Vor dem grossen Lauf. Klaert zwei Fragen: Sind die Adressen ohne
Dateiendung nutzbar, und liefern sie tatsaechlich ein GeoTIFF?
"""
import io
import re
import requests
import numpy as np
from PIL import Image

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

Image.MAX_IMAGE_PIXELS = None

STAC = "https://dgm.stac.lgln.niedersachsen.de"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}
RECHTECK = "10.77,52.40,10.80,52.42"     # Stadtforst Wolfsburg


def main():
    print("Suche eine Kachel ...")
    a = requests.get(f"{STAC}/search", headers=HEADERS, timeout=90,
                     params={"bbox": RECHTECK, "limit": 1})
    treffer = a.json().get("features", [])
    if not treffer:
        print("Keine Kachel gefunden.")
        return

    e = treffer[0]
    print(f"   {e.get('id')}")
    print(f"   Eigenschaften: {e.get('properties')}")

    assets = e.get("assets") or {}
    url = None
    for name, wert in assets.items():
        print(f"\n   Asset '{name}':")
        print(f"     {wert.get('href')}")
        print(f"     Typ laut Angabe: {wert.get('type', '?')}")
        if "metadata" not in name.lower() and url is None:
            url = wert.get("href")

    if not url:
        print("\nKeine brauchbare Adresse.")
        return

    print(f"\nLade herunter ...")
    b = requests.get(url, headers=HEADERS, timeout=300)
    print(f"   HTTP {b.status_code}, {len(b.content)/1024/1024:.1f} MB")
    print(f"   Content-Type: {b.headers.get('Content-Type', '?')}")
    print(f"   Erste Bytes: {b.content[:4]}")

    if b.status_code != 200 or len(b.content) < 10000:
        print("   Zu klein oder Fehler.")
        return

    try:
        bild = Image.open(io.BytesIO(b.content))
        feld = np.array(bild)
        print(f"\n   Bild: {bild.size[0]} x {bild.size[1]}, "
              f"Modus {bild.mode}, Typ {feld.dtype}")
        gueltig = feld[feld > -9000]
        if gueltig.size:
            print(f"   Hoehen: {gueltig.min():.1f} bis "
                  f"{gueltig.max():.1f} m")
            print(f"   Leerwerte: {(feld <= -9000).mean()*100:.1f} %")
        print("\nAlles in Ordnung - dgm_holen.py kann starten.")
    except Exception as ex:
        print(f"\n   Nicht als Bild lesbar: {str(ex)[:120]}")
        print("   Vermutlich ein Archiv. Schick mir die Ausgabe.")


main()
