"""
Misst, welche Baumarten die Pilze tatsaechlich bevorzugen.

Bisher sind die Gewichte in arten.py aus der Pilzliteratur geschaetzt.
Dieses Skript vergleicht die Baumarten AN DEN FUNDORTEN mit denen in
der Region - dieselbe Methode wie bei Wetter und Boden.

Braucht nur, was schon da ist:
  kacheln/          die Baumartenkacheln von baumarten.py
  funde_arten.csv   die GBIF-Fundmeldungen

Ergebnis: Tabelle im Terminal und baumarten_gewichte.txt zum Einsetzen.
"""
import os
import csv
import math
from collections import Counter, defaultdict

import numpy as np
import protokoll
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

KACHELORDNER = "kacheln"
FUNDE_DATEI = "funde_arten.csv"
AUFWAND_DATEI = "aufwand_orte.csv"
AUSGABE = "baumarten_gewichte.txt"

# Gleiche Grenzen wie baumarten.py
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15
KACHELN_X, KACHELN_Y = 4, 4

# Fenster um einen Fundort, in Bildpunkten (10 m). 5 = 50 x 50 m.
# GBIF-Koordinaten sind selten punktgenau, ein Fenster faengt das ab.
FENSTER = 5

MAX_UNSICHERHEIT = 500     # ungenauere Fundorte weglassen
MINDEST_FUNDE = 40         # weniger sagt nichts

# Ab welcher Spreizung der Bestandsfaktor voll wirkt.
#
# Spreizung = hoechstes Verhaeltnis geteilt durch niedrigstes. Bei
# 3.0 heisst das: Die beliebteste Baumart wird dreimal so oft
# gefunden wie die unbeliebteste - eine klare Bindung, der Faktor
# spreizt dann von 1.0 bis hinunter zum gemessenen Wert.
#
# Liegt die Spreizung nur bei 1.5, ist die Bindung schwach und die
# Gewichte bleiben nah beieinander. Das verhindert, dass die
# Normierung Kontrast erfindet, wo keiner gemessen wurde.
SPANNE_VOLL = 3.0

# Mindestzahl FUNDORTE je Baumart, nicht nur insgesamt.
#
# Gemessen an 42 Steinpilz-Fundorten: Die Fichte machte 3.6 % der
# Bildpunkte aus - das sind ein bis zwei Fundorte. Das Verhaeltnis
# von 1.70 kam also aus zwei Beobachtungen und ist Rauschen. Die
# Erle stand bei drei Arten mit starkem Signal da, jedes Mal auf
# Grundlage von ein bis drei Fundorten.
#
# Baumarten unter dieser Schwelle bekommen den Mittelwert statt
# eines erfundenen Werts.
MINDEST_ORTE = 6

# Nur die Kernmonate der jeweiligen Art vergleichen.
#
# Steinpilzfunde liegen im September, die Meldeorte verteilen sich
# ueber das ganze Jahr. Wer im Fruehjahr andere Waelder besucht als
# im Herbst, verzerrt den Vergleich. Braucht die Spalte "monat" in
# aufwand_orte.csv.
NUR_KERNMONATE = True
MONATSANTEIL = 0.08        # ab wann ein Monat als Kernmonat gilt

KLASSEN = {
    2: "birke", 3: "buche", 4: "douglasie", 5: "eiche", 6: "erle",
    8: "fichte", 9: "kiefer", 10: "laerche", 14: "tanne",
    16: "laub_lang", 17: "laub_kurz",
}

NAMEN = {
    "birke": "Birke", "buche": "Buche", "douglasie": "Douglasie",
    "eiche": "Eiche", "erle": "Erle", "fichte": "Fichte",
    "kiefer": "Kiefer", "laerche": "Laerche", "tanne": "Tanne",
    "laub_lang": "sonst. Laubholz lang", "laub_kurz": "sonst. Laubholz kurz",
}


