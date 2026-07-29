"""
Ordnet jedem Fund aus funde_arten.csv die Wetterlage davor zu.

Zwei Phasen:
  1. Abrufen - laeuft parallel, das ist der schnelle Teil
  2. Rechnen  - laeuft lokal, braucht keine Verbindung

Kann jederzeit abgebrochen werden. Beim Neustart werden fertige Funde
uebernommen und nur die fehlenden geholt.

Ergebnis: funde_wetter2.csv
"""
import requests
import csv
import os
import time
import threading
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from kennwerte import berechne, KENNWERT_SPALTEN

FUNDE_DATEI = "funde_arten.csv"
DATEI = "funde_wetter2.csv"

# Wie weit zurueck geholt wird. 62 Tage werden fuer die 60-Tage-
# Wasserbilanz gebraucht. Auf 20 gesenkt laeuft alles etwa dreimal so
# schnell - dann fehlen aber regen_60 und bilanz_60 in der Kalibrierung.
RUECKBLICK = 62

MAX_UNSICHERHEIT = 5000

# Gleichzeitige Abrufe. Open-Meteo zaehlt nicht Anfragen, sondern
# Aufwand: 7 Groessen ueber 63 Tage sind rund 440 Wert-Tage und zaehlen
# mehrfach. Bei haeufiger Drosselung auf 2 senken.
ARBEITER = 4

FELDER = [
    "precipitation_sum",
    "temperature_2m_mean",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_temperature_7_to_28cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "et0_fao_evapotranspiration",
]

SPALTEN = (["art", "gbif_id", "datum", "lat", "lon", "monat", "hoehe"]
           + KENNWERT_SPALTEN)

sperre = threading.Lock()
bremse = threading.Event()      # gesetzt = alle warten kurz


