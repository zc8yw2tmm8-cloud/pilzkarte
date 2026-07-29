"""
Fuegt die iNaturalist-Beobachtungen zu den GBIF-Funden hinzu.

Legt vorher eine Kopie an und zeigt, was dazukommt. Fragt nach.
Doppelte werden entfernt: gleiche Art, gleicher Tag, gleiche Stelle
auf 100 m genau.

Danach neu rechnen:
    python funde_wetter2.py
    python kalibrieren.py
"""
import csv
import os
import shutil
from collections import Counter

GBIF = "funde_arten.csv"
INAT = "funde_inat.csv"
KOPIE = "funde_arten_nur_gbif.csv"

# Welche Pruefstufen uebernommen werden. "research" ist bestaetigt,
# "needs_id" noch offen - bei unverwechselbaren Arten vertretbar,
# bei aehnlichen Arten heikel.
STUFEN = ["research", "needs_id"]

# Arten, bei denen unbestaetigte Meldungen NICHT uebernommen werden.
# Der Sommersteinpilz wird regelmaessig als Steinpilz gemeldet und
# umgekehrt - da wuerde needs_id mehr schaden als nutzen.
NUR_BESTAETIGT = {"sommersteinpilz", "steinpilz", "marone"}

SPALTEN = ["art", "gbif_id", "datum", "lat", "lon", "unsicherheit_m", "ort"]


def schluessel(z):
    return (z["art"], z["datum"],
            round(float(z["lat"]), 3), round(float(z["lon"]), 3))


def main():
    for pflicht in (GBIF, INAT):
        if not os.path.exists(pflicht):
            print(f"{pflicht} fehlt.")
            return

    with open(GBIF, "r", encoding="utf-8") as f:
        gbif = [dict(z) for z in csv.DictReader(f)]
    vorhanden = {schluessel(z) for z in gbif}

    with open(INAT, "r", encoding="utf-8") as f:
        inat = [dict(z) for z in csv.DictReader(f)]

    neu = []
    abgelehnt = Counter()

    for z in inat:
        stufe = z.get("stufe", "research")
        if stufe not in STUFEN:
            abgelehnt["falsche Pruefstufe"] += 1
            continue
        if stufe != "research" and z["art"] in NUR_BESTAETIGT:
            abgelehnt["unbestaetigt bei heikler Art"] += 1
            continue
        if schluessel(z) in vorhanden:
            abgelehnt["schon vorhanden"] += 1
            continue
        vorhanden.add(schluessel(z))
        neu.append({s: z.get(s, "") for s in SPALTEN})

    print(f"{len(gbif)} Funde aus GBIF")
    print(f"{len(inat)} Beobachtungen von iNaturalist\n")

    for grund, n in abgelehnt.most_common():
        print(f"  {n:5d} {grund}")
    print(f"  {len(neu):5d} kommen dazu\n")

    if not neu:
        print("Nichts zu ergaenzen.")
        return

    print(f"{'Art':<18}{'bisher':>8}{'neu':>7}{'gesamt':>9}{'Zuwachs':>10}")
    alt_zahl = Counter(z["art"] for z in gbif)
    neu_zahl = Counter(z["art"] for z in neu)
    for art in sorted(set(alt_zahl) | set(neu_zahl)):
        a, n = alt_zahl[art], neu_zahl[art]
        print(f"{art:<18}{a:>8}{n:>7}{a+n:>9}"
              f"{(n/a*100 if a else 0):>9.0f}%")

    print()
    antwort = input("Zusammenfuegen? (j/n) ").strip().lower()
    if not antwort.startswith("j"):
        print("Abgebrochen.")
        return

    if not os.path.exists(KOPIE):
        shutil.copy(GBIF, KOPIE)
        print(f"Kopie der GBIF-Fassung als {KOPIE} abgelegt.")

    with open(GBIF, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        writer.writerows([{s: z.get(s, "") for s in SPALTEN} for z in gbif])
        writer.writerows(neu)

    print(f"\n{len(gbif) + len(neu)} Funde in {GBIF}.")
    print("\nDanach neu rechnen:")
    print("  python funde_wetter2.py")
    print("  python kalibrieren.py")
    print("  python saison_uebernehmen.py")


main()
