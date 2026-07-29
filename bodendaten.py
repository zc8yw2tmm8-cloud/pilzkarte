"""
Holt Bodeneigenschaften von SoilGrids fuer alle Waldpunkte -
und optional fuer die GBIF-Fundorte, damit die Schwellen spaeter
kalibriert statt geschaetzt werden koennen.

Laeuft EINMAL. Boden aendert sich nicht.

Ergebnis: bodendaten.csv  (aus waldpunkte.csv)
          bodendaten_funde.csv  (aus funde_arten.csv, falls vorhanden)

WICHTIG: SoilGrids ist deutlich langsamer als Open-Meteo und drosselt
schnell. Rechne mit 30-50 Minuten fuer 1046 Punkte. Das Skript kann
jederzeit abgebrochen und neu gestartet werden - es setzt fort.
"""
import requests
import csv
import os
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

PUNKTE_DATEI = "waldpunkte.csv"
FUNDE_DATEI = "funde_arten.csv"
DATEI = "bodendaten.csv"
FUNDE_AUSGABE = "bodendaten_funde.csv"

# Gleichzeitige Abfragen. SoilGrids ist empfindlicher als Open-Meteo.
# Bei Drosselungsmeldungen auf 1 senken.
ARBEITER = 1

PAUSE = 0.4          # Sekunden zwischen Abfragen je Arbeiter

# Abbruch erst nach so vielen ECHTEN Fehlern hintereinander.
# Punkte ohne Bodenwerte (Siedlung) zaehlen NICHT dazu.
MAX_FEHLER = 20

EIGENSCHAFTEN = ["phh2o", "cec", "sand", "clay", "silt", "soc", "nitrogen"]
TIEFEN = ["0-5cm", "5-15cm", "15-30cm"]

TEILER = {"phh2o": 10, "cec": 10, "sand": 10, "clay": 10, "silt": 10,
          "soc": 10, "nitrogen": 100}

SPALTEN = ["id", "lat", "lon", "ph", "cec", "sand", "clay", "silt",
           "humus", "stickstoff"]


bremse = threading.Event()


def hole(lat, lon):
    """
    Rueckgabe:
      dict  - Werte gefunden
      {}    - Antwort in Ordnung, aber kein Boden (Siedlung, Wasser)
      None  - Abfrage fehlgeschlagen
    """
    parameter = [("lon", lon), ("lat", lat), ("value", "mean")]
    for e in EIGENSCHAFTEN:
        parameter.append(("property", e))
    for t in TIEFEN:
        parameter.append(("depth", t))

    for versuch in range(4):
        while bremse.is_set():
            time.sleep(1)
        try:
            antwort = requests.get(URL, params=parameter, headers=HEADERS,
                                   timeout=90)
        except Exception:
            time.sleep(5 * (versuch + 1))
            continue

        if antwort.status_code == 429:
            if not bremse.is_set():
                bremse.set()
                print("   gedrosselt, bremse kurz ...")
                time.sleep(20)
                bremse.clear()
            time.sleep(5 * (versuch + 1))
            continue

        if antwort.status_code != 200:
            time.sleep(5 * (versuch + 1))
            continue

        try:
            daten = antwort.json()
        except Exception:
            time.sleep(5)
            continue

        werte = {}
        for lage in daten.get("properties", {}).get("layers", []):
            name = lage.get("name")
            zahlen = [t.get("values", {}).get("mean")
                      for t in lage.get("depths", [])]
            zahlen = [z for z in zahlen if z is not None]
            if zahlen:
                werte[name] = round(
                    sum(zahlen) / len(zahlen) / TEILER.get(name, 1), 2)

        # Leeres dict heisst: Antwort war gueltig, es gibt hier nur
        # keinen Boden. Das ist kein Fehler.
        return werte

    return None


def zeile_bauen(kennung, lat, lon, w):
    return {
        "id": kennung, "lat": lat, "lon": lon,
        "ph": w.get("phh2o", ""),
        "cec": w.get("cec", ""),
        "sand": w.get("sand", ""),
        "clay": w.get("clay", ""),
        "silt": w.get("silt", ""),
        "humus": w.get("soc", ""),
        "stickstoff": w.get("nitrogen", ""),
    }


def schreibe(datei, zeilen):
    with open(datei, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        writer.writerows(zeilen)


def vorhandene(datei):
    fertig = {}
    if not os.path.exists(datei):
        return fertig
    with open(datei, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            fertig[z["id"]] = z
    return fertig


def abarbeiten(aufgaben, ziel, titel):
    """aufgaben: Liste von (kennung, lat, lon)"""
    fertig = vorhandene(ziel)
    zeilen = list(fertig.values())
    offen = [a for a in aufgaben if a[0] not in fertig]

    print(f"\n=== {titel} ===")
    print(f"{len(aufgaben)} Punkte, davon {len(fertig)} erledigt, "
          f"{len(offen)} offen")

    if not offen:
        print("Nichts zu tun.")
        return

    print(f"{ARBEITER} gleichzeitig\n")

    sperre = threading.Lock()
    zaehler = {"erledigt": 0, "leer": 0, "fehler": 0, "kette": 0}
    beginn = time.time()
    abbruch = threading.Event()

    def einer(auftrag):
        kennung, lat, lon = auftrag
        if abbruch.is_set():
            return None
        w = hole(lat, lon)
        time.sleep(PAUSE)
        return kennung, lat, lon, w

    with ThreadPoolExecutor(max_workers=ARBEITER) as pool:
        auftraege = [pool.submit(einer, a) for a in offen]

        for fertig_auftrag in as_completed(auftraege):
            try:
                ergebnis = fertig_auftrag.result()
            except Exception:
                ergebnis = None

            if ergebnis is None:
                continue

            kennung, lat, lon, w = ergebnis

            with sperre:
                zaehler["erledigt"] += 1

                if w is None:
                    zaehler["fehler"] += 1
                    zaehler["kette"] += 1
                    if zaehler["kette"] >= MAX_FEHLER:
                        print(f"\n{MAX_FEHLER} Fehler hintereinander - "
                              f"Abbruch. Spaeter neu starten.")
                        abbruch.set()
                elif not w:
                    # gueltige Antwort, nur kein Boden - kein Fehler
                    zaehler["leer"] += 1
                    zaehler["kette"] = 0
                else:
                    zaehler["kette"] = 0
                    zeilen.append(zeile_bauen(kennung, lat, lon, w))

                if zaehler["erledigt"] % 50 == 0:
                    schreibe(ziel, zeilen)
                    pro_sek = zaehler["erledigt"] / max(1, time.time() - beginn)
                    rest = ((len(offen) - zaehler["erledigt"])
                            / max(pro_sek, 0.01) / 60)
                    print(f"  {zaehler['erledigt']} von {len(offen)}  "
                          f"({round(pro_sek, 2)}/s, noch ~{round(rest)} min, "
                          f"{len(zeilen)} gespeichert)")

    schreibe(ziel, zeilen)

    print(f"\n{len(zeilen)} Punkte in {ziel}.")
    if zaehler["leer"]:
        print(f"{zaehler['leer']} ohne Bodenwerte (Siedlung oder Wasser).")
    if zaehler["fehler"]:
        print(f"{zaehler['fehler']} Abfragen fehlgeschlagen.")

    if zeilen:
        ph = sorted(float(z["ph"]) for z in zeilen if z["ph"] != "")
        sand = sorted(float(z["sand"]) for z in zeilen if z["sand"] != "")
        if ph:
            print(f"pH:   {ph[0]} bis {ph[-1]}, Median {ph[len(ph)//2]}")
        if sand:
            print(f"Sand: {sand[0]} bis {sand[-1]} %, "
                  f"Median {sand[len(sand)//2]} %")


def lade_waldpunkte():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))
    return punkte


def lade_fundorte():
    """Fundorte auf ein 250-m-Raster runden - SoilGrids loest nicht feiner
    auf, und benachbarte Funde teilen sich damit eine Abfrage."""
    if not os.path.exists(FUNDE_DATEI):
        return []

    gesehen = {}
    with open(FUNDE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            lat = round(float(z["lat"]), 3)
            lon = round(float(z["lon"]), 3)
            kennung = f"F{lat}_{lon}"
            if kennung not in gesehen:
                gesehen[kennung] = (kennung, lat, lon)

    orte = list(gesehen.values())

    # Mischen mit festem Startwert: funde_arten.csv ist nach Arten
    # sortiert. Ohne Mischen haette ein abgebrochener Lauf Bodendaten
    # nur fuer die ersten Arten - und die Kalibrierung waere verzerrt.
    random.Random(42).shuffle(orte)
    return orte


def main():
    if not os.path.exists(PUNKTE_DATEI):
        print(f"{PUNKTE_DATEI} fehlt.")
        return

    abarbeiten(lade_waldpunkte(), DATEI, "Waldpunkte")

    fundorte = lade_fundorte()
    if fundorte:
        print(f"\n{len(fundorte)} verschiedene Fundorte gefunden.")
        print("Diese braucht kalibrieren.py, um die Bodenschwellen")
        print("zu messen statt zu schaetzen.")
        antwort = input("Jetzt auch abfragen? (j/n) ").strip().lower()
        if antwort.startswith("j"):
            abarbeiten(fundorte, FUNDE_AUSGABE, "Fundorte")
        else:
            print("Uebersprungen. Spaeter einfach nochmal starten.")


main()