def lade_funde():
    funde = []
    verworfen = 0
    gesehen = set()

    with open(FUNDE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            u = z.get("unsicherheit_m", "")
            if u not in ("", None):
                try:
                    if float(u) > MAX_UNSICHERHEIT:
                        verworfen += 1
                        continue
                except ValueError:
                    pass

            schluessel = (z["art"], z["datum"],
                          round(float(z["lat"]), 3), round(float(z["lon"]), 3))
            if schluessel in gesehen:
                verworfen += 1
                continue
            gesehen.add(schluessel)
            funde.append(z)

    print(f"{len(funde)} Funde verwendbar, "
          f"{verworfen} verworfen (ungenau oder Dublette).")
    return funde


def lade_fertige():
    fertig = {}
    if not os.path.exists(DATEI):
        return fertig
    with open(DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            fertig[(z["art"], str(z["gbif_id"]))] = z
    return fertig


def hole_reihe(lat, lon, fundtag):
    """Tagesreihe der 62 Tage vor dem Fund. Gibt (reihe, hoehe) zurueck."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    parameter = {
        "latitude": lat,
        "longitude": lon,
        "start_date": str(fundtag - timedelta(days=RUECKBLICK)),
        "end_date": str(fundtag),
        "daily": ",".join(FELDER),
        "timezone": "Europe/Berlin",
    }

    for versuch in range(6):
        # Wenn gebremst wird, kurz anstellen - aber nicht minutenlang
        while bremse.is_set():
            time.sleep(1)

        try:
            antwort = requests.get(url, params=parameter, timeout=60)
        except Exception:
            time.sleep(2 * (versuch + 1))
            continue

        if antwort.status_code == 429:
            # Nur der betroffene Abruf zieht sich zurueck, die anderen
            # laufen weiter. Kurze gemeinsame Bremse verhindert, dass
            # alle gleichzeitig nachlegen.
            if not bremse.is_set():
                bremse.set()
                time.sleep(3)
                bremse.clear()
            time.sleep(4 * (versuch + 1))
            continue

        try:
            daten = antwort.json()
        except Exception:
            time.sleep(2)
            continue

        if "daily" not in daten:
            grund = str(daten.get("reason", ""))[:90]
            if grund and versuch == 0:
                with sperre:
                    print(f"   API meldet: {grund}")
            time.sleep(3 * (versuch + 1))
            continue

        d = daten["daily"]
        n = len(d["time"])

        def spalte(feld):
            return d.get(feld) or [None] * n

        reihe = [{
            "tag": date.fromisoformat(tag),
            "regen": spalte("precipitation_sum")[i],
            "temp": spalte("temperature_2m_mean")[i],
            "bt07": spalte("soil_temperature_0_to_7cm_mean")[i],
            "bf07": spalte("soil_moisture_0_to_7cm_mean")[i],
            "bt728": spalte("soil_temperature_7_to_28cm_mean")[i],
            "bf728": spalte("soil_moisture_7_to_28cm_mean")[i],
            "et0": spalte("et0_fao_evapotranspiration")[i],
        } for i, tag in enumerate(d["time"])]

        return reihe, daten.get("elevation")

    return None, None


def schreibe(zeilen):
    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        writer.writerows(zeilen)


def main():
    funde = lade_funde()
    fertig = lade_fertige()

    if fertig:
        print(f"{len(fertig)} Funde schon ausgewertet, werden uebernommen.")

    offen = [f for f in funde
             if (f["art"], str(f["gbif_id"])) not in fertig]

    if not offen:
        print("Nichts zu tun.")
        return

    # Das Wetterraster ist rund 11 km grob: Funde am selben Tag in
    # derselben Zelle brauchen nur einen Abruf.
    aufgaben = {}
    for f in offen:
        schluessel = (round(float(f["lat"]), 1), round(float(f["lon"]), 1),
                      f["datum"])
        aufgaben.setdefault(schluessel, (float(f["lat"]), float(f["lon"]),
                                         date.fromisoformat(f["datum"])))

    print(f"\n{len(offen)} offene Funde, dafuer {len(aufgaben)} Abrufe "
          f"({ARBEITER} gleichzeitig)")
    dauer = len(aufgaben) / ARBEITER * 1.0 / 60
    print(f"Geschaetzt {round(dauer)} bis {round(dauer * 2)} Minuten\n")

    # Funde nach Abrufschluessel gruppieren, damit ein fertiger Abruf
    # sofort ausgewertet und weggeschrieben werden kann
    je_schluessel = {}
    for f in offen:
        s = (round(float(f["lat"]), 1), round(float(f["lon"]), 1), f["datum"])
        je_schluessel.setdefault(s, []).append(f)

    zeilen = list(fertig.values())
    fehler = 0
    ohne = 0
    erledigt = 0
    beginn = time.time()

    def verarbeite(schluessel, reihe, hoehe):
        """Alle Funde zu einem Abruf in Zeilen umwandeln."""
        neu_zeilen = []
        for f in je_schluessel.get(schluessel, []):
            fundtag = date.fromisoformat(f["datum"])
            k = berechne(reihe, fundtag)
            if k is None:
                continue
            z = {
                "art": f["art"], "gbif_id": f["gbif_id"], "datum": f["datum"],
                "lat": float(f["lat"]), "lon": float(f["lon"]),
                "monat": fundtag.month,
                "hoehe": "" if hoehe is None else hoehe,
            }
            for spalte in KENNWERT_SPALTEN:
                wert = k.get(spalte)
                z[spalte] = "" if wert is None else wert
            neu_zeilen.append(z)
        return neu_zeilen

    with ThreadPoolExecutor(max_workers=ARBEITER) as pool:
        auftraege = {
            pool.submit(hole_reihe, lat, lon, tag): schluessel
            for schluessel, (lat, lon, tag) in aufgaben.items()
        }

        for auftrag in as_completed(auftraege):
            schluessel = auftraege[auftrag]
            try:
                reihe, hoehe = auftrag.result()
            except Exception:
                reihe, hoehe = None, None

            erledigt += 1

            if reihe is None:
                fehler += 1
                ohne += len(je_schluessel.get(schluessel, []))
            else:
                zeilen.extend(verarbeite(schluessel, reihe, hoehe))

            # Zwischenstand sichern - ein Abbruch kostet dann fast nichts
            if erledigt % 100 == 0:
                schreibe(zeilen)
                pro_sek = erledigt / max(1, time.time() - beginn)
                rest = (len(aufgaben) - erledigt) / max(pro_sek, 0.01) / 60
                print(f"  {erledigt} von {len(aufgaben)}  "
                      f"({round(pro_sek, 2)}/s, noch ~{round(rest)} min, "
                      f"{len(zeilen)} Funde fertig, {fehler} Fehler)")

    schreibe(zeilen)

    minuten = (time.time() - beginn) / 60
    print(f"\n{len(zeilen)} Funde mit Wetterdaten in {DATEI}.")
    print(f"Laufzeit {round(minuten, 1)} Minuten.")
    if ohne:
        print(f"{ohne} ohne brauchbare Daten. Spaeter nochmal starten - "
              f"das Skript setzt fort.")

    from collections import Counter
    for art, n in Counter(z["art"] for z in zeilen).most_common():
        print(f"  {art}: {n}")


main()
