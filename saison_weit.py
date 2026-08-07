"""
Berechnet die Saisonfaktoren aus einem grossen Gebiet.

Fuer Boden, Baumarten und Wetter braucht die Kalibrierung einen
oertlichen Hintergrund - deshalb ist sie an eure Region gebunden.
Der Saisonfaktor braucht das nicht: Er ist der Anteil einer Art an
allen Pilzmeldungen desselben Monats. Das laesst sich ueber ganz
Norddeutschland rechnen und liefert fuer Pfifferling und
Sommersteinpilz ein Vielfaches der Fundzahlen.

Fragt nur Zaehlungen ab, keine Einzelmeldungen - deshalb schnell.

Ergebnis: saison_weit.txt mit fertigen Zeilen fuer arten.py
"""
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Norddeutsches Tiefland und angrenzende Mittelgebirge
SUED, WEST, NORD, OST = 51.0, 6.5, 54.5, 13.5
JAHR_VON, JAHR_BIS = 2015, 2026

ARTEN = {
    "steinpilz": "Boletus edulis",
    "sommersteinpilz": "Boletus reticulatus",
    "marone": "Imleria badia",
    "pfifferling": "Cantharellus cibarius",
    "birkenpilz": "Leccinum scabrum",
    "schwefelporling": "Laetiporus sulphureus",
    "parasol": "Macrolepiota procera",
    "hexenroehrling": "Neoboletus erythropus",
    "netzhexe": "Suillellus luridus",
    "reizker": "Lactarius deliciosus",
    "krauseglucke": "Sparassis crispa",
}

AUFWAND_GRUPPE = "Agaricomycetes"
MINDEST_AUFWAND = 200

BASIS = "https://api.gbif.org/v1"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}
AUSGABE = "saison_weit.txt"

MONATSNAMEN = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
LETZTER = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
           7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def taxonkey(name):
    try:
        d = requests.get(f"{BASIS}/species/match", params={"name": name},
                         headers=HEADERS, timeout=45).json()
        return d.get("usageKey"), d.get("scientificName")
    except Exception:
        return None, None


def monatszahl(key, monat):
    """Zaehlung fuer einen Monat ueber alle Jahre."""
    summe = 0
    for jahr in range(JAHR_VON, JAHR_BIS + 1):
        parameter = {
            "taxonKey": key, "hasCoordinate": "true",
            "decimalLatitude": f"{SUED},{NORD}",
            "decimalLongitude": f"{WEST},{OST}",
            "eventDate": f"{jahr}-{monat:02d}-01,"
                         f"{jahr}-{monat:02d}-{LETZTER[monat]}",
            "limit": 0,
        }
        for _ in range(3):
            try:
                summe += requests.get(f"{BASIS}/occurrence/search",
                                      params=parameter, headers=HEADERS,
                                      timeout=60).json().get("count", 0)
                break
            except Exception:
                time.sleep(2)
    return monat, summe


def alle_monate(key):
    with ThreadPoolExecutor(max_workers=6) as pool:
        ergebnis = dict(pool.map(lambda m: monatszahl(key, m), range(1, 13)))
    return ergebnis


def balken(werte):
    return "".join("#" if w >= 0.7 else "+" if w >= 0.35
                   else "." if w > 0.05 else " " for w in werte)


def main():
    print(f"Gebiet: {SUED}-{NORD} Nord, {WEST}-{OST} Ost")
    print(f"Jahre {JAHR_VON} bis {JAHR_BIS}\n")

    key, name = taxonkey(AUFWAND_GRUPPE)
    print(f"Bezugsgruppe {name} ...")
    aufwand = alle_monate(key)
    print("  " + "  ".join(f"{MONATSNAMEN[m-1]} {aufwand[m]}"
                           for m in range(1, 13)))
    print()

    zeilen = []
    print(f"{'Art':<18}{'Funde':>8}   JFMAMJJASOND   Hoehepunkt")

    for schluessel, wissenschaftlich in ARTEN.items():
        k, n = taxonkey(wissenschaftlich)
        if k is None:
            print(f"{schluessel:<18}nicht gefunden")
            continue

        zahlen = alle_monate(k)
        gesamt = sum(zahlen.values())

        rate = {}
        duenn = []
        for m in range(1, 13):
            if aufwand.get(m, 0) < MINDEST_AUFWAND:
                rate[m] = 0.0
                if zahlen.get(m, 0) > 0:
                    duenn.append(m)
            else:
                rate[m] = zahlen[m] / aufwand[m]

        hoechste = max(rate.values()) if rate else 0
        if hoechste <= 0:
            print(f"{schluessel:<18}{gesamt:>8}   keine Rate berechenbar")
            continue

        faktor = {m: round(rate[m] / hoechste, 2) for m in range(1, 13)}
        hoch = max(faktor, key=faktor.get)

        print(f"{schluessel:<18}{gesamt:>8}   "
              f"{balken([faktor[m] for m in range(1, 13)])}   "
              f"{MONATSNAMEN[hoch-1]}"
              + ("   (duenne Monate: " + ",".join(str(m) for m in duenn) + ")"
                 if duenn else ""))

        zeile = ('        "saison": {'
                 + ", ".join(f"{m}: {faktor[m]}" for m in range(1, 13))
                 + "},")
        zeilen.append(f"# {schluessel}  ({gesamt} Funde im Grossgebiet)\n"
                      f"{zeile}\n")

    with open(AUSGABE, "w", encoding="utf-8") as f:
        f.write("# Saisonfaktoren aus dem Grossgebiet\n"
                f"# {SUED}-{NORD} Nord, {WEST}-{OST} Ost, "
                f"{JAHR_VON}-{JAHR_BIS}\n"
                f"# Bezugsgruppe: {AUFWAND_GRUPPE}\n\n"
                + "\n".join(zeilen))

    print(f"\nZeilen zum Einsetzen liegen in {AUSGABE}.")
    print("Mit den bisherigen Werten in arten.py vergleichen - wo beide")
    print("uebereinstimmen, ist die Sache sicher. Wo sie auseinandergehen,")
    print("hat das Grossgebiet mehr Funde, eure Region mehr Ortsbezug.")


main()