def lade_raster():
    """Setzt die Kacheln zu einem Bild zusammen."""
    teile = {}
    breiten = [0] * KACHELN_X
    hoehen = [0] * KACHELN_Y

    for iy in range(KACHELN_Y):
        for ix in range(KACHELN_X):
            pfad = os.path.join(KACHELORDNER, f"k_{iy}_{ix}.tif")
            if not os.path.exists(pfad):
                return None
            bild = np.array(Image.open(pfad))
            if bild.ndim == 3:
                bild = bild[:, :, 0]
            teile[(iy, ix)] = bild
            hoehen[iy] = max(hoehen[iy], bild.shape[0])
            breiten[ix] = max(breiten[ix], bild.shape[1])

    voll = np.zeros((sum(hoehen), sum(breiten)), dtype=np.uint8)
    for iy in range(KACHELN_Y):
        for ix in range(KACHELN_X):
            bild = teile[(iy, ix)]
            # Kachelzeile 0 liegt im Sueden, im Bild also unten
            y = sum(hoehen[KACHELN_Y - 1 - j] for j in range(KACHELN_Y - 1 - iy))
            x = sum(breiten[:ix])
            voll[y:y + bild.shape[0], x:x + bild.shape[1]] = bild
    return voll


def bildpunkt(lat, lon, form):
    hoehe, breite = form
    x = int((lon - WEST) / (OST - WEST) * breite)
    y = int((NORD - lat) / (NORD - SUED) * hoehe)
    if 0 <= x < breite and 0 <= y < hoehe:
        return y, x
    return None


def lade_funde():
    """
    Fundorte je Art als (lat, lon, monat).

    Dubletten werden entfernt - dasselbe Raster wie in
    aufwand_orte.py und funde_wetter2.py, damit Funde und
    Hintergrund vergleichbar bleiben.
    """
    funde = defaultdict(list)
    gesehen = set()
    if not os.path.exists(FUNDE_DATEI):
        return funde
    with open(FUNDE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                lat, lon = float(z["lat"]), float(z["lon"])
            except (ValueError, KeyError):
                continue
            if not (SUED <= lat <= NORD and WEST <= lon <= OST):
                continue
            u = z.get("unsicherheit_m", "")
            if u not in ("", None):
                try:
                    if float(u) > MAX_UNSICHERHEIT:
                        continue
                except ValueError:
                    pass
            datum = (z.get("datum") or "")[:10]
            schluessel = (z["art"], datum,
                          round(lat, 3), round(lon, 3))
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)

            monat = None
            if len(datum) >= 7:
                try:
                    monat = int(datum[5:7])
                except ValueError:
                    pass

            funde[z["art"]].append((lat, lon, monat))
    return funde


def orte_auszaehlen(raster, orte):
    """
    Baumarten in einem Fenster um jeden Ort zaehlen.

    Zaehlt zweierlei: die Bildpunkte je Baumart (fuer die Anteile)
    und die Zahl der ORTE, an denen eine Baumart ueberhaupt
    vorkommt. Das zweite entscheidet, ob ein Wert belastbar ist -
    3 % Bildpunkte koennen von einem einzigen Fundort stammen.
    """
    treffer = Counter()
    orte_je_art = Counter()
    ohne_wald = 0
    im_bild = 0

    for lat, lon in orte:
        p = bildpunkt(lat, lon, raster.shape)
        if p is None:
            continue
        im_bild += 1
        y, x = p
        y0, y1 = max(0, y - FENSTER), min(raster.shape[0], y + FENSTER + 1)
        x0, x1 = max(0, x - FENSTER), min(raster.shape[1], x + FENSTER + 1)
        fenster = raster[y0:y1, x0:x1]
        wald = fenster[fenster > 0]
        if wald.size == 0:
            ohne_wald += 1
            continue
        hier = set()
        for w, n in zip(*np.unique(wald, return_counts=True)):
            if int(w) in KLASSEN:
                treffer[KLASSEN[int(w)]] += int(n)
                # Nur zaehlen, wenn die Baumart hier nennenswert
                # vertreten ist - ein einzelner Bildpunkt am Rand
                # des Fensters macht keinen Fundort aus
                if n >= wald.size * 0.05:
                    hier.add(KLASSEN[int(w)])
        for a in hier:
            orte_je_art[a] += 1

    return treffer, im_bild, ohne_wald, orte_je_art


def lade_aufwandsorte():
    """
    Fundorte aller Pilzmeldungen - der Massstab fuer Sammlerdichte.

    Rueckgabe: Liste von (lat, lon, monat). Der Monat ist None, wenn
    die Datei noch aus einem alten Lauf ohne Datum stammt.
    """
    if not os.path.exists(AUFWAND_DATEI):
        return []
    orte = []
    ohne_monat = 0
    with open(AUFWAND_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            try:
                lat, lon = float(z["lat"]), float(z["lon"])
            except (ValueError, KeyError):
                continue
            try:
                monat = int(z["monat"])
            except (ValueError, KeyError, TypeError):
                monat = None
                ohne_monat += 1
            orte.append((lat, lon, monat))

    if ohne_monat:
        print(f"  {ohne_monat} Meldeorte ohne Monat - "
              f"{AUFWAND_DATEI} stammt aus einem alten Lauf.")
        print("  Fuer den Monatsvergleich: python aufwand_orte.py")
    return orte


def kernmonate(orte):
    """
    Monate, in denen ein nennenswerter Teil der Funde liegt.

    orte: Liste von (lat, lon, monat)
    """
    zaehler = Counter(o[2] for o in orte if o[2] is not None)
    if not zaehler:
        return None
    grenze = sum(zaehler.values()) * MONATSANTEIL
    return {m for m, n in zaehler.items() if n >= grenze}


def main():
    print("Lese Baumartenkacheln ...")
    raster = lade_raster()
    if raster is None:
        print(f"Kacheln in {KACHELORDNER}/ fehlen. Erst baumarten.py.")
        return
    print(f"  {raster.shape[1]} x {raster.shape[0]} Bildpunkte")

    # Hintergrund: alle Waldpunkte der Region
    werte, anzahl = np.unique(raster[raster > 0], return_counts=True)
    hintergrund = Counter()
    for w, n in zip(werte.tolist(), anzahl.tolist()):
        if w in KLASSEN:
            hintergrund[KLASSEN[w]] += n
    gesamt_hg = sum(hintergrund.values())

    print(f"  {gesamt_hg} Waldbildpunkte in der Region\n")
    print("Baumarten in der Region:")
    for art, n in hintergrund.most_common():
        print(f"  {NAMEN[art]:24s}{n / gesamt_hg * 100:6.1f} %")

    # Wenn Meldeorte aller Pilze vorliegen, sind DIE der Massstab.
    # Sonst misst der Vergleich nur, wo Menschen spazieren gehen.
    massstab_text = "in Region"
    aufwandsorte = lade_aufwandsorte()
    hat_monate = any(o[2] is not None for o in aufwandsorte)

    if aufwandsorte:
        a_treffer, a_im_bild, a_ohne, _ = orte_auszaehlen(
            raster, [(o[0], o[1]) for o in aufwandsorte])
        if sum(a_treffer.values()) > 10000:
            hintergrund = a_treffer
            gesamt_hg = sum(hintergrund.values())
            massstab_text = "bei Sammlern"
            print(f"\nMassstab: {a_im_bild} Meldeorte aller Pilze "
                  f"({a_ohne} ausserhalb des Waldes)")
            print("Baumarten an Meldeorten:")
            for art, n in hintergrund.most_common():
                print(f"  {NAMEN[art]:24s}{n / gesamt_hg * 100:6.1f} %")
        else:
            print("\nZu wenige Meldeorte - vergleiche gegen die Region.")
    else:
        print(f"\n{AUFWAND_DATEI} fehlt - vergleiche gegen die Region.")
        print("ACHTUNG: Dann misst das Ergebnis zum grossen Teil, wo")
        print("Menschen unterwegs sind. Erst aufwand_orte.py laufen lassen.")

    funde = lade_funde()
    if not funde:
        print(f"\nKeine Funde in {FUNDE_DATEI} im Gebiet.")
        return

    zeilen_aus = []
    print("\n" + "=" * 66)
    if massstab_text == "bei Sammlern":
        print("Auswahlverhaeltnis: Baumart am Fundort gegen die Baumarten")
        print("an ALLEN Pilzmeldeorten - Sammlerdichte ist herausgerechnet")
    else:
        print("Auswahlverhaeltnis: Baumart am Fundort gegen Region")
        print("ACHTUNG: OHNE Aufwandskorrektur - erst aufwand_orte.py")
    print("1.00 = kein Signal, 2.00 = doppelt so haeufig wie zufaellig")
    print("=" * 66)

    for pilzart in sorted(funde):
        orte = funde[pilzart]
        treffer, im_bild, ohne_wald, orte_je_art = orte_auszaehlen(
            raster, [(o[0], o[1]) for o in orte])

        gesamt = sum(treffer.values())
        # Hintergrund auf die Kernmonate dieser Art begrenzen.
        # Sonst werden Septemberfunde gegen ganzjaehrige Meldeorte
        # gehalten - und wer im Fruehjahr andere Waelder besucht,
        # verzerrt den Vergleich.
        art_hintergrund = hintergrund
        art_gesamt_hg = gesamt_hg
        if NUR_KERNMONATE and hat_monate and massstab_text == "bei Sammlern":
            kern = kernmonate(orte)
            if kern and len(kern) < 12:
                teil = [(o[0], o[1]) for o in aufwandsorte
                        if o[2] in kern]
                if len(teil) > 300:
                    k_treffer, _, _, _ = orte_auszaehlen(raster, teil)
                    if sum(k_treffer.values()) > 3000:
                        art_hintergrund = k_treffer
                        art_gesamt_hg = sum(k_treffer.values())
                        monatstext = ", ".join(str(m)
                                               for m in sorted(kern))
                        print(f"  Hintergrund auf Monate "
                              f"{monatstext} begrenzt "
                              f"({len(teil)} Meldeorte)")

        if gesamt == 0 or im_bild - ohne_wald < MINDEST_FUNDE:
            print(f"\n{pilzart.upper()}: nur "
                  f"{im_bild - ohne_wald} Fundorte im Wald, zu wenig")
            continue

        print(f"\n{pilzart.upper()}  ({im_bild - ohne_wald} Fundorte im "
              f"Wald, {ohne_wald} ausserhalb)")
        print(f"  {'Baumart':<24}{'Fundort':>10}{'Sammler':>10}"
              f"{'Verh.':>10}{'Orte':>7}")

        verhaeltnisse = {}
        for art in sorted(art_hintergrund,
                          key=lambda a: -art_hintergrund[a]):
            h_anteil = art_hintergrund[art] / art_gesamt_hg
            f_anteil = treffer.get(art, 0) / gesamt
            if h_anteil < 0.002:
                continue
            v = f_anteil / h_anteil if h_anteil else 0
            n_orte = orte_je_art.get(art, 0)

            # Nur werten, wenn genug verschiedene Fundorte dahinter
            # stehen. Sonst stammt das Verhaeltnis aus ein, zwei
            # Beobachtungen.
            belastbar = n_orte >= MINDEST_ORTE
            if belastbar:
                verhaeltnisse[art] = v

            if not belastbar:
                marke = f"  ({n_orte} Orte, zu wenig)"
            elif v >= 1.5:
                marke = "  <<<"
            elif v >= 1.15:
                marke = "  <"
            elif v <= 0.6:
                marke = "  --"
            else:
                marke = ""

            print(f"  {NAMEN[art]:<24}{f_anteil*100:9.1f}%"
                  f"{h_anteil*100:10.1f}%{v:10.2f}{n_orte:>7}{marke}")

        # Gewichte aus den Verhaeltnissen.
        #
        # FRUEHER: hoechstes Verhaeltnis wird 1.0, der Rest anteilig.
        # Das erzeugt Kontrast, wo keiner ist: Hat eine Art nur eine
        # schwache Baumbindung (bestes Verhaeltnis 1.2), bekam der
        # Spitzenreiter trotzdem 1.0 und alle anderen wurden
        # heruntergerechnet.
        #
        # JETZT: Das Verhaeltnis selbst ist das Gewicht, gestaucht um
        # den Punkt 1.0. Eine Art ohne Baumbindung bekommt damit
        # ueberall Werte nahe 1.0 - und der Bestandsfaktor wirkt
        # kaum, was richtig ist.
        # Der Faktor muss bei 1.0 enden - er daempft den Score, er
        # erhoeht ihn nicht. Deshalb bekommt die beste Baumart 1.0.
        #
        # Die Frage ist nur, wie weit die anderen darunter liegen.
        # Frueher wurde stur durch das Hoechste geteilt - das erzeugt
        # vollen Kontrast auch dort, wo die Verhaeltnisse dicht
        # beieinanderliegen.
        #
        # Jetzt richtet sich der Abstand danach, wie stark die
        # gemessene Bindung ueberhaupt ist: Spreizt sich das
        # Verhaeltnis um mehr als SPANNE_VOLL, wirkt der Faktor
        # vollstaendig. Liegt alles dicht beisammen, bleiben die
        # Gewichte nah an 1.0 und der Bestand spielt kaum eine Rolle.
        if len(verhaeltnisse) < 3:
            print(f"  -> nur {len(verhaeltnisse)} Baumarten mit "
                  f"mindestens {MINDEST_ORTE} Fundorten - zu wenig "
                  f"fuer Gewichte")
            continue

        # Woran wird normiert?
        #
        # Nicht am hoechsten Wert ueberhaupt: Beim Schwefelporling
        # stand die Erle mit 2.18 auf 10 Fundorten, die Eiche mit
        # 1.26 auf 69. Nimmt man die Erle als Anker, faellt die Eiche
        # auf 0.66 - der schwaecher gestuetzte Wert bestimmt die
        # ganze Skala.
        #
        # Deshalb: Anker ist der hoechste Wert unter den GUT
        # gestuetzten Baumarten. Was darueber liegt, bekommt
        # ebenfalls 1.0.
        gut = {a: v for a, v in verhaeltnisse.items()
               if orte_je_art.get(a, 0) >= MINDEST_ORTE * 2}
        anker = max(gut.values()) if gut else max(
            verhaeltnisse.values(), default=1.0)

        werte = [v for v in verhaeltnisse.values() if v > 0]
        niedrigstes = min(werte) if werte else 1.0
        spreizung = anker / max(0.05, niedrigstes)

        if gut:
            beste = max(gut, key=gut.get)
            print(f"\n  Anker: {NAMEN[beste]} mit {anker:.2f} "
                  f"({orte_je_art.get(beste, 0)} Orte)")

        staerke = min(1.0, (spreizung - 1.0) / SPANNE_VOLL)
        staerke = max(0.0, staerke)

        gewichte = {}
        for a, v in verhaeltnisse.items():
            anteil = min(1.0, v / anker) if anker else 1.0
            gewichte[a] = round(
                max(0.05, 1.0 - (1.0 - anteil) * staerke), 2)

        print(f"  Spreizung {spreizung:.2f}x -> Bindungsstaerke "
              f"{staerke:.2f}")
        if staerke < 0.4:
            print("  -> schwache Baumbindung, Gewichte bleiben nah "
                  "bei 1.0")


        # KEINE Behelfswerte fuer ungemessene Baumarten.
        #
        # Frueher wurde hier der Mittelwert eingesetzt. Das hat gut
        # gestuetzte alte Werte ueberschrieben - beim
        # Schwefelporling waere Fichte von 0.06 (aus 1141 Funden)
        # auf 0.63 gesprungen, nur weil in diesem Lauf drei
        # Fundorte zu wenig waren.
        #
        # Was hier fehlt, behaelt in arten.py seinen bisherigen
        # Wert. gewichte_uebernehmen.py fuegt nur ein, was
        # dasteht.

        text = ('        "baumarten": {'
                + ", ".join(f'"{a}": {gewichte[a]}' for a in
                            sorted(gewichte, key=lambda x: -gewichte[x]))
                + "},")
        zeilen_aus.append(f"# {pilzart}\n{text}\n")

    if zeilen_aus:
        kopf = (f"# Massstab: {massstab_text}\n"
                f"# {'MIT' if massstab_text == 'bei Sammlern' else 'OHNE'} "
                f"Aufwandskorrektur\n\n")
        with open(AUSGABE, "w", encoding="utf-8") as f:
            f.write(kopf + "\n".join(zeilen_aus))
        print(f"\n\nGewichte zum Einsetzen liegen in {AUSGABE}.")
        print("Vorher lesen - Beobachterverzerrung ist hier besonders")
        print("wahrscheinlich, weil Eichenwaelder oft naeher an Ortschaften")
        print("liegen als Kiefernforste.")

    # Festhalten, woraus diese Gewichte entstanden sind
    protokoll.notiere(
        "Baumartengewichte",
        [FUNDE_DATEI, AUFWAND_DATEI],
        {"MINDEST_FUNDE": MINDEST_FUNDE,
         "SPANNE_VOLL": SPANNE_VOLL,
         "MINDEST_ORTE": MINDEST_ORTE,
         "NUR_KERNMONATE": NUR_KERNMONATE,
         "MONATSANTEIL": MONATSANTEIL},
        {"Massstab": massstab_text,
         "Meldeorte": len(aufwandsorte),
         "Ausgabe": AUSGABE})


main()