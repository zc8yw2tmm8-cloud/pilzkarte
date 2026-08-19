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
import protokoll
import os
from datetime import date
from collections import defaultdict

from kennwerte import berechne, zahl

HINTERGRUND = "hintergrund.csv"
FUNDE = "funde_wetter2.csv"
AUFWAND = "aufwand.csv"

# Meldetage: An welchen Tagen wurde ueberhaupt gesammelt?
#
# Der Grund ist derselbe wie bei den Baumarten und beim Boden:
# Menschen gehen nicht zufaellig in den Wald. Sie gehen nach Regen,
# weil sie wissen, dass dann Pilze kommen. Vergleicht man Fundtage
# mit ZUFAELLIGEN Tagen, misst man dieses Verhalten mit.
#
# Gemessen macht das bis zu zwei Drittel des Effekts aus: Beim
# Sommersteinpilz fiel das Verhaeltnis bei viel Regen von 3.05 auf
# 1.22, sobald gegen Meldetage verglichen wurde.
#
# Jeder Hintergrundtag wird deshalb mit der Zahl der Meldungen
# dieses Tages gewichtet. Tage, an denen niemand draussen war,
# zaehlen gar nicht.
MELDETAGE = "aufwand_tage.csv"
BERICHT = "kalibrierung.txt"

MONATE = (6, 7, 8, 9, 10, 11)     # relevanter Zeitraum
SAISON = (9, 10, 11)              # Hauptsaison Steinpilz
# Jeden n-ten Tag im Hintergrund auswerten.
#
# 1 = alle Tage. Das kostet Rechenzeit, ist aber noetig: Seit die
# Vergleichstage nach Meldungen gewichtet werden, sind die
# Auswahlverhaeltnisse deutlich naeher an 1.0 - und um einen
# Unterschied zwischen 1.17 und 0.85 von Zufall zu trennen, braucht
# es mehr Vergleichstage, nicht weniger.
STICHPROBE = 1

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
            # Wird fuer die Gewichtung nach Meldetagen gebraucht
            k["tag"] = tag
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


def quantile_gewichtet(werte, gewichte, anteile):
    """
    Quantile mit Gewichten.

    Ohne Gewichte waeren die Klassengrenzen an zufaelligen Tagen
    ausgerichtet, die Anteile aber an Meldetagen - beides muss
    zusammenpassen.
    """
    paare = sorted((w, g) for w, g in zip(werte, gewichte) if g > 0)
    if not paare:
        return quantile(werte, anteile)

    gesamt = sum(g for _, g in paare)
    ergebnis = []
    for p in anteile:
        ziel = gesamt * p
        summe = 0.0
        gewaehlt = paare[-1][0]
        for w, g in paare:
            summe += g
            if summe >= ziel:
                gewaehlt = w
                break
        ergebnis.append(gewaehlt)
    return ergebnis


def lade_meldetage():
    """Zahl der Pilzmeldungen je Tag. Leer, wenn die Datei fehlt."""
    if not os.path.exists(MELDETAGE):
        return {}
    with open(MELDETAGE, "r", encoding="utf-8") as f:
        return {z["datum"]: int(z["meldungen"])
                for z in csv.DictReader(f)}


MELDUNGEN = {}


