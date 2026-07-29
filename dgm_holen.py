"""
Liest die Blattschnittuebersicht des DGM1 und laedt die Kacheln
fuer ein Gebiet herunter.

Die Uebersicht kommt aus dem OpenGeoData-Portal Niedersachsen als
GeoJSON oder CSV. Darin steht je Kachel eine Download-Adresse.
Dieses Skript sucht sie, filtert auf das Gebiet und holt die Dateien.

Ablegen als uebersicht.geojson (oder .csv) neben diesem Skript.
Ergebnis: die GeoTIFF-Kacheln im Ordner dgm/
"""
import os
import re
import csv
import json
import time
import requests

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}
ORDNER = "dgm"

# Gesuchtes Gebiet in UTM32-Kilometern.
# Voreinstellung: Stadtforst Wolfsburg und Hasselbachtal.
OST_VON, OST_BIS = 619, 623
NORD_VON, NORD_BIS = 5805, 5809

QUELLEN = ["uebersicht.geojson", "uebersicht.json",
           "uebersicht.csv", "blattschnitt.geojson"]


def finde_datei():
    for name in QUELLEN:
        if os.path.exists(name):
            return name
    treffer = [d for d in os.listdir(".")
               if d.lower().endswith((".geojson", ".csv"))
               and "wetter" not in d.lower() and "funde" not in d.lower()
               and "boden" not in d.lower() and "wald" not in d.lower()
               and "baumarten" not in d.lower() and "hoehen" not in d.lower()
               and "klassen" not in d.lower() and "ortsnamen" not in d.lower()
               and "hintergrund" not in d.lower() and "aufwand" not in d.lower()]
    return treffer[0] if treffer else None


def lade_eintraege(pfad):
    """Gibt eine Liste von dicts zurueck - egal ob GeoJSON oder CSV."""
    if pfad.lower().endswith(".csv"):
        with open(pfad, "r", encoding="utf-8-sig") as f:
            return [dict(z) for z in csv.DictReader(f)]

    with open(pfad, "r", encoding="utf-8") as f:
        daten = json.load(f)

    if isinstance(daten, dict) and "features" in daten:
        return [f.get("properties", {}) or {} for f in daten["features"]]
    if isinstance(daten, list):
        return daten
    return []


def finde_url(eintrag):
    for wert in eintrag.values():
        text = str(wert)
        if text.startswith("http") and text.lower().endswith(
                (".tif", ".tiff", ".zip")):
            return text
    for wert in eintrag.values():
        text = str(wert)
        if text.startswith("http"):
            return text
    return None


def finde_kachel(eintrag):
    """Sucht die UTM-Kilometerangaben in irgendeinem Feld."""
    for wert in eintrag.values():
        text = str(wert)
        zahlen = re.findall(r"(?<!\d)(\d{3,4})(?!\d)", text)
        for i in range(len(zahlen) - 1):
            ost, nord = int(zahlen[i]), int(zahlen[i + 1])
            if 280 <= ost <= 920 and 5230 <= nord <= 6110:
                return ost, nord
    return None


def main():
    pfad = finde_datei()
    if pfad is None:
        print("Keine Uebersichtsdatei gefunden.")
        print("Exportiere im Portal als GeoJSON und lege die Datei als")
        print("uebersicht.geojson neben dieses Skript.")
        return

    print(f"Lese {pfad} ...")
    eintraege = lade_eintraege(pfad)
    print(f"{len(eintraege)} Eintraege\n")

    if not eintraege:
        print("Datei enthaelt keine lesbaren Eintraege.")
        return

    print("Felder im ersten Eintrag:")
    for schluessel, wert in list(eintraege[0].items())[:15]:
        kurz = str(wert)[:80]
        print(f"   {schluessel}: {kurz}")
    print()

    gesucht = []
    ohne_url = 0
    ohne_kachel = 0

    for e in eintraege:
        kachel = finde_kachel(e)
        if kachel is None:
            ohne_kachel += 1
            continue
        ost, nord = kachel
        if not (OST_VON <= ost <= OST_BIS and NORD_VON <= nord <= NORD_BIS):
            continue
        url = finde_url(e)
        if url is None:
            ohne_url += 1
            continue
        gesucht.append((ost, nord, url))

    if not gesucht:
        print(f"Keine passende Kachel gefunden.")
        print(f"Gesucht: Ost {OST_VON}-{OST_BIS}, "
              f"Nord {NORD_VON}-{NORD_BIS}")
        if ohne_kachel:
            print(f"{ohne_kachel} Eintraege ohne erkennbare UTM-Angabe")
        if ohne_url:
            print(f"{ohne_url} passende Kacheln ohne Download-Adresse")
        print("\nSchick mir die Feldliste von oben, dann passe ich das an.")
        return

    print(f"{len(gesucht)} Kacheln im Gebiet\n")
    os.makedirs(ORDNER, exist_ok=True)

    geladen = 0
    for i, (ost, nord, url) in enumerate(sorted(gesucht), start=1):
        endung = ".zip" if url.lower().endswith(".zip") else ".tif"
        ziel = os.path.join(ORDNER, f"dgm1_32_{ost}_{nord}_1_ni{endung}")

        if os.path.exists(ziel) and os.path.getsize(ziel) > 10000:
            print(f"  {i}/{len(gesucht)}  {ost}_{nord}  schon da")
            geladen += 1
            continue

        try:
            antwort = requests.get(url, headers=HEADERS, timeout=300)
            if antwort.status_code != 200 or len(antwort.content) < 10000:
                print(f"  {i}/{len(gesucht)}  {ost}_{nord}  "
                      f"fehlgeschlagen (HTTP {antwort.status_code})")
                continue
            with open(ziel, "wb") as f:
                f.write(antwort.content)
            mb = len(antwort.content) / 1024 / 1024
            print(f"  {i}/{len(gesucht)}  {ost}_{nord}  {round(mb, 1)} MB")
            geladen += 1
        except Exception as e:
            print(f"  {i}/{len(gesucht)}  {ost}_{nord}  {str(e)[:70]}")

        time.sleep(0.5)

    print(f"\n{geladen} von {len(gesucht)} Kacheln in {ORDNER}/")

    zips = [d for d in os.listdir(ORDNER) if d.endswith(".zip")]
    if zips:
        print(f"\n{len(zips)} Dateien sind ZIP-Archive - entpacke sie,")
        print(f"die TIFFs muessen flach in {ORDNER}/ liegen.")

    print("\nWeiter mit:  python relief.py")


main()