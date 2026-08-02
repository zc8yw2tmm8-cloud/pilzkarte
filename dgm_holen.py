"""
Laedt die DGM1-Hoehenkacheln fuer die Gebiete aus gebiete.py.

Geladen wird nur, was Wald beruehrt - das halbiert die Menge. Die
Waldflaechen kommen aus baumarten.csv, ersatzweise aus waldpunkte.csv.

Braucht die Blattschnittuebersicht des OpenGeoData-Portals
Niedersachsen, exportiert als GeoJSON und abgelegt als
uebersicht.geojson.

Kacheln landen je Gebiet in einem eigenen Ordner:
    dgm/wolfsburg/  dgm/elm/  ...

Vorhandene werden uebersprungen. Abbruch mit Strg+C kostet nichts.
"""
import os
import re
import csv
import json
import math
import time
import requests
from concurrent.futures import ThreadPoolExecutor

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import gebiete

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}
ORDNER = "dgm"
ARBEITER = 3

# Wie weit um einen Waldpunkt herum Kacheln geholt werden, in km
NAEHE_KM = 1.2

QUELLEN = ["uebersicht.geojson", "uebersicht.json", "uebersicht.csv"]

# Das LGLN bietet eine STAC-API an - der saubere Weg. STAC ist ein
# Standard, um Rasterdaten nach Ort und Zeit zu durchsuchen. Damit
# entfaellt der Umweg ueber den GeoJSON-Export aus dem Portal.
STAC = "https://dgm.stac.lgln.niedersachsen.de"