def auswahlverhaeltnis(funde, hintergrund, feld, faktor, einheit, titel):
    """Kernrechnung: Fundanteil je Klasse geteilt durch Hintergrundanteil."""
    # Jeder Hintergrundtag mit der Zahl der Meldungen gewichtet.
    # Ohne Meldedaten zaehlt jeder Tag gleich - dann ist es die
    # alte, verzerrte Rechnung.
    paare = [(h[feld],
              MELDUNGEN.get(h["tag"].isoformat(), 0) if MELDUNGEN else 1.0)
             for h in hintergrund if h.get(feld) is not None]
    h_werte = [w for w, g in paare]
    h_gewichte = [g for w, g in paare]
    f_werte = [f[feld] for f in funde if f.get(feld) is not None]

    if len(h_werte) < 200 or len(f_werte) < 30:
        sag(f"  {titel}: zu wenig Daten "
            f"({len(f_werte)} Funde, {len(h_werte)} Hintergrund)")
        return None

    # Klassengrenzen aus dem Hintergrund - jede Klasse etwa 20 %.
    # Ebenfalls gewichtet: Ein Tag mit zehn Meldungen soll die
    # Grenzen staerker bestimmen als einer mit einer.
    grenzen = quantile_gewichtet(h_werte, h_gewichte,
                                 [0.2, 0.4, 0.6, 0.8])
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
    h_zahl = [0.0] * anzahl_klassen
    f_zahl = [0.0] * anzahl_klassen

    for w, g in zip(h_werte, h_gewichte):
        h_zahl[klasse(w)] += g
    for w in f_werte:
        f_zahl[klasse(w)] += 1

    # Durch die SUMME DER GEWICHTE teilen, nicht durch die Anzahl.
    # Sonst summieren sich die Anteile auf ein Vielfaches von 100 %
    # und alle Verhaeltnisse sind um denselben Faktor zu klein.
    h_summe = sum(h_zahl)
    f_summe = sum(f_zahl)
    if h_summe <= 0 or f_summe <= 0:
        sag(f"  {titel}: keine gewichteten Vergleichstage")
        return None

    sag(f"\n  {titel}  ({len(f_werte)} Funde)")
    sag(f"  {'Bereich':<22}{'Funde':>8}{'normal':>9}"
        f"{'Verhaeltnis':>14}")

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

        f_anteil = f_zahl[i] / f_summe
        h_anteil = h_zahl[i] / h_summe
        verh = f_anteil / h_anteil if h_anteil > 0 else 0

        # Wie sicher ist dieses Verhaeltnis? Bei wenigen Funden je
        # Klasse schwankt es stark. Die Faustformel: Der relative
        # Fehler liegt bei etwa 1/Wurzel(Anzahl).
        n_klasse = f_zahl[i]
        streuung = (verh / (n_klasse ** 0.5)) if n_klasse >= 1 else 0

        # Nur als Signal werten, was groesser ist als die Streuung.
        # Ein Verhaeltnis von 1.3 bei 9 Funden sagt nichts - dort
        # liegt die Streuung bei 0.43.
        deutlich = streuung > 0 and abs(verh - 1.0) > 2 * streuung

        marker = ""
        if not deutlich:
            marker = "  (unsicher)"
        elif verh >= 1.5:
            marker = "  <<<"
        elif verh >= 1.15:
            marker = "  <"
        elif verh <= 0.7:
            marker = "  --"

        sag(f"  {bereich:<22}{f_anteil*100:7.1f}%{h_anteil*100:8.1f}%"
            f"{verh:8.2f} \u00b1{streuung:5.2f}{marker}")

        ergebnis.append({
            "von": grenzen[i-1] if i > 0 else None,
            "bis": grenzen[i] if i < anzahl_klassen - 1 else None,
            "verhaeltnis": round(verh, 2),
            "streuung": round(streuung, 2),
            "deutlich": deutlich,
            "funde": int(f_zahl[i]),
        })

    sicher = sum(1 for e in ergebnis if e["deutlich"])
    if sicher == 0:
        sag("    -> kein belastbares Signal "
            "(alle Werte im Bereich der Streuung)")
    elif sicher < len(ergebnis) // 2:
        sag(f"    -> nur {sicher} von {len(ergebnis)} Klassen "
            f"belastbar")

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
    global MELDUNGEN
    MELDUNGEN = lade_meldetage()
    hintergrund = hintergrund_kennwerte(punkte)

    if MELDUNGEN:
        # Pruefen, ob genug Hintergrundtage ueberhaupt Meldungen
        # haben - sonst waere die Gewichtung auf wenige Tage
        # gestuetzt und damit unzuverlaessig
        mit = sum(1 for h in hintergrund
                  if MELDUNGEN.get(h["tag"].isoformat(), 0) > 0)
        anteil = mit / max(1, len(hintergrund))

        if anteil < 0.25:
            sag(f"ACHTUNG: Nur {mit} von {len(hintergrund)} "
                f"Vergleichstagen haben Meldungen ({anteil*100:.0f} %).")
            sag("Zu wenig fuer eine belastbare Gewichtung - es wird")
            sag("gegen alle Tage gerechnet.\n")
            MELDUNGEN = {}
        else:
            sag(f"Massstab: {mit} von {len(hintergrund)} "
                f"Vergleichstagen mit Meldungen ({anteil*100:.0f} %)")
            sag("Damit ist das Sammlerverhalten herausgerechnet - es")
            sag("bleibt der Zusammenhang mit den Pilzen.\n")
    else:
        sag(f"ACHTUNG: {MELDETAGE} fehlt.")
        sag("Verglichen wird gegen ZUFAELLIGE Tage. Das misst zum")
        sag("Teil, wann Menschen sammeln gehen - nicht nur, wann")
        sag("Pilze wachsen. Fuer eine saubere Messung erst:")
        sag("  python aufwand_tage.py\n")
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

    # Festhalten, woraus diese Kalibrierung entstanden ist - sonst
    # ist sie spaeter nicht nachvollziehbar
    protokoll.notiere(
        "Wetterbaender und Saison",
        [HINTERGRUND, FUNDE, AUFWAND, MELDETAGE],
        {"MONATE": str(MONATE), "STICHPROBE": STICHPROBE,
         "gegen_Meldetage": bool(MELDUNGEN),
         "WETTER_SPANNE in arten.py": arten.WETTER_SPANNE},
        {"Vergleichstage": len(hintergrund),
         "Meldetage": len(MELDUNGEN),
         "Funde gesamt": sum(len(v) for v in funde.values()),
         "Arten": len(funde),
         "Bericht": BERICHT})


main()
