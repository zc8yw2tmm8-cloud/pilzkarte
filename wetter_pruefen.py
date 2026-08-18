"""
Prueft, ob die Wetterbaender Beobachterverzerrung enthalten.

Die Baender wurden gegen zufaellige Tage gerechnet. Menschen gehen
aber nicht zufaellig sammeln, sondern nach Regen - weil sie wissen,
dass dann Pilze kommen. Dieselbe Verzerrung hat bei Boden und
Baumarten mehr ausgemacht als die Biologie.

Dieses Skript rechnet dieselben Auswahlverhaeltnisse zweimal:

  A: Funde gegen ALLE Tage         (wie bisher)
  B: Funde gegen MELDETAGE         (Sammlerverhalten herausgerechnet)

Weichen die Ergebnisse stark ab, sind die Baender zu korrigieren.
Bleiben sie aehnlich, war die Sorge unbegruendet - und das waere ein
wichtiger Befund fuer sich.

Braucht: hintergrund.csv, funde_wetter2.csv, aufwand_tage.csv
"""
import os
import csv
from datetime import date
from collections import defaultdict

import arten
from kennwerte import berechne, zahl

HINTERGRUND = "hintergrund.csv"
FUNDE = "funde_wetter2.csv"
TAGE = "aufwand_tage.csv"

SCHRITT = 2
MINDEST_FUNDE = 60

# Groessen, die geprueft werden
GROESSEN = [
    ("bf07", "Bodenfeuchte 0-7cm", 100, "%"),
    ("bt07", "Bodentemperatur", 1, "C"),
    ("bilanz_14", "Wasserbilanz 14T", 1, "mm"),
    ("regen_reife", "Regen Tag 4-14", 1, "mm"),
    ("regentage", "Regentage von 14", 1, ""),
]