def utm_zu_wgs84(ost, nord, zone=32):
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    x, y = ost - 500000.0, nord
    mu = (y / k0) / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu))
    n1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = e2 / (1 - e2) * math.cos(phi1) ** 2
    r1 = a * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * k0)
    breite = phi1 - (n1 * math.tan(phi1) / r1) * (
        d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2
                      - 9 * e2 / (1 - e2)) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2
           - 252 * e2 / (1 - e2) - 3 * c1 ** 2) * d ** 6 / 720)
    laenge = (d - (1 + 2 * t1 + c1) * d ** 3 / 6
              + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * e2 / (1 - e2)
                 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(phi1)
    return (math.degrees(breite),
            (zone - 1) * 6 - 180 + 3 + math.degrees(laenge))


def wgs84_zu_utm(lat, lon):
    """Numerisch invertiert - genau genug fuer Kachelnamen."""
    e, n = 600000.0, 5800000.0
    for _ in range(40):
        b, l = utm_zu_wgs84(e, n)
        n += (lat - b) * 111000
        e += (lon - l) * 111000 * math.cos(math.radians(lat))
    return e, n


def stac_suche(g):
    """
    Fragt die STAC-API nach den Kacheln eines Gebiets.

    Rueckgabe: {(ost_km, nord_km): url} oder None, wenn der Dienst
    nicht antwortet.
    """
    rechteck = [g["west"], g["sued"], g["ost"], g["nord"]]
    gefunden = {}
    naechste = None
    seiten = 0

    while seiten < 60:
        try:
            if naechste:
                antwort = requests.get(naechste, headers=HEADERS, timeout=90)
            else:
                antwort = requests.get(
                    f"{STAC}/search", headers=HEADERS, timeout=90,
                    params={"bbox": ",".join(str(x) for x in rechteck),
                            "limit": 200})
            if antwort.status_code != 200:
                return None
            daten = antwort.json()
        except Exception:
            return None

        eintraege = daten.get("features", [])
        if not eintraege and not gefunden:
            return None

        for e in eintraege:
            # Das Bild-Asset heisst beim LGLN "dgm1-tif". Die Adresse
            # traegt dort keine Dateiendung, deshalb wird nach dem
            # Namen gesucht und nicht nach ".tif".
            eintraege_assets = e.get("assets") or {}
            url = None
            for name in ("dgm1-tif", "data", "image", "tif"):
                if name in eintraege_assets:
                    url = eintraege_assets[name].get("href")
                    break
            if url is None:
                # Alles ausser den Metadaten nehmen
                for name, a in eintraege_assets.items():
                    if "metadata" in name.lower():
                        continue
                    href = a.get("href")
                    if href:
                        url = href
                        break
            if not url:
                continue

            # Kachelkoordinate aus der Kennung, etwa
            # "dgm1_32_623_5810_1_ni_2020" -> Ost 623, Nord 5810
            text = str(e.get("id", "")) + " " + url
            zahlen = re.findall(r"(?<!\d)(\d{3,4})(?!\d)", text)
            for i in range(len(zahlen) - 1):
                o, n = int(zahlen[i]), int(zahlen[i + 1])
                if 280 <= o <= 920 and 5230 <= n <= 6110:
                    gefunden[(o, n)] = url
                    break

        naechste = None
        for verweis in daten.get("links", []):
            if verweis.get("rel") == "next":
                naechste = verweis.get("href")
                break
        if not naechste:
            break
        seiten += 1

    return gefunden or None


def finde_uebersicht():
    for name in QUELLEN:
        if os.path.exists(name):
            return name
    return None


def lade_verzeichnis(pfad):
    """Kachelkoordinate -> Download-Adresse."""
    if pfad.lower().endswith(".csv"):
        with open(pfad, "r", encoding="utf-8-sig") as f:
            eintraege = [dict(z) for z in csv.DictReader(f)]
    else:
        with open(pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)
        eintraege = ([x.get("properties", {}) or {} for x in daten["features"]]
                     if isinstance(daten, dict) and "features" in daten
                     else daten)

    verzeichnis = {}
    for e in eintraege:
        url = None
        for wert in e.values():
            text = str(wert)
            if text.startswith("http"):
                url = text
                if text.lower().endswith((".tif", ".tiff", ".zip")):
                    break
        if not url:
            continue
        for wert in e.values():
            zahlen = re.findall(r"(?<!\d)(\d{3,4})(?!\d)", str(wert))
            gefunden = False
            for i in range(len(zahlen) - 1):
                o, n = int(zahlen[i]), int(zahlen[i + 1])
                if 280 <= o <= 920 and 5230 <= n <= 6110:
                    verzeichnis[(o, n)] = url
                    gefunden = True
                    break
            if gefunden:
                break
    return verzeichnis


def waldkacheln():
    """
    Kacheln, die Wald beruehren.

    Bevorzugt baumarten.csv, weil dort der Waldanteil steht.
    Ersatzweise waldpunkte.csv.
    """
    punkte = []

    if os.path.exists("baumarten.csv"):
        with open("baumarten.csv", "r", encoding="utf-8") as f:
            for z in csv.DictReader(f):
                try:
                    anteil = float(z.get("waldanteil") or 0)
                except ValueError:
                    anteil = 0
                if anteil >= 0.05:
                    punkte.append((float(z["lat"]), float(z["lon"])))
    elif os.path.exists("waldpunkte.csv"):
        with open("waldpunkte.csv", "r", encoding="utf-8") as f:
            for z in csv.DictReader(f):
                punkte.append((float(z["lat"]), float(z["lon"])))
    else:
        return None

    spanne = int(math.ceil(NAEHE_KM))
    kacheln = set()
    for lat, lon in punkte:
        e, n = wgs84_zu_utm(lat, lon)
        ko, kn = int(e // 1000), int(n // 1000)
        for do in range(-spanne, spanne + 1):
            for dn in range(-spanne, spanne + 1):
                kacheln.add((ko + do, kn + dn))
    return kacheln


def gebietskacheln(g):
    """Alle Kachelkoordinaten im Rechteck eines Gebiets."""
    ecken = [(g["sued"], g["west"]), (g["sued"], g["ost"]),
             (g["nord"], g["west"]), (g["nord"], g["ost"])]
    utm = [wgs84_zu_utm(a, b) for a, b in ecken]
    o0 = int(min(p[0] for p in utm) // 1000)
    o1 = int(max(p[0] for p in utm) // 1000) + 1
    n0 = int(min(p[1] for p in utm) // 1000)
    n1 = int(max(p[1] for p in utm) // 1000) + 1
    return {(o, n) for o in range(o0, o1 + 1) for n in range(n0, n1 + 1)}


def hole_kachel(url, ziel):
    """
    Laedt eine Kachel. Die STAC-Adressen tragen keine Endung -
    entscheidend ist der Inhalt, nicht der Name.
    """
    for versuch in range(3):
        try:
            a = requests.get(url, headers=HEADERS, timeout=300)
            if a.status_code == 200 and len(a.content) > 10000:
                # TIFF beginnt mit "II*" oder "MM*", ZIP mit "PK"
                kopf = a.content[:4]
                if kopf[:2] == b"PK":
                    ziel = ziel.replace(".tif", ".zip")
                with open(ziel, "wb") as f:
                    f.write(a.content)
                return True
        except Exception:
            pass
        time.sleep(2 * (versuch + 1))
    return False


def main():
    # Erst die STAC-API versuchen - dann braucht es keinen Export
    print(f"Frage {STAC} ab ...")
    verzeichnis = {}
    stac_ok = True

    for schluessel, g in gebiete.aktive().items():
        teil = stac_suche(g)
        if teil is None:
            stac_ok = False
            break
        verzeichnis.update(teil)
        print(f"  {g['name']}: {len(teil)} Kacheln")

    if stac_ok and verzeichnis:
        print(f"\n{len(verzeichnis)} Kacheln ueber die STAC-API\n")
    else:
        print("  STAC-API antwortet nicht wie erwartet.\n")
        pfad = finde_uebersicht()
        if pfad is None:
            print("Und keine Uebersichtsdatei gefunden.")
            print("Entweder spaeter nochmal versuchen, oder im")
            print("OpenGeoData-Portal als GeoJSON exportieren und als")
            print("uebersicht.geojson hier ablegen.")
            return
        print(f"Rueckfall auf {pfad} ...")
        verzeichnis = lade_verzeichnis(pfad)
        print(f"{len(verzeichnis)} Kacheln mit Download-Adresse\n")

    wald = waldkacheln()
    if wald is None:
        print("Weder baumarten.csv noch waldpunkte.csv gefunden -")
        print("es werden alle Kacheln geladen.")
    else:
        print(f"{len(wald)} Kacheln beruehren Wald "
              f"(Umkreis {NAEHE_KM} km)\n")

    plan = []
    print(f"{'Gebiet':<16}{'im Rechteck':>12}{'mit Wald':>10}"
          f"{'fehlen':>8}{'MB':>7}")

    for schluessel, g in gebiete.aktive().items():
        alle = gebietskacheln(g)
        noetig = sorted(k for k in alle
                        if k in verzeichnis and (wald is None or k in wald))

        ziel = os.path.join(ORDNER, schluessel)
        vorhanden = set()
        if os.path.isdir(ziel):
            for d in os.listdir(ziel):
                zahlen = re.findall(r"(?<!\d)(\d{3,4})(?!\d)", d)
                for i in range(len(zahlen) - 1):
                    o, n = int(zahlen[i]), int(zahlen[i + 1])
                    if 280 <= o <= 920 and 5230 <= n <= 6110:
                        vorhanden.add((o, n))
                        break

        fehlen = [k for k in noetig if k not in vorhanden]
        print(f"{schluessel:<16}{len(alle):>12}{len(noetig):>10}"
              f"{len(fehlen):>8}{len(fehlen)*1.6:>7.0f}")
        plan.append((schluessel, g, ziel, fehlen))

    gesamt = sum(len(f) for _, _, _, f in plan)
    if gesamt == 0:
        print("\nAlles vorhanden. Weiter mit: python relief.py")
        return

    print(f"\n{gesamt} Kacheln zu laden, etwa {gesamt*1.6/1024:.1f} GB.")
    print(f"Geschaetzt {gesamt*1.5/ARBEITER/60:.0f} Minuten.")
    if input("Starten? (j/n) ").strip().lower()[:1] != "j":
        return

    for schluessel, g, ziel, fehlen in plan:
        if not fehlen:
            continue
        os.makedirs(ziel, exist_ok=True)
        print(f"\n=== {g['name']} ({len(fehlen)} Kacheln) ===")

        beginn = time.time()
        erledigt = [0]
        fehler = [0]

        def eine(k):
            o, n = k
            url = verzeichnis[k]
            endung = ".zip" if url.lower().endswith(".zip") else ".tif"
            datei = os.path.join(ziel, f"dgm1_32_{o}_{n}_1_ni{endung}")
            ok = hole_kachel(url, datei)
            erledigt[0] += 1
            if not ok:
                fehler[0] += 1
            if erledigt[0] % 20 == 0 or erledigt[0] == len(fehlen):
                dauer = time.time() - beginn
                rest = (len(fehlen) - erledigt[0]) / max(
                    erledigt[0] / max(dauer, 0.1), 0.01) / 60
                print(f"  {erledigt[0]} von {len(fehlen)}, "
                      f"noch ~{rest:.0f} min, {fehler[0]} Fehler")
            return ok

        with ThreadPoolExecutor(max_workers=ARBEITER) as pool:
            list(pool.map(eine, fehlen))

    zips = []
    for schluessel, _, ziel, _ in plan:
        if os.path.isdir(ziel):
            zips += [d for d in os.listdir(ziel) if d.endswith(".zip")]
    if zips:
        print(f"\n{len(zips)} ZIP-Archive - entpacken, die TIFFs muessen")
        print("flach im jeweiligen Gebietsordner liegen.")

    print("\nWeiter mit: python relief.py")


main()
