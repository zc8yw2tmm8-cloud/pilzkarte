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

# Der Massstab fuer den Vergleich.
#
# bodendaten.csv sind zufaellige Waldpunkte. Vergleicht man Fundorte
# damit, misst man auch, wo Menschen unterwegs sind - und das ist ein
# grosser Anteil. Bei den Baumarten hat sich gezeigt: Kiefer macht
# 45 % der Waldflaeche aus, aber nur 12 % der Meldeorte.
#
# bodendaten_aufwand.csv sind die Orte, an denen ueberhaupt Pilze
# gemeldet werden. Gegen die zu vergleichen laesst nur die
# Bodenvorliebe uebrig.
AUFWAND = "bodendaten_aufwand.csv"

# Womit verglichen wurde - fuer die Ausgabe. Liste, damit main()
# den Wert setzen kann.
MASSSTAB = ["zufaellige Waldpunkte"]
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


def rahmen(boden, rand=0.02):
    """Umschliessendes Rechteck der Hintergrundpunkte."""
    lats = [b["lat"] for b in boden.values() if b["lat"] is not None]
    lons = [b["lon"] for b in boden.values() if b["lon"] is not None]
    if not lats:
        return None
    return (min(lats) - rand, min(lons) - rand,
            max(lats) + rand, max(lons) + rand)


def im_rahmen(eintrag, r):
    if r is None:
        return True
    if eintrag["lat"] is None or eintrag["lon"] is None:
        return False
    sued, west, nord, ost = r
    return sued <= eintrag["lat"] <= nord and west <= eintrag["lon"] <= ost


def auswahl(boden, fundboden, funde_je_art):
    """Auswahlverhaeltnis: Bodenwerte an Fundorten gegen die Region."""
    r = rahmen(boden)
    if r:
        drin = {k: v for k, v in fundboden.items() if im_rahmen(v, r)}
        print("\n" + "=" * 58)
        print("Bevorzugen die Arten bestimmte Boeden?")
        print(f"Verglichen gegen: {MASSSTAB[0]}")
        print("=" * 58)
        print(f"Vergleichsgebiet: {round(r[0], 2)}-{round(r[2], 2)} Nord, "
              f"{round(r[1], 2)}-{round(r[3], 2)} Ost")
        print(f"{len(drin)} von {len(fundboden)} Fundorten liegen darin.")
        print("Die uebrigen fallen weg - sonst misst der Vergleich")
        print("Landschaft statt Pilzvorliebe.")
        fundboden = drin
    else:
        print("\n" + "=" * 58)
        print("Bevorzugen die Arten bestimmte Boeden?")
        print(f"Verglichen gegen: {MASSSTAB[0]}")
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


def vergleich_gesamt(boden, fundboden):
    """Grobvergleich Hintergrund gegen Fundorte, im selben Gebiet."""
    r = rahmen(boden)
    drin = [v for v in fundboden.values() if im_rahmen(v, r)]
    if len(drin) < 50:
        return

    print("\n\nHintergrund gegen Fundorte (gleiches Gebiet)")
    print(f"{'Groesse':<20}{'Hintergrund':>13}{'Fundorte':>11}"
          f"{'Unterschied':>13}")
    for feld, name, _, einheit in FELDER[:4]:
        h = quantile([b[feld] for b in boden.values()], [0.5])
        f = quantile([b[feld] for b in drin], [0.5])
        if not h or not f:
            continue
        d = f[0] - h[0]
        print(f"{name:<20}{round(h[0], 2):>13}{round(f[0], 2):>11}"
              f"{round(d, 2):>+13}")
    print(f"({len(drin)} Fundorte im Vergleichsgebiet)")


def main():
    boden = lade(BODEN)

    # Wenn die Meldeorte vorliegen, sind DIE der Massstab
    if os.path.exists(AUFWAND):
        aufwand = lade(AUFWAND)
        if len(aufwand) > 500:
            print(f"Massstab: {len(aufwand)} Pilzmeldeorte "
                  f"(statt {len(boden)} Waldpunkte)\n")
            print("Damit ist herausgerechnet, wo Menschen unterwegs")
            print("sind - es bleibt die Bodenvorliebe.\n")
            boden = aufwand
            MASSSTAB[0] = "Pilzmeldeorte"
        else:
            print(f"{AUFWAND} enthaelt nur {len(aufwand)} Orte - "
                  f"zu wenig.\n")
    else:
        print("ACHTUNG: Verglichen wird gegen zufaellige Waldpunkte.")
        print("Das misst zum Teil, wo Menschen unterwegs sind, nicht")
        print("nur die Bodenvorliebe. Fuer eine saubere Messung:")
        print("  python aufwand_orte.py")
        print("  python boden_aufwand.py\n")
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

    vergleich_gesamt(boden, fundboden)
    auswahl(boden, fundboden, funde_je_art)


main()
