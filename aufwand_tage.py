"""
Holt die Meldetage aller Pilzbeobachtungen der Region.

Warum: Die Wetterbaender wurden gegen zufaellige Tage gerechnet.
Menschen gehen aber nicht zufaellig sammeln - sie gehen nach Regen,
weil sie wissen, dass dann Pilze kommen. Genau die Baender, die wir
messen wollen, koennten dadurch verstaerkt sein.

Bei Boden und Baumarten hat sich gezeigt, dass diese Verzerrung
groesser sein kann als die Biologie. Ob das beim Wetter auch so ist,
laesst sich nur mit den Meldetagen pruefen.

Holt fuer jeden Tag seit 2019 die Zahl der Agaricomycetes-Meldungen
in der Region. Aus jedem Tag mit Meldungen wird ein Vergleichstag -
gewichtet nach der Zahl der Meldungen.

Ergebnis: aufwand_tage.csv mit Spalten datum, meldungen
"""
import os
import csv
import time
import requests
from datetime import date, timedelta

SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
JAHR_VON, JAHR_BIS = 2019, 2026

GRUPPE = "Agaricomycetes"
DATEI = "aufwand_tage.csv"

BASIS = "https://api.gbif.org/v1"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}


def taxonkey(name):
    a = requests.get(f"{BASIS}/species/match", params={"name": name},
                     headers=HEADERS, timeout=45).json()
    return a.get("usageKey"), a.get("scientificName")


def lade_vorhandene():
    if not os.path.exists(DATEI):
        return {}
    with open(DATEI, "r", encoding="utf-8") as f:
        return {z["datum"]: int(z["meldungen"])
                for z in csv.DictReader(f)}


def schreibe(werte):
    with open(DATEI, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["datum", "meldungen"])
        for tag in sorted(werte):
            w.writerow([tag, werte[tag]])


def hole_monat(key, jahr, monat):
    """
    Alle Meldungen eines Monats, nach Tagen gezaehlt.

    Ein Monat je Anfrage statt ein Tag - das sind 96 Anfragen statt
    2900.
    """
    letzter = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
               7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}[monat]

    zaehler = {}
    offset = 0

    while True:
        parameter = {
            "taxonKey": key, "hasCoordinate": "true",
            "decimalLatitude": f"{SUED},{NORD}",
            "decimalLongitude": f"{WEST},{OST}",
            "eventDate": f"{jahr}-{monat:02d}-01,"
                         f"{jahr}-{monat:02d}-{letzter}",
            "limit": 300, "offset": offset,
        }
        for versuch in range(4):
            try:
                daten = requests.get(f"{BASIS}/occurrence/search",
                                     params=parameter, headers=HEADERS,
                                     timeout=90).json()
                break
            except Exception:
                time.sleep(3 * (versuch + 1))
        else:
            return None

        treffer = daten.get("results", [])
        for t in treffer:
            tag = (t.get("eventDate") or "")[:10]
            if len(tag) == 10:
                zaehler[tag] = zaehler.get(tag, 0) + 1

        if daten.get("endOfRecords") or not treffer:
            break
        offset += 300
        if offset >= 20000:
            break
        time.sleep(0.3)

    return zaehler


def main():
    key, name = taxonkey(GRUPPE)
    if key is None:
        print(f"{GRUPPE} nicht gefunden.")
        return

    print(f"Bezugsgruppe: {name}")
    print(f"Gebiet: {SUED}-{NORD} Nord, {WEST}-{OST} Ost")
    print(f"Jahre {JAHR_VON} bis {JAHR_BIS}\n")

    werte = lade_vorhandene()
    if werte:
        print(f"{len(werte)} Tage schon geholt\n")

    monate = [(j, m) for j in range(JAHR_VON, JAHR_BIS + 1)
              for m in range(1, 13)
              if not (j == JAHR_BIS and m > date.today().month)]

    # Monate ueberspringen, aus denen schon Tage vorliegen
    offen = []
    for j, m in monate:
        vorsatz = f"{j}-{m:02d}"
        if not any(t.startswith(vorsatz) for t in werte):
            offen.append((j, m))

    if not offen:
        print("Nichts zu holen.")
    else:
        print(f"{len(offen)} Monate offen, geschaetzt "
              f"{len(offen) * 4 / 60:.0f} Minuten\n")
        beginn = time.time()

        for i, (j, m) in enumerate(offen, start=1):
            teil = hole_monat(key, j, m)
            if teil is None:
                print(f"  {j}-{m:02d}: fehlgeschlagen")
                continue
            werte.update(teil)

            if i % 6 == 0 or i == len(offen):
                schreibe(werte)
                dauer = time.time() - beginn
                rest = (len(offen) - i) / max(i / max(dauer, 0.1), 0.01)
                jetzt = time.strftime("%H:%M")
                print(f"  {i} von {len(offen)} Monaten, "
                      f"{len(werte)} Tage, noch ~{rest/60:.0f} min "
                      f"({jetzt})", flush=True)
            time.sleep(0.5)

        schreibe(werte)

    if not werte:
        return

    gesamt = sum(werte.values())
    print(f"\n{len(werte)} Tage mit Meldungen, {gesamt} Meldungen.")

    # Wie viele Tage im Zeitraum gibt es ueberhaupt?
    alle = (date(JAHR_BIS, date.today().month, 1)
            - date(JAHR_VON, 1, 1)).days
    print(f"Von {alle} Tagen im Zeitraum wurde an "
          f"{len(werte)} gemeldet ({len(werte)/alle*100:.0f} %).")
    print("\nWeiter mit: python wetter_pruefen.py")


main()
