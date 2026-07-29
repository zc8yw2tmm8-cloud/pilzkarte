"""
Zeigt, wie Boden-pH und Sandanteil in der Region verteilt sind -
und, sobald bodendaten_funde.csv vorliegt, ob die Pilze tatsaechlich
bestimmte Boeden bevorzugen.

Ohne Funddaten: reine Uebersicht.
Mit Funddaten: Auswahlverhaeltnis wie in kalibrieren.py.
"""
import csv
import os
from collections import defaultdict

BODEN = "bodendaten.csv"
BODEN_FUNDE = "bodendaten_funde.csv"
FUNDE = "funde_arten.csv"

FELDER = [("ph", "pH-Wert", 1, ""), ("sand", "Sandanteil", 1, "%"),
          ("clay", "Tonanteil", 1, "%"), ("cec", "Naehrstoffspeicher", 1, ""),
          ("humus", "Humus", 1, "g/kg")]


def zahl(t):
    if t is None or t == "":
        return None
    try:
        return float(t)
    except ValueError:
        return None


def lade(datei):
    if not os.path.exists(datei):
        return {}
    daten = {}
    with open(datei, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            daten[z["id"]] = {k: zahl(z.get(k)) for k in
                              ("lat", "lon", "ph", "sand", "clay",
                               "cec", "humus")}
    return daten


def quantile(werte, anteile):
    werte = sorted(w for w in werte if w is not None)
    if not werte:
        return []
    return [werte[min(int(len(werte) * a), len(werte) - 1)] for a in anteile]


def uebersicht(boden):
    print(f"{len(boden)} Punkte mit Bodendaten\n")
    print(f"{'Groesse':<20}{'10%':>8}{'25%':>8}{'Median':>8}"
          f"{'75%':>8}{'90%':>8}")
    for feld, name, _, einheit in FELDER:
        q = quantile([b[feld] for b in boden.values()],
                     [.1, .25, .5, .75, .9])
        if not q:
            continue
        print(f"{name:<20}" + "".join(f"{round(w, 1):>8}" for w in q))

    # Nord-Sued-Verlauf
    print("\nVerlauf von Sued nach Nord (je 0.2 Grad):")
    gruppen = defaultdict(list)
    for b in boden.values():
        if b["lat"] is None:
            continue
        gruppen[round(b["lat"] * 5) / 5].append(b)

    print(f"{'Breite':<10}{'n':>6}{'pH':>8}{'Sand %':>9}{'Ton %':>8}")
    for lat in sorted(gruppen):
        g = gruppen[lat]
        def m(feld):
            w = [x[feld] for x in g if x[feld] is not None]
            return round(sum(w) / len(w), 1) if w else "-"
        print(f"{lat:<10}{len(g):>6}{m('ph'):>8}{m('sand'):>9}{m('clay'):>8}")


def auswahl(boden, fundboden, funde_je_art):
    """Auswahlverhaeltnis: Bodenwerte an Fundorten gegen die Region."""
    print("\n" + "=" * 58)
    print("Bevorzugen die Arten bestimmte Boeden?")
    print("=" * 58)

    for art, ids in sorted(funde_je_art.items()):
        werte = [fundboden[i] for i in ids if i in fundboden]
        if len(werte) < 40:
            print(f"\n{art}: nur {len(werte)} Fundorte mit Boden, zu wenig")
            continue

        print(f"\n{art.upper()}  ({len(werte)} Fundorte)")

        for feld, name, _, einheit in FELDER[:3]:
            hg = [b[feld] for b in boden.values() if b[feld] is not None]
            fw = [b[feld] for b in werte if b[feld] is not None]
            if len(hg) < 100 or len(fw) < 30:
                continue

            grenzen = sorted(set(quantile(hg, [.25, .5, .75])))
            if len(grenzen) < 2:
                continue

            def klasse(w):
                for i, g in enumerate(grenzen):
                    if w <= g:
                        return i
                return len(grenzen)

            n = len(grenzen) + 1
            hz = [0] * n
            fz = [0] * n
            for w in hg:
                hz[klasse(w)] += 1
            for w in fw:
                fz[klasse(w)] += 1

            print(f"  {name}")
            for i in range(n):
                b = (f"bis {round(grenzen[0], 1)}" if i == 0
                     else f"ab {round(grenzen[-1], 1)}" if i == n - 1
                     else f"{round(grenzen[i-1], 1)}-{round(grenzen[i], 1)}")
                fa = fz[i] / len(fw)
                ha = hz[i] / len(hg)
                v = fa / ha if ha else 0
                m = "  <<<" if v >= 1.4 else "  <" if v >= 1.15 else \
                    "  --" if v <= 0.65 else ""
                print(f"    {b + ' ' + einheit:<14}{fa*100:6.1f}%"
                      f"{ha*100:7.1f}%{v:7.2f}{m}")


def main():
    boden = lade(BODEN)
    if not boden:
        print(f"{BODEN} fehlt. Erst bodendaten.py laufen lassen.")
        return

    uebersicht(boden)

    fundboden = lade(BODEN_FUNDE)
    if not fundboden or not os.path.exists(FUNDE):
        print("\n" + "-" * 58)
        print("Fuer den Vergleich mit Funden fehlt bodendaten_funde.csv.")
        print("bodendaten.py nochmal starten und die Fundorte mitnehmen.")
        return

    funde_je_art = defaultdict(set)
    with open(FUNDE, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            kennung = f"F{round(float(z['lat']), 3)}_{round(float(z['lon']), 3)}"
            funde_je_art[z["art"]].add(kennung)

    auswahl(boden, fundboden, funde_je_art)


main()