def lade_hintergrund():
    punkte = defaultdict(list)
    with open(HINTERGRUND, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte[z["ort"]].append({
                "tag": date.fromisoformat(z["datum"]),
                "regen": zahl(z.get("regen")),
                "temp": zahl(z.get("temp")),
                "bt07": zahl(z.get("bt07")),
                "bf07": zahl(z.get("bf07")),
                "bt728": zahl(z.get("bt728")),
                "bf728": zahl(z.get("bf728")),
                "et0": zahl(z.get("et0")),
            })
    for o in punkte:
        punkte[o].sort(key=lambda r: r["tag"])

    tage = []
    for r in punkte.values():
        for i in range(62, len(r), SCHRITT):
            t = r[i]["tag"]
            k = berechne(r[i - 62:i + 1], t)
            if k:
                k["tag"] = t
                tage.append(k)
    return tage


def lade_meldetage():
    if not os.path.exists(TAGE):
        return None
    with open(TAGE, "r", encoding="utf-8") as f:
        return {z["datum"]: int(z["meldungen"])
                for z in csv.DictReader(f)}


def lade_funde():
    funde = defaultdict(list)
    with open(FUNDE, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            e = {k: zahl(v) for k, v in z.items()
                 if k not in ("art", "datum", "gbif_id")}
            e["monat"] = int(z["monat"])
            funde[z["art"]].append(e)
    return funde


def grenzen(werte, anteile=(0.2, 0.4, 0.6, 0.8)):
    w = sorted(x for x in werte if x is not None)
    if not w:
        return []
    return sorted(set(w[min(int(len(w) * p), len(w) - 1)]
                      for p in anteile))


def verhaeltnis(fundwerte, hintergrundwerte, gewichte, gr):
    """Auswahlverhaeltnis je Klasse. gewichte kann None sein."""
    def klasse(x):
        for i, g in enumerate(gr):
            if x <= g:
                return i
        return len(gr)

    n = len(gr) + 1
    fz = [0.0] * n
    hz = [0.0] * n

    for x in fundwerte:
        if x is not None:
            fz[klasse(x)] += 1
    for i, x in enumerate(hintergrundwerte):
        if x is None:
            continue
        hz[klasse(x)] += gewichte[i] if gewichte else 1.0

    fs, hs = sum(fz), sum(hz)
    if not fs or not hs:
        return None
    return [round((fz[i] / fs) / (hz[i] / hs), 2) if hz[i] else 0.0
            for i in range(n)]


def main():
    for pflicht in (HINTERGRUND, FUNDE):
        if not os.path.exists(pflicht):
            print(f"{pflicht} fehlt.")
            return

    meldetage = lade_meldetage()
    if meldetage is None:
        print(f"{TAGE} fehlt - erst aufwand_tage.py laufen lassen.")
        print("Ohne die Meldetage laesst sich die Verzerrung nicht")
        print("pruefen.")
        return

    print("Lese Hintergrund ...", flush=True)
    hintergrund = lade_hintergrund()
    funde = lade_funde()

    # Gewicht je Vergleichstag: wie viele Meldungen gab es an dem Tag?
    gewichte = [meldetage.get(k["tag"].isoformat(), 0)
                for k in hintergrund]
    mit = sum(1 for g in gewichte if g > 0)

    print(f"{len(hintergrund)} Vergleichstage, davon {mit} mit "
          f"Meldungen ({mit/len(hintergrund)*100:.0f} %)")
    print(f"{len(meldetage)} Meldetage insgesamt\n")

    if mit < 500:
        print("Zu wenige Vergleichstage mit Meldungen - das Ergebnis")
        print("waere nicht belastbar.")
        return

    print("=" * 70)
    print("A = gegen alle Tage (wie bisher)")
    print("B = gegen Meldetage (Sammlerverhalten herausgerechnet)")
    print("=" * 70)

    grosse_abweichung = []

    for art in sorted(funde):
        liste = funde[art]
        mz = defaultdict(int)
        for f in liste:
            mz[f["monat"]] += 1
        kern = {m for m in range(1, 13) if mz[m] >= len(liste) * 0.08}
        teil = [f for f in liste if f["monat"] in kern]

        if len(teil) < MINDEST_FUNDE:
            continue

        hk = [k for k in hintergrund if k["tag"].month in kern]
        gk = [meldetage.get(k["tag"].isoformat(), 0) for k in hk]
        if sum(gk) == 0:
            continue

        name = arten.ARTEN.get(art, {}).get("name", art)
        print(f"\n{name}  ({len(teil)} Funde in den Kernmonaten)")

        for feld, bezeichnung, faktor, einheit in GROESSEN:
            hw = [k.get(feld) for k in hk]
            fw = [f.get(feld) for f in teil]
            gr = grenzen([x for x in hw if x is not None])
            if len(gr) < 3:
                continue

            a = verhaeltnis(fw, hw, None, gr)
            b = verhaeltnis(fw, hw, gk, gr)
            if not a or not b:
                continue

            bereiche = []
            for i in range(len(gr) + 1):
                if i == 0:
                    bereiche.append(f"bis {round(gr[0]*faktor,1)}")
                elif i == len(gr):
                    bereiche.append(f"ab {round(gr[-1]*faktor,1)}")
                else:
                    bereiche.append(f"{round(gr[i-1]*faktor,1)}-"
                                    f"{round(gr[i]*faktor,1)}")

            print(f"  {bezeichnung} ({einheit})")
            print(f"    {'Bereich':<16}{'A':>7}{'B':>7}{'':>4}")
            for i, bereich in enumerate(bereiche):
                unterschied = abs(a[i] - b[i])
                marke = "  <<<" if unterschied >= 0.4 else ""
                if unterschied >= 0.4:
                    grosse_abweichung.append(
                        (name, bezeichnung, bereich, a[i], b[i]))
                print(f"    {bereich:<16}{a[i]:>7.2f}{b[i]:>7.2f}{marke}")

    print("\n" + "=" * 70)
    if grosse_abweichung:
        print(f"{len(grosse_abweichung)} Baender weichen deutlich ab.")
        print("Bei diesen ist ein Teil des gemessenen Zusammenhangs")
        print("Sammlerverhalten, nicht Biologie.")
    else:
        print("Keine grossen Abweichungen.")
        print("Die Wetterbaender halten dem Vergleich stand - das")
        print("Sammlerverhalten erklaert sie nicht.")


main()
