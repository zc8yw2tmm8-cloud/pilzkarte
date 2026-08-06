"""
Findet Waldzellen, die im bisherigen Raster fehlen.

Das erste Raster hat nur Zellen aufgenommen, deren Mittelpunkt in
einem Waldpolygon liegt. Waelder, die zwischen zwei Mittelpunkten
liegen oder nur einen Zellrand streifen, fallen dadurch heraus.

Dieses Skript geht das Gitter vollstaendig durch und fragt fuer jede
noch fehlende Zelle bei OpenStreetMap nach, ob dort Wald ist. Neue
Punkte werden an waldpunkte.csv angehaengt - vorhandene bleiben
unberuehrt, damit die gesammelte Wetterhistorie erhalten bleibt.

Danach fehlen den neuen Punkten alle Begleitdaten. Die Reihenfolge:
    python waldraster_ergaenzen.py
    python nachfuellen.py       (90 Tage Wetter, dauert)
    python baumarten.py
    python bodendaten.py
    python hoehen.py
    python ortsnamen.py
"""
import os
import csv
import math
import time
import requests

SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
RASTER_KM = 2.0

DATEI = "waldpunkte.csv"
STAND = "waldraster_stand.csv"

# ALLE fehlenden Zellen aufnehmen, auch solche ohne Wald?
#
# True:  lueckenloses Rechteck. Sinnvoll, wenn die Karte die ganze
#        Region abdecken soll - Pilze wachsen auch auf Wiesen,
#        Wegraendern und brachliegenden Flaechen, und der Nutzer
#        kann selbst entscheiden, wo er sucht.
# False: nur Zellen mit Wald. Spart Abfragen und Daten.
#
# Hinweis: Dieses Skript prueft nur, OB Wald da ist, nicht WIE VIEL.
# In Niedersachsen enthaelt fast jede 2-km-Zelle irgendein
# Feldgehoelz - der Unterschied zwischen True und False ist deshalb
# gering.
ALLE_ZELLEN = True

OVERPASS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

# Wie viele Zellen je Abfrage. Zu viele lassen den Dienst ablaufen.
BLOCK = 30


def gitter():
    """Alle moeglichen Zellmittelpunkte im Gebiet."""
    schritt_lat = RASTER_KM / 111.0
    mitte = (SUED + NORD) / 2
    schritt_lon = RASTER_KM / (111.0 * math.cos(math.radians(mitte)))

    punkte = []
    lat = SUED + schritt_lat / 2
    while lat < NORD:
        lon = WEST + schritt_lon / 2
        while lon < OST:
            punkte.append((round(lat, 5), round(lon, 5)))
            lon += schritt_lon
        lat += schritt_lat
    return punkte, schritt_lat, schritt_lon


def vorhandene():
    """
    Die schon erfassten Punkte.

    Verglichen wird ueber den Abstand, nicht ueber gerundete
    Koordinaten: Die vorhandenen Punkte stammen aus einem frueheren
    Lauf und liegen minimal versetzt zum neu gerechneten Gitter.
    """
    if not os.path.exists(DATEI):
        return [], 0
    with open(DATEI, "r", encoding="utf-8") as f:
        zeilen = list(csv.DictReader(f))
    return ([(float(z["lat"]), float(z["lon"])) for z in zeilen],
            len(zeilen))


def hoechste_nummer():
    """Die hoechste vergebene Kennung, damit keine doppelt entsteht."""
    if not os.path.exists(DATEI):
        return -1
    hoechste = -1
    with open(DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            ziffern = "".join(c for c in z["id"] if c.isdigit())
            if ziffern:
                hoechste = max(hoechste, int(ziffern))
    return hoechste


def ist_neu(lat, lon, alte, d_lat, d_lon):
    """Liegt in der Naehe schon ein Punkt?"""
    for a, b in alte:
        if abs(a - lat) < d_lat * 0.5 and abs(b - lon) < d_lon * 0.5:
            return False
    return True


def frage_block(zellen, d_lat, d_lon):
    """
    Fragt fuer einen Block von Zellen auf einmal, wo Wald liegt.

    Eine Abfrage je Zelle waere zu langsam - Overpass braucht pro
    Anfrage mehrere Sekunden, unabhaengig von der Groesse. Deshalb
    wird ein umschliessendes Rechteck geholt und die Zuordnung
    danach oertlich gerechnet.

    Rueckgabe: Menge der Indizes mit Wald, oder None bei Fehler.
    """
    sued = min(z[0] for z in zellen) - d_lat
    nord = max(z[0] for z in zellen) + d_lat
    west = min(z[1] for z in zellen) - d_lon
    ost = max(z[1] for z in zellen) + d_lon

    abfrage = (
        f"[out:json][timeout:90];"
        f'(way["landuse"="forest"]({sued},{west},{nord},{ost});'
        f'way["natural"="wood"]({sued},{west},{nord},{ost}););'
        f"out geom;")

    for dienst in OVERPASS:
        try:
            print(f"    frage {dienst.split('/')[2]} ...", flush=True)
            a = requests.post(dienst, data={"data": abfrage},
                              headers=HEADERS, timeout=120)
            if a.status_code != 200:
                print(f"    HTTP {a.status_code}", flush=True)
                continue

            elemente = a.json().get("elements", [])
            print(f"    {len(elemente)} Waldflaechen erhalten", flush=True)

            # Alle Eckpunkte der Waldflaechen einsammeln
            ecken = []
            for e in elemente:
                for p in e.get("geometry") or []:
                    if p.get("lat") is not None:
                        ecken.append((p["lat"], p["lon"]))

            # Welche Zelle enthaelt mindestens einen Eckpunkt?
            mit_wald = set()
            for i, (lat, lon) in enumerate(zellen):
                s_, n_ = lat - d_lat / 2, lat + d_lat / 2
                w_, o_ = lon - d_lon / 2, lon + d_lon / 2
                for a_, b_ in ecken:
                    if s_ <= a_ <= n_ and w_ <= b_ <= o_:
                        mit_wald.add(i)
                        break
            return mit_wald

        except Exception as e:
            print(f"    {str(e)[:70]}", flush=True)
        time.sleep(3)

    return None


def main():
    punkte, d_lat, d_lon = gitter()
    schon_da, anzahl = vorhandene()

    fehlend = [(lat, lon) for lat, lon in punkte
               if ist_neu(lat, lon, schon_da, d_lat, d_lon)]

    print(f"Gitter: {len(punkte)} moegliche Zellen")
    print(f"Vorhanden: {anzahl}")
    print(f"Zu pruefen: {len(fehlend)}\n")

    if not fehlend:
        print("Nichts zu ergaenzen.")
        return

    if ALLE_ZELLEN:
        print("ALLE_ZELLEN ist eingeschaltet - es werden alle "
              f"{len(fehlend)} Zellen aufgenommen,")
        print("ohne Abfrage bei OpenStreetMap.\n")
        if input("Uebernehmen? (j/n) ").strip().lower()[:1] != "j":
            return

        # An der HOECHSTEN vorhandenen Nummer weiterzaehlen, nicht an
        # der Zeilenzahl. Wurden vorher Punkte entfernt, ist die
        # Zeilenzahl kleiner als die hoechste Kennung - und die neuen
        # Punkte bekaemen Kennungen, die es schon gibt. Beim Einlesen
        # ueberschreibt dann einer den anderen, und der neue erbt die
        # Wetterdaten des alten von einer ganz anderen Stelle.
        naechste = hoechste_nummer() + 1
        with open(DATEI, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for lat, lon in fehlend:
                writer.writerow([f"W{naechste:04d}", lat, lon])
                naechste += 1

        print(f"\n{len(fehlend)} Zellen in {DATEI}.")
        print(f"Jetzt {anzahl + len(fehlend)} Punkte insgesamt.")
        print("\nDamit sie brauchbar werden, der Reihe nach:")
        print("  python nachfuellen.py")
        print("  python baumarten.py")
        print("  python bodendaten.py")
        print("  python hoehen.py")
        print("  python ortsnamen.py")
        return

    bloecke = (len(fehlend) + BLOCK - 1) // BLOCK
    anzahl_bloecke = (len(fehlend) + BLOCK - 1) // BLOCK
    print(f"{anzahl_bloecke} Abfragen, etwa "
          f"{anzahl_bloecke*10/60:.0f} Minuten.")
    print("Ein Abbruch ist unkritisch - beim Neustart wird "
          "fortgesetzt.")
    print("Neue Punkte brauchen danach 90 Tage Wetterhistorie -")
    print("das dauert einen weiteren Lauf von nachfuellen.py.\n")
    if input("Starten? (j/n) ").strip().lower()[:1] != "j":
        return

    # Zwischenstand: schon geprueft, mit Ergebnis
    geprueft = {}
    if os.path.exists(STAND):
        with open(STAND, "r", encoding="utf-8") as f:
            for z in csv.DictReader(f):
                geprueft[(round(float(z["lat"]), 5),
                          round(float(z["lon"]), 5))] = z["wald"] == "1"
        print(f"Zwischenstand: {len(geprueft)} Zellen schon geprueft\n")

    offen = [(a, b) for a, b in fehlend
             if (round(a, 5), round(b, 5)) not in geprueft]
    neu = [k for k, v in geprueft.items() if v]

    if not offen:
        print("Alle Zellen geprueft.")
    else:
        bloecke = [offen[i:i + BLOCK] for i in range(0, len(offen), BLOCK)]
        beginn = time.time()

        # Zwischenstand fortschreiben, damit ein Abbruch nichts kostet
        neuanlage = not os.path.exists(STAND)
        stand = open(STAND, "a", newline="", encoding="utf-8")
        schreiber = csv.writer(stand)
        if neuanlage:
            schreiber.writerow(["lat", "lon", "wald"])

        for i, block in enumerate(bloecke, start=1):
            print(f"\n  Block {i} von {len(bloecke)} "
                  f"({len(block)} Zellen)", flush=True)

            ergebnis = None
            for anlauf in range(1, 6):
                ergebnis = frage_block(block, d_lat, d_lon)
                if ergebnis is not None:
                    break
                wartezeit = min(180, 20 * anlauf)
                print(f"    Anlauf {anlauf} fehlgeschlagen, "
                      f"warte {wartezeit} s", flush=True)
                time.sleep(wartezeit)

            if ergebnis is None:
                # Nach fuenf Anlaeufen aufgeben und spaeter nochmal -
                # der Zwischenstand merkt sich diese Zellen nicht
                print("    dauerhaft fehlgeschlagen, uebersprungen",
                      flush=True)
                continue

            gefunden = 0
            for j, (lat, lon) in enumerate(block):
                hat = j in ergebnis
                schreiber.writerow([lat, lon, 1 if hat else 0])
                if hat:
                    neu.append((lat, lon))
                    gefunden += 1
            stand.flush()

            dauer = time.time() - beginn
            rest = (len(bloecke) - i) / max(i / max(dauer, 0.1), 0.01) / 60
            print(f"    {gefunden} mit Wald, zusammen {len(neu)}, "
                  f"noch ~{rest:.0f} min", flush=True)
            time.sleep(2)

        stand.close()

    if not neu:
        print("\nKeine weiteren Waldzellen gefunden.")
        return

    # An der hoechsten vorhandenen Nummer weiterzaehlen
    naechste = hoechste_nummer() + 1
    with open(DATEI, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for lat, lon in neu:
            writer.writerow([f"W{naechste:04d}", lat, lon])
            naechste += 1

    try:
        os.remove(STAND)
    except OSError:
        pass

    print(f"\n{len(neu)} neue Zellen in {DATEI}.")
    print(f"Jetzt {anzahl + len(neu)} Punkte insgesamt.")
    print("\nDamit sie brauchbar werden, der Reihe nach:")
    print("  python nachfuellen.py")
    print("  python baumarten.py")
    print("  python bodendaten.py")
    print("  python hoehen.py")
    print("  python ortsnamen.py")


main()
