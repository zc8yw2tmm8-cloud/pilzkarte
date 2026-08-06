"""
Findet ein fehlendes Feld anhand seiner Nachbarn.

Aufruf: die Kennungen der umliegenden Zellen eingeben, das Skript
rechnet aus, welches Feld dazwischen liegt und was dort ist.

Beantwortet drei Fragen:
  - Gibt es dort ueberhaupt einen Punkt in waldpunkte.csv?
  - Steht er in web/daten.json?
  - In welchem Feld landet er nach der Rechnung der Karte?
"""
import os
import csv
import json
import math

PUNKTE = "waldpunkte.csv"
DATEN = os.path.join("web", "daten.json")

# Die Nachbarlisten aus der Karte. Jede Gruppe beschreibt ein Loch.
GRUPPEN = [
    ["W0711", "W0743", "W0744", "W0745", "W0712", "W0657", "W0656",
     "W0655"],
    ["W0657", "W0712", "W0684", "W0713", "W0714", "W0658", "W0628",
     "W1615", "W0627", "W0626"],
    ["W0663", "W0718", "W0719", "W0720", "W0664", "W1617", "W0633",
     "W0632"],
    ["W1601", "W0638", "W0639", "W0640", "W1602", "W0613", "W0612",
     "W0611"],
    ["W0643", "W0674", "W0730", "W0731", "W0732", "W0733", "W0675",
     "W0644", "W1767", "W1766", "W1605", "W1604"],
    ["W0678", "W0736", "W0737", "W0705", "W0679", "W0649", "W0648",
     "W0647"],
    ["W1614", "W1613", "W0650", "W0680", "W0738", "W1630"],
]


def main():
    with open(DATEN, "r", encoding="utf-8") as f:
        d = json.load(f)
    g = d["gitter"]

    # Zellen aus daten.json - das sieht die Karte
    aus_json = {z["id"]: z for z in d["zellen"]}

    # Punkte aus waldpunkte.csv - das sehen die Skripte
    aus_csv = {}
    with open(PUNKTE, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            aus_csv[z["id"]] = (float(z["lat"]), float(z["lon"]))

    def feld(lat, lon):
        return (math.floor((lat - g["sued"]) / g["schritt_lat"]),
                math.floor((lon - g["west"]) / g["schritt_lon"]))

    # Alle belegten Felder nach der Rechnung der Karte
    belegt = {}
    for kennung, z in aus_json.items():
        belegt.setdefault(feld(z["lat"], z["lon"]), []).append(kennung)

    print(f"{len(aus_csv)} Punkte in {PUNKTE}")
    print(f"{len(aus_json)} Zellen in daten.json")
    print(f"{len(belegt)} belegte Felder nach Kartenrechnung\n")

    nur_csv = set(aus_csv) - set(aus_json)
    if nur_csv:
        print(f"{len(nur_csv)} Punkte fehlen in daten.json: "
              f"{', '.join(sorted(nur_csv)[:8])}\n")

    print("=" * 58)
    for nummer, gruppe in enumerate(GRUPPEN, start=1):
        vorhanden = [k for k in gruppe if k in aus_json]
        if not vorhanden:
            print(f"\nGruppe {nummer}: keine der Kennungen gefunden")
            continue

        felder = [feld(aus_json[k]["lat"], aus_json[k]["lon"])
                  for k in vorhanden]
        z_werte = sorted({f[0] for f in felder})
        s_werte = sorted({f[1] for f in felder})

        # Welche Felder im umschlossenen Bereich sind leer?
        loecher = [(z, s)
                   for z in range(min(z_werte), max(z_werte) + 1)
                   for s in range(min(s_werte), max(s_werte) + 1)
                   if (z, s) not in belegt]

        print(f"\nGruppe {nummer} ({len(vorhanden)} Nachbarn)")
        print(f"  Bereich: Zeilen {min(z_werte)}-{max(z_werte)}, "
              f"Spalten {min(s_werte)}-{max(s_werte)}")

        if loecher:
            print(f"  {len(loecher)} leere Felder:")
            for z, s in loecher:
                lat = g["sued"] + (z + 0.5) * g["schritt_lat"]
                lon = g["west"] + (s + 0.5) * g["schritt_lon"]
                print(f"     Feld ({z},{s}) Mitte {lat:.5f}, {lon:.5f}")
        else:
            print("  Kein leeres Feld - alle belegt.")

        doppelt = [(f, v) for f, v in belegt.items()
                   if len(v) > 1
                   and min(z_werte) <= f[0] <= max(z_werte)
                   and min(s_werte) <= f[1] <= max(s_werte)]
        if doppelt:
            print(f"  {len(doppelt)} doppelt belegte Felder:")
            for f, v in doppelt:
                print(f"     Feld {f}: {', '.join(v)}")


main()