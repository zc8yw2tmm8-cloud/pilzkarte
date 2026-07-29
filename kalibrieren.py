"""
Der Kern: vergleicht Fundbedingungen mit dem Normalzustand.

Ohne diesen Vergleich sagt "Funde bei 31 % Bodenfeuchte" nichts - man muss
wissen, was in der Region ueberhaupt normal ist. Das Verhaeltnis aus beiden
heisst Auswahlverhaeltnis (englisch selection ratio):

    Anteil der Funde in einem Wertebereich
    --------------------------------------  =  1.0 bedeutet: kein Signal
    Anteil der normalen Tage im Bereich        2.0 bedeutet: doppelt so oft

Der Vergleich laeuft nur innerhalb derselben Monate. Sonst misst man den
Herbst und nicht den Pilz.

Braucht: hintergrund.csv, funde_wetter2.csv, aufwand.csv
Ergebnis: Tabellen im Terminal und in kalibrierung.txt
"""
import csv
import os
from datetime import date
from collections import defaultdict

from kennwerte import berechne, zahl

HINTERGRUND = "hintergrund.csv"
FUNDE = "funde_wetter2.csv"
AUFWAND = "aufwand.csv"
BERICHT = "kalibrierung.txt"

MONATE = (6, 7, 8, 9, 10, 11)     # relevanter Zeitraum
SAISON = (9, 10, 11)              # Hauptsaison Steinpilz
STICHPROBE = 2                    # jeden n-ten Tag im Hintergrund auswerten

# Funde oberhalb dieser Hoehe weglassen. Der Hintergrund stammt aus dem
# Flachland; Bergland hat ein anderes Klima und waere kein fairer
# Vergleich. Gepruefte Wirkung: minimal, weil nur 11-19 % der Funde
# aus dem Bergland kommen. None schaltet den Filter ab.
HOEHE_MAX = 300

VARIABLEN = [
    ("bf07", "Bodenfeuchte 0-7cm", 100, "%"),
    ("bf728", "Bodenfeuchte 7-28cm", 100, "%"),
    ("bt07", "Bodentemp 0-7cm", 1, "C"),
    ("bt728", "Bodentemp 7-28cm", 1, "C"),
    ("temp", "Lufttemperatur", 1, "C"),
    ("regen_reife", "Regen Tag 4-14", 1, "mm"),
    ("regen_frisch", "Regen Tag 0-3", 1, "mm"),
    ("regentage", "Regentage von 14", 1, ""),
    ("tage_seit_regen", "Tage seit Regen", 1, "d"),
    ("regen_60", "Regen 60 Tage", 1, "mm"),
    ("bilanz_14", "Wasserbilanz 14 Tage", 1, "mm"),
    ("bilanz_60", "Wasserbilanz 60 Tage", 1, "mm"),
]

zeilen_bericht = []


def sag(text=""):
    print(text)
    zeilen_bericht.append(text)


def lade_hintergrund():
    """Liest die Tagesreihen und gruppiert sie nach Punkt."""
    punkte = defaultdict(list)

    with open(HINTERGRUND, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte[z["ort"]].append({
                "tag": date.fromisoformat(z["datum"]),
                "regen": zahl(z["regen"]),
                "temp": zahl(z["temp"]),
                "bt07": zahl(z["bt07"]),
                "bf07": zahl(z["bf07"]),
                "bt728": zahl(z["bt728"]),
                "bf728": zahl(z["bf728"]),
                "et0": zahl(z["et0"]),
                "hoehe": zahl(z["hoehe"]),
            })

    for ort in punkte:
        punkte[ort].sort(key=lambda r: r["tag"])

    return punkte


def hintergrund_kennwerte(punkte):
    """Rechnet fuer jeden n-ten Tag im relevanten Zeitraum die Kennwerte."""
    ergebnis = []

    for ort, reihe in punkte.items():
        n = len(reihe)
        for i in range(60, n):
            tag = reihe[i]["tag"]
            if tag.month not in MONATE:
                continue
            if i % STICHPROBE != 0:
                continue

            k = berechne(reihe[i - 61:i + 1], tag)
            if k is None:
                continue

            k["monat"] = tag.month
            k["hoehe"] = reihe[i].get("hoehe")
            ergebnis.append(k)

    return ergebnis


def lade_funde():
    funde = []
    zu_hoch = 0
    with open(FUNDE, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            if HOEHE_MAX is not None:
                h = zahl(z.get("hoehe"))
                if h is not None and h > HOEHE_MAX:
                    zu_hoch += 1
                    continue
            eintrag = {"art": z["art"], "monat": int(z["monat"])}
            for spalte in z:
                if spalte in ("art", "monat", "datum", "gbif_id"):
                    continue
                eintrag[spalte] = zahl(z[spalte])
            funde.append(eintrag)

    if zu_hoch:
        print(f"  {zu_hoch} Funde ueber {HOEHE_MAX} m weggelassen "
              f"(Bergland, anderes Klima)")
    return funde


def quantile(werte, anteile):
    werte = sorted(w for w in werte if w is not None)
    if not werte:
        return []
    return [werte[min(int(len(werte) * a), len(werte) - 1)] for a in anteile]


def auswahlverhaeltnis(funde, hintergrund, feld, faktor, einheit, titel):
    """Kernrechnung: Fundanteil je Klasse geteilt durch Hintergrundanteil."""
    h_werte = [h[feld] for h in hintergrund if h.get(feld) is not None]
    f_werte = [f[feld] for f in funde if f.get(feld) is not None]

    if len(h_werte) < 200 or len(f_werte) < 30:
        sag(f"  {titel}: zu wenig Daten "
            f"({len(f_werte)} Funde, {len(h_werte)} Hintergrund)")
        return None

    # Klassengrenzen aus dem Hintergrund - jede Klasse etwa 20 %
    grenzen = quantile(h_werte, [0.2, 0.4, 0.6, 0.8])
    grenzen = sorted(set(grenzen))

    if len(grenzen) < 2:
        sag(f"  {titel}: Werte zu einheitlich fuer Klassen")
        return None

    def klasse(wert):
        for i, g in enumerate(grenzen):
            if wert <= g:
                return i
        return len(grenzen)

    anzahl_klassen = len(grenzen) + 1
    h_zahl = [0] * anzahl_klassen
    f_zahl = [0] * anzahl_klassen

    for w in h_werte:
        h_zahl[klasse(w)] += 1
    for w in f_werte:
        f_zahl[klasse(w)] += 1

    sag(f"\n  {titel}  ({len(f_werte)} Funde)")
    sag(f"  {'Bereich':<22}{'Funde':>8}{'normal':>9}{'Verhaeltnis':>13}")

    ergebnis = []
    for i in range(anzahl_klassen):
        if i == 0:
            bereich = f"bis {round(grenzen[0] * faktor, 1)}"
        elif i == anzahl_klassen - 1:
            bereich = f"ab {round(grenzen[-1] * faktor, 1)}"
        else:
            bereich = (f"{round(grenzen[i-1] * faktor, 1)} - "
                       f"{round(grenzen[i] * faktor, 1)}")
        if einheit:
            bereich += f" {einheit}"

        f_anteil = f_zahl[i] / len(f_werte)
        h_anteil = h_zahl[i] / len(h_werte)
        verh = f_anteil / h_anteil if h_anteil > 0 else 0

        marker = ""
        if verh >= 1.5:
            marker = "  <<<"
        elif verh >= 1.15:
            marker = "  <"
        elif verh <= 0.5:
            marker = "  --"

        sag(f"  {bereich:<22}{f_anteil*100:7.1f}%{h_anteil*100:8.1f}%"
            f"{verh:12.2f}{marker}")

        ergebnis.append({
            "von": grenzen[i-1] if i > 0 else None,
            "bis": grenzen[i] if i < anzahl_klassen - 1 else None,
            "verhaeltnis": round(verh, 2),
        })

    return ergebnis


def saisonfaktor(funde_art, art):
    """Fundrate je Monat, korrigiert um den Sammleraufwand."""
    if not os.path.exists(AUFWAND):
        sag("  aufwand.csv fehlt - keine Aufwandskorrektur moeglich")
        return None

    aufwand = defaultdict(int)
    with open(AUFWAND, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            if z["anzahl"] == "":
                continue
            aufwand[int(z["monat"])] += int(z["anzahl"])

    funde_monat = defaultdict(int)
    for f in funde_art:
        funde_monat[f["monat"]] += 1

    # Monate mit sehr wenigen Vergleichsmeldungen sind unzuverlaessig -
    # aber sie ganz auf null zu setzen loescht echte Funde aus.
    MINDEST = 20
    roh = {}
    duenn = []
    for m in range(1, 13):
        n = aufwand.get(m, 0)
        if n < MINDEST:
            roh[m] = 0.0
            if funde_monat.get(m, 0) > 0:
                duenn.append(m)
        else:
            roh[m] = funde_monat.get(m, 0) / n

    hoechster = max(roh.values()) if roh else 0
    if hoechster <= 0:
        return None

    faktor = {m: round(roh[m] / hoechster, 2) for m in range(1, 13)}

    sag(f"\n  Saisonfaktor {art} (1.0 = beste Zeit)")
    if duenn:
        sag(f"  ACHTUNG: In Monat {duenn} gibt es Funde, aber unter "
            f"{MINDEST} Vergleichsmeldungen.")
        sag(f"  Diese Monate stehen auf 0 - pruefe sie von Hand.")
    sag(f"  {'Monat':<8}{'Funde':>7}{'alle Pilze':>12}{'Rate':>10}{'Faktor':>9}")
    for m in range(1, 13):
        sag(f"  {m:<8}{funde_monat.get(m,0):7d}{aufwand.get(m,0):12d}"
            f"{roh[m]*1000:10.2f}{faktor[m]:9.2f}")

    sag("\n  Zum Einsetzen in arten.py:")
    sag("  \"saison\": {" + ", ".join(f"{m}: {faktor[m]}" for m in range(1, 13))
        + "},")

    return faktor


def main():
    for pflicht in (HINTERGRUND, FUNDE):
        if not os.path.exists(pflicht):
            print(f"{pflicht} fehlt. Erst die vorherigen Skripte laufen lassen.")
            return

    print("Lese Hintergrund ...")
    punkte = lade_hintergrund()
    print(f"  {len(punkte)} Punkte")

    print("Rechne Hintergrund-Kennwerte (dauert etwas) ...")
    hintergrund = hintergrund_kennwerte(punkte)
    print(f"  {len(hintergrund)} Vergleichstage\n")

    funde = lade_funde()
    arten = sorted({f["art"] for f in funde})

    sag("=" * 62)
    sag("KALIBRIERUNG")
    sag("=" * 62)
    sag(f"Hintergrund: {len(hintergrund)} Punkt-Tage, Monate {MONATE}")
    sag(f"Funde: {len(funde)} in {len(arten)} Arten")
    sag()
    sag("Verhaeltnis 1.00 = Bedingung ist bei Funden genauso haeufig")
    sag("wie an normalen Tagen, also kein Signal.")
    sag("<<< starkes Signal   < schwaches Signal   -- gemieden")

    for art in arten:
        funde_art = [f for f in funde if f["art"] == art]
        if len(funde_art) < 40:
            sag(f"\n{'='*62}\n{art.upper()}: nur {len(funde_art)} Funde, "
                f"zu wenig fuer Kalibrierung\n")
            continue

        sag()
        sag("=" * 62)
        sag(f"{art.upper()}  ({len(funde_art)} Funde)")
        sag("=" * 62)

        saisonfaktor(funde_art, art)

        # Hauptsaison eingrenzen: nur Monate mit >=8 % der Funde
        monate_art = defaultdict(int)
        for f in funde_art:
            monate_art[f["monat"]] += 1
        kernmonate = tuple(m for m in range(1, 13)
                           if monate_art[m] >= len(funde_art) * 0.08)
        if len(kernmonate) < 2:
            kernmonate = SAISON

        sag(f"\n  Kernmonate: {kernmonate}")
        sag("  (Vergleich nur innerhalb dieser Monate - das trennt")
        sag("   Pilzsignal von Jahreszeit)")

        f_kern = [f for f in funde_art if f["monat"] in kernmonate]
        h_kern = [h for h in hintergrund if h["monat"] in kernmonate]

        for feld, titel, faktor, einheit in VARIABLEN:
            auswahlverhaeltnis(f_kern, h_kern, feld, faktor, einheit, titel)

    with open(BERICHT, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen_bericht))

    print(f"\n\nBericht in {BERICHT} gespeichert.")


main()