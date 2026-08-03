"""
Pilzarten und ihre Anforderungen - die einzige Datei zum Nachjustieren.

Aufbau je Groesse: Liste von (von, bis, punkte). None = offenes Ende.
Die erste passende Zeile gewinnt. Summe der Bestwerte = 100.

Endscore = Wetterpunkte x Saison x Waldtyp x Boden

HERKUNFT DER ZAHLEN
Die Wetterbaender und Saisonfaktoren sind an 2819 GBIF-Funden gegen
rund 47.000 Vergleichstage gemessen (Auswahlverhaeltnis, siehe
kalibrieren.py). Die Boden- und Waldtypfaktoren sind noch geschaetzt.
"""

SAISON_STAERKE = 0.85

# Untergrenze fuer den Bodenfaktor. 0.5 heisst: der Boden kann den
# Score halbieren, aber nicht ausloeschen.
BODEN_MINDEST = 0.5

# Weiche Saisonkurve: zwischen den Monatswerten wird interpoliert,
# statt am Monatsersten zu springen.
SAISON_WEICH = True

# Wie stark ein geringer Waldanteil in der Zelle daempft.
#
# ACHTUNG, das ist eine heiklere Groesse als sie aussieht:
#
# Der Waldanteil misst, wie wahrscheinlich eine ZUFAELLIGE Stelle in
# der Zelle Wald ist. Das beantwortet die Frage "wie viele Pilze
# stehen in dieser Zelle insgesamt".
#
# Ein Sammler fragt aber etwas anderes: "Wenn ich in DEM Waldstueck
# dort suche - wie stehen meine Chancen?" Dafuer ist es gleichgueltig,
# ob drumherum Acker liegt. Niemand sucht auf dem Acker.
#
# Deshalb daempft der Waldanteil nur noch schwach. Was bleibt, ist
# nicht die Trefferwahrscheinlichkeit, sondern der Umstand, dass ein
# kleines Waldstueck weniger Flaeche zum Absuchen bietet - und dass
# bei sehr wenig Wald die Baumartenangabe unsicherer wird, weil sie
# aus wenigen Bildpunkten stammt.
#
# Frueher standen hier Werte bis 0.40. Das hat kleine Waelder
# bestraft, ohne dass es dem Sammler etwas gesagt haette.
WALDANTEIL_WIRKUNG = 0.10

# Unterhalb dieses Waldanteils wird staerker gedaempft - dort ist
# nicht die Pilzdichte das Problem, sondern die Datenlage: Baumarten
# und Boden stammen dann aus einer sehr kleinen Flaeche.
WALDANTEIL_UNSICHER = 0.04


# Klassen der Thuenen-Baumartenkarte (Blickensdoerfer et al. 2024).
# Die englischen Namen kommen so aus dem Dienst.
BAUMART_SCHLUESSEL = {
    "Birch (Betula spp)": "birke",
    "Beech (Fagus sylvatica)": "buche",
    "Douglas fir (Pseudotsuga menziesii)": "douglasie",
    "Oak (Quercus spp)": "eiche",
    "Alder (Alnus spp)": "erle",
    "Spruce (Picea spp)": "fichte",
    "Pine (Pinus spp)": "kiefer",
    "Larch (Larix spp)": "laerche",
    "Fir (Abies spp)": "tanne",
    "Other deciduous - high life expectancy": "laub_lang",
    "Other deciduous \u2013 low life expectancy": "laub_kurz",
    "Other deciduous - low life expectancy": "laub_kurz",
}

# Rohe Klassenwerte der Karte - fuer Dateien, die vor dem Auslesen
# der Legende entstanden sind und deshalb Zahlen statt Namen enthalten
BAUMART_WERTE = {
    2: "birke", 3: "buche", 4: "douglasie", 5: "eiche", 6: "erle",
    8: "fichte", 9: "kiefer", 10: "laerche", 14: "tanne",
    16: "laub_lang", 17: "laub_kurz",
}

# Dieselben Klassen ueber die Zahlenwerte - falls baumarten.py lief,
# bevor die Legende lesbar war.
BAUMART_CODE = {
    2: "birke", 3: "buche", 4: "douglasie", 5: "eiche", 6: "erle",
    8: "fichte", 9: "kiefer", 10: "laerche", 14: "tanne",
    16: "laub_lang", 17: "laub_kurz",
}

# Dieselben Klassen ueber ihre Zahlenwerte. baumarten.py schreibt
# Zahlen, wenn die Legende beim Lauf nicht erreichbar war.
BAUMART_WERTE = {
    2: "birke", 3: "buche", 4: "douglasie", 5: "eiche", 6: "erle",
    8: "fichte", 9: "kiefer", 10: "laerche", 14: "tanne",
    16: "laub_lang", 17: "laub_kurz",
}

# Dieselbe Zuordnung ueber die Klassenwerte - falls baumarten.csv
# ohne Legende erzeugt wurde und Zahlen statt Namen enthaelt.
BAUMART_WERTE = {
    2: "birke", 3: "buche", 4: "douglasie", 5: "eiche", 6: "erle",
    8: "fichte", 9: "kiefer", 10: "laerche", 14: "tanne",
    16: "laub_lang", 17: "laub_kurz",
}

BAUMART_NAMEN = {
    "birke": "Birke", "buche": "Buche", "douglasie": "Douglasie",
    "eiche": "Eiche", "erle": "Erle", "fichte": "Fichte",
    "kiefer": "Kiefer", "laerche": "Laerche", "tanne": "Tanne",
    "laub_lang": "sonst. Laubholz (langlebig)",
    "laub_kurz": "sonst. Laubholz (kurzlebig)",
}


ARTEN = {
    "steinpilz": {
        "name": "Steinpilz",
        "gbif": "Boletus edulis",
        # 403 Funde, Aug-Nov. Wasserbilanz ist der staerkste Einzelwert
        # (Verhaeltnis 0.12 bis 2.07).
        "bilanz_14": [(15, None, 22), (0, 15, 17), (-12, 0, 10),
                      (-30, -12, 3)],
        "bt07": [(9, 13, 22), (13, 16, 16), (7, 9, 10), (16, 19, 7),
                 (19, 21, 2)],
        "bf07": [(0.33, None, 18), (0.24, 0.33, 15), (0.20, 0.24, 8),
                 (0.17, 0.20, 3)],
        "regen_reife": [(34, None, 15), (24, 34, 12), (15, 24, 7),
                        (7, 15, 3)],
        "regentage": [(8, None, 15), (6, 8, 11), (5, 6, 7), (3, 5, 4)],
        "temp": [(10, 16, 8), (16, 18, 4), (8, 10, 4)],
        "verzug": (10, 16),   # Tage vom Regenereignis bis zum Schub
        # Gemessen an 53 Fundorten: Ton ueber 20 % Verhaeltnis 1.81,
        # pH ueber 6.1 nur 0.23
        "boden_ph": [(5.0, 6.1, 1.0), (4.6, 5.0, 0.85), (6.1, 6.6, 0.6),
                     (None, 4.6, 0.7), (6.6, None, 0.5)],
        "boden_ton": [(19, None, 1.0), (15, 19, 0.9), (12, 15, 0.7),
                      (None, 12, 0.65)],
        # auch Parkbaeume und Alleen, aber Schwerpunkt Wald
        # Gemessen (n=43, Sammlerdichte herausgerechnet): Fichte 1.67,
        # Buche 1.37, Kiefer 1.16 - bestaetigt die Literatur.
        # Birke 0.44 und Erle 0.27 nach unten gezogen.
        "baumarten": {"fichte": 1.0, "buche": 1.0, "tanne": 0.9,
                      "kiefer": 0.85, "eiche": 0.75, "douglasie": 0.45,
                      "laerche": 0.5, "laub_lang": 0.45, "birke": 0.25,
                      "laub_kurz": 0.25, "erle": 0.12},
        "waldanteil_wirkung": 0.10,
        # gemessen: leicht 0.71, stark 0.23 (nur Nov)
        "frost_abzug": (15, 40),   # (leichter, starker Frost)
        "saison": {1: 0.0, 2: 0.01, 3: 0.0, 4: 0.0, 5: 0.02, 6: 0.02,
                   7: 0.21, 8: 0.37, 9: 1.00, 10: 0.70, 11: 0.44, 12: 0.04},
        # Mykorrhiza mit Fichte, Buche, Kiefer, Eiche - breit aufgestellt
        "baumarten": {"fichte": 1.0, "buche": 1.0, "tanne": 0.9,
                      "kiefer": 0.85, "eiche": 0.8, "douglasie": 0.5,
                      "laerche": 0.5, "laub_lang": 0.5, "birke": 0.4,
                      "laub_kurz": 0.3, "erle": 0.2},
        "waldtyp": {"laub": 1.0, "misch": 1.0, "nadel": 0.95,
                    "bruch": 0.4, "unbekannt": 0.95},
    },

    "sommersteinpilz": {
        "name": "Sommersteinpilz",
        "gbif": "Boletus reticulatus",
        # 92 Funde, Jun-Aug. KORREKTUR: nicht waermeliebend im Tagesverlauf.
        # Unter 17.4 C Bodentemperatur Verhaeltnis 2.26, ueber 21.3 nur 0.23.
        "bilanz_14": [(-5, None, 22), (-24, -5, 15), (-37, -24, 8),
                      (-50, -37, 3)],
        "bt07": [(None, 17.5, 22), (17.5, 19, 13), (19, 20, 8),
                 (20, 21.5, 4)],
        "bf07": [(0.29, None, 20), (0.24, 0.29, 15), (0.20, 0.24, 7),
                 (0.15, 0.20, 2)],
        "regen_reife": [(38, None, 16), (25, 38, 12), (17, 25, 6),
                        (9, 17, 2)],
        "regentage": [(8, None, 14), (6, 8, 10), (5, 6, 5), (3, 5, 2)],
        "temp": [(None, 17, 6), (17, 18.5, 4), (18.5, 19.5, 2)],
        "verzug": (8, 14),   # Tage vom Regenereignis bis zum Schub
        # Nur 10 Fundorte im Vergleichsgebiet - weiter geschaetzt
        "boden_ph": [(5.5, 7.0, 1.0), (5.0, 5.5, 0.85), (None, 5.0, 0.6),
                     (7.0, None, 0.85)],
        "boden_ton": [(18, None, 1.0), (14, 18, 0.85), (None, 14, 0.65)],
        # warme Eichenbestaende, auch offen und licht
        "waldanteil_wirkung": 0.10,
        # geschaetzt - im Juni gibt es keinen Frost
        "frost_abzug": (15, 35),   # (leichter, starker Frost)
        "saison": {1: 0.0, 2: 0.01, 3: 0.02, 4: 0.0, 5: 0.05, 6: 1.00,
                   7: 0.89, 8: 0.32, 9: 0.06, 10: 0.01, 11: 0.01, 12: 0.0},
        # Kalkbuchenwald und Eiche - der Elm ist klassisches Revier
        # Waermeliebender Laubwaldpilz: Eiche und Buche, keine Nadelhoelzer
        "baumarten": {"eiche": 1.0, "buche": 1.0, "laub_lang": 0.7,
                      "birke": 0.3, "laub_kurz": 0.25, "erle": 0.2,
                      "kiefer": 0.15, "laerche": 0.15, "fichte": 0.1,
                      "douglasie": 0.1, "tanne": 0.1},
        "waldtyp": {"laub": 1.0, "misch": 0.8, "nadel": 0.3,
                    "bruch": 0.3, "unbekannt": 0.85},
    },

    "marone": {
        "name": "Maronenroehrling",
        "gbif": "Imleria badia",
        # 384 Funde, Sep-Nov. Deutlich weniger heikel als der Steinpilz -
        # alle Verhaeltnisse liegen naeher an 1.
        "bilanz_14": [(24, None, 18), (-1, 24, 14), (-14, -1, 9),
                      (-28, -14, 5)],
        "bt07": [(7.5, 13, 22), (13, 16, 17), (16, 18, 8), (5, 7.5, 6)],
        "bf07": [(0.27, None, 18), (0.22, 0.27, 15), (0.19, 0.22, 9),
                 (0.16, 0.19, 4)],
        "regen_reife": [(34, None, 14), (15, 34, 10), (8, 15, 7),
                        (4, 8, 3)],
        "regentage": [(6, None, 14), (3, 6, 10), (2, 3, 5)],
        "temp": [(8.5, 14, 14), (14, 16.5, 10), (16.5, 18, 4),
                 (6, 8.5, 5)],
        "verzug": (10, 16),   # Tage vom Regenereignis bis zum Schub
        # KORREKTUR: kein Sandpilz. An 45 Fundorten zeigt sich
        # dieselbe Richtung wie beim Steinpilz - Ton ueber 20 % = 1.96
        "boden_ph": [(4.9, 5.8, 1.0), (None, 4.9, 0.85), (5.8, 6.4, 0.7),
                     (6.4, None, 0.55)],
        "boden_ton": [(19, None, 1.0), (14, 19, 0.85), (12, 14, 0.7),
                      (None, 12, 0.6)],
        # braucht geschlossenen Nadelbestand
        # Gemessen (n=44): Laerche 1.86, Kiefer 1.27, Laubholz unter 1.
        # Bestaetigt den Nadelwaldpilz. Fichte 0.67 nehme ich nicht
        # ernst - sie macht nur 2 % der Meldeorte aus.
        "baumarten": {"fichte": 1.0, "kiefer": 0.95, "tanne": 0.9,
                      "laerche": 0.8, "douglasie": 0.6, "buche": 0.5,
                      "eiche": 0.35, "birke": 0.35, "laub_lang": 0.25,
                      "laub_kurz": 0.2, "erle": 0.3},
        "waldanteil_wirkung": 0.12,
        # KORREKTUR: nicht frosthart. Leicht 0.00 im Nov
        "frost_abzug": (20, 35),   # (leichter, starker Frost)
        "saison": {1: 0.01, 2: 0.01, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.06,
                   7: 0.21, 8: 0.33, 9: 1.00, 10: 0.99, 11: 0.75, 12: 0.08},
        # Nadelwaldpilz. In dieser Region faellt Fichte praktisch aus,
        # Kiefer traegt sie.
        "baumarten": {"fichte": 1.0, "kiefer": 0.95, "tanne": 0.9,
                      "douglasie": 0.7, "laerche": 0.6, "buche": 0.5,
                      "eiche": 0.35, "birke": 0.3, "laub_lang": 0.25,
                      "laub_kurz": 0.2, "erle": 0.15},
        "waldtyp": {"nadel": 1.0, "misch": 0.9, "laub": 0.45,
                    "bruch": 0.3, "unbekannt": 0.85},
    },

    "pfifferling": {
        "name": "Pfifferling",
        "gbif": "Cantharellus cibarius",
        # 111 Funde, Jul-Okt. Die 60-Tage-Bilanz ist bei keiner anderen
        # Art so eindeutig: unter -143 mm null Funde, ueber -24 mm 3.03.
        "bilanz_60": [(-25, None, 25), (-63, -25, 15), (-95, -63, 6),
                      (-143, -95, 2)],
        "bilanz_14": [(11, None, 16), (-7, 11, 11), (-23, -7, 5),
                      (-40, -23, 2)],
        "bf07": [(0.33, None, 18), (0.27, 0.33, 13), (0.23, 0.27, 8),
                 (0.18, 0.23, 3)],
        "bt07": [(16, 19, 16), (13, 16, 13), (19, 20.5, 8),
                 (10, 13, 6)],
        "regentage": [(8, None, 15), (6, 8, 10), (5, 6, 6), (3, 5, 3)],
        "temp": [(17, 19, 10), (13.5, 17, 8), (19, 20, 3)],
        "verzug": (14, 25),   # Tage vom Regenereignis bis zum Schub
        # Nur 10 Fundorte im Vergleichsgebiet - weiter geschaetzt
        "boden_ph": [(None, 5.5, 1.0), (5.5, 6.1, 0.85), (6.1, None, 0.6)],
        "boden_ton": [(13, 20, 1.0), (20, None, 0.9), (None, 13, 0.75)],
        # am staerksten an geschlossenen Wald gebunden
        "waldanteil_wirkung": 0.14,
        # geschaetzt, zu wenige Spaetfunde
        "frost_abzug": (18, 40),   # (leichter, starker Frost)
        "saison": {1: 0.02, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.37,
                   7: 1.00, 8: 0.53, 9: 0.57, 10: 0.20, 11: 0.07, 12: 0.11},
        # Saure, moosige Nadelwaelder, auch Buche auf saurem Grund
        "baumarten": {"fichte": 1.0, "kiefer": 0.9, "tanne": 0.85,
                      "buche": 0.6, "eiche": 0.55, "douglasie": 0.5,
                      "laerche": 0.45, "birke": 0.4, "laub_lang": 0.3,
                      "laub_kurz": 0.25, "erle": 0.2},
        "waldtyp": {"nadel": 1.0, "misch": 0.95, "laub": 0.7,
                    "bruch": 0.3, "unbekannt": 0.85},
    },

    "birkenpilz": {
        "name": "Birkenpilz",
        "gbif": "Leccinum scabrum",
        # 135 Funde, Sep-Okt. Schwache Signale - anspruchsloseste Art.
        "bf07": [(0.30, None, 20), (0.25, 0.30, 16), (0.21, 0.25, 10),
                 (0.17, 0.21, 5)],
        "bilanz_14": [(20, None, 18), (-7, 20, 14), (-20, -7, 9),
                      (-34, -20, 5)],
        "bt07": [(None, 15, 20), (15, 16.5, 14), (16.5, 18, 6)],
        "regen_reife": [(34, None, 14), (9, 34, 11), (4, 9, 6)],
        "regentage": [(6, None, 14), (4, 6, 10), (2, 4, 6)],
        "temp": [(11, 15.5, 14), (15.5, 17, 8), (8, 11, 9)],
        "verzug": (8, 14),   # Tage vom Regenereignis bis zum Schub
        # 30 Fundorte: Schwerpunkt bei maessigem Ton (12-15 % = 1.87),
        # und als einzige Art auf sandigem Grund haeufiger
        "boden_ph": [(4.9, 5.7, 1.0), (None, 4.9, 0.9), (5.7, 6.3, 0.75),
                     (6.3, None, 0.8)],
        "boden_ton": [(12, 16, 1.0), (16, 22, 0.8), (None, 12, 0.65),
                      (22, None, 0.8)],
        # nur die Birke zaehlt - auch in Heide, Park, Garten
        "waldanteil_wirkung": 0.05,
        # KORREKTUR: nicht frosthart, wie die anderen
        "frost_abzug": (18, 40),   # (leichter, starker Frost)
        "saison": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0,
                   7: 0.14, 8: 0.19, 9: 1.00, 10: 0.70, 11: 0.18, 12: 0.0},
        # zwingend an Birke gebunden - Bruchwald ist hier gut
        # Zwingend an Birke gebunden. Der Anteil zaehlt, nicht die
        # Hauptbaumart - Birke steht oft als Beimischung im Kiefernforst.
        "baumarten": {"birke": 1.0, "laub_kurz": 0.45, "erle": 0.3,
                      "kiefer": 0.25, "laub_lang": 0.2, "eiche": 0.15,
                      "buche": 0.1, "laerche": 0.1, "fichte": 0.1,
                      "tanne": 0.05, "douglasie": 0.05},
        "waldtyp": {"bruch": 1.0, "misch": 0.9, "laub": 0.8,
                    "nadel": 0.5, "unbekannt": 0.8},
    },

    "parasol": {
        "name": "Parasol",
        "gbif": "Macrolepiota procera",
        # 500 Funde, Aug-Nov. KORREKTUR: kein Trockenheitsvertraeger.
        # Verhaelt sich fast wie der Steinpilz.
        "bilanz_14": [(22, None, 20), (5, 22, 16), (-9, 5, 11),
                      (-28, -9, 4)],
        "bt07": [(9, 12.5, 22), (12.5, 16, 16), (16, 19, 10),
                 (7, 9, 7)],
        "bf07": [(0.33, None, 18), (0.24, 0.33, 14), (0.20, 0.24, 8),
                 (0.17, 0.20, 3)],
        "regen_reife": [(34, None, 15), (24, 34, 11), (15, 24, 6),
                        (7, 15, 3)],
        "regentage": [(8, None, 15), (6, 8, 11), (5, 6, 6), (3, 5, 3)],
        "temp": [(10, 16, 10), (16, 19, 6), (8, 10, 5)],
        "verzug": (5, 12),   # Tage vom Regenereignis bis zum Schub
        # 140 Fundorte: klarer Schwerpunkt bei mittlerem Ton
        # (15-20 % = 2.00), pH 5.1-5.5 = 1.91
        "boden_ph": [(5.0, 5.7, 1.0), (5.7, 6.2, 0.8), (None, 5.0, 0.7),
                     (6.2, None, 0.6)],
        "boden_ton": [(14, 21, 1.0), (21, None, 0.8), (11, 14, 0.75),
                      (None, 11, 0.55)],
        # Wiesen- und Weidenpilz, Wald fast nebensaechlich
        # Gemessen (n=73): kein starkes Signal ausser Erle 2.55 und
        # Birke 1.68 - passt zu einem Pilz, der Waldraender und
        # Lichtungen mag. Buche 0.41 leicht nach unten.
        "baumarten": {"eiche": 1.0, "birke": 1.0, "erle": 1.0,
                      "laub_lang": 1.0, "laub_kurz": 1.0, "kiefer": 0.9,
                      "laerche": 0.85, "buche": 0.7, "fichte": 0.85,
                      "douglasie": 0.7, "tanne": 0.7},
        "waldanteil_wirkung": 0.02,
        # gemessen: leicht 0.64, stark 0.00 (nur Nov)
        "frost_abzug": (20, 45),   # (leichter, starker Frost)
        "saison": {1: 0.0, 2: 0.01, 3: 0.0, 4: 0.0, 5: 0.07, 6: 0.31,
                   7: 0.42, 8: 0.51, 9: 1.00, 10: 0.68, 11: 0.39, 12: 0.0},
        # Waldraender und Lichtungen - Waldtyp fast egal
        # Zersetzer an Waldraendern und Lichtungen - Baumart fast egal
        "baumarten": {"eiche": 1.0, "birke": 1.0, "laub_lang": 1.0,
                      "laub_kurz": 1.0, "buche": 0.95, "laerche": 0.95,
                      "kiefer": 0.9, "erle": 0.85, "fichte": 0.8,
                      "douglasie": 0.8, "tanne": 0.8},
        "waldtyp": {"laub": 1.0, "misch": 1.0, "nadel": 0.9,
                    "bruch": 0.7, "unbekannt": 1.0},
    },

    "schwefelporling": {
        "name": "Schwefelporling",
        "gbif": "Laetiporus sulphureus",
        # 840 Funde, Mai-Sep. WICHTIG: Das Wetter sagt bei dieser Art
        # kaum etwas aus - alle Auswahlverhaeltnisse liegen zwischen 0.74
        # und 1.33. Als Holzbewohner zieht er sein Wasser aus dem Stamm.
        # Der Score ist deshalb fast reine Saison; die Wetterbaender sind
        # absichtlich flach gehalten, damit sie nichts vortaeuschen.
        "bilanz_60": [(-42, None, 30), (-100, -42, 24), (None, -100, 20)],
        "bf07": [(0.30, None, 25), (0.15, 0.30, 22), (None, 0.15, 20)],
        "bt07": [(None, 16, 25), (16, 18.5, 22), (18.5, None, 19)],
        "temp": [(None, 16, 20), (16, 18, 17), (18, None, 15)],
        # Holzbewohner - nicht regengesteuert, kein Schubfenster
        "verzug": None,
        # 180 Fundorte, das staerkste Bodensignal ueberhaupt:
        # Ton unter 12 % Verhaeltnis 0.04, ueber 20 % dagegen 2.89.
        # Passt zu Eiche auf lehmigem Grund.
        "boden_ph": [(5.1, 6.1, 1.0), (6.1, 6.6, 0.75), (4.8, 5.1, 0.6),
                     (None, 4.8, 0.5), (6.6, None, 0.65)],
        "boden_ton": [(20, None, 1.0), (16, 20, 0.8), (13, 16, 0.55),
                      (None, 13, 0.4)],
        # waechst am einzelnen Baum, nicht am Bestand
        # Gemessen (n=86): Erle 2.55, sonst. Laubholz kurz 1.79,
        # Eiche 1.16, Fichte 0.14. Erle und Weide sind bekannte Wirte -
        # deshalb deutlich hochgesetzt.
        "baumarten": {"eiche": 1.0, "laub_kurz": 0.9, "erle": 0.85,
                      "laub_lang": 0.8, "buche": 0.4, "birke": 0.3,
                      "laerche": 0.15, "kiefer": 0.12, "fichte": 0.06,
                      "douglasie": 0.08, "tanne": 0.08},
        "waldanteil_wirkung": 0.04,
        # gemessen: leicht 1.74 - Holzbewohner, unbeeindruckt
        "frost_abzug": (0, 8),   # (leichter, starker Frost)
        "saison": {1: 0.02, 2: 0.01, 3: 0.02, 4: 0.07, 5: 1.00, 6: 0.50,
                   7: 0.13, 8: 0.19, 9: 0.19, 10: 0.03, 11: 0.02, 12: 0.02},
        # Eiche, Weide, Kirsche, Robinie - reiner Laubholzbewohner
        # Eiche ist der Hauptwirt, dazu Weide, Kirsche, Robinie.
        # Auf Nadelholz kaum, und von dort auch nicht zu empfehlen.
        "baumarten": {"eiche": 1.0, "laub_kurz": 0.85, "laub_lang": 0.8,
                      "erle": 0.4, "buche": 0.35, "birke": 0.3,
                      "laerche": 0.15, "kiefer": 0.1, "fichte": 0.08,
                      "douglasie": 0.08, "tanne": 0.08},
        "waldtyp": {"laub": 1.0, "bruch": 0.9, "misch": 0.7,
                    "nadel": 0.15, "unbekannt": 0.7},
        "abzug_faktor": 0.2,
    },
}

# Alle Groessen, die als Punktband auftreten koennen. Je Art wird nur
# bewertet, was dort auch definiert ist.
MOEGLICHE_FELDER = ["bf07", "bt07", "temp", "regen_reife", "regentage",
                    "bilanz_14", "bilanz_60"]

MONATSMITTE = 15.0


def schubfenster(art, ereignistag):
    """
    Von wann bis wann nach einem Regenereignis mit Fruchtkoerpern zu
    rechnen ist. Aus der Fachliteratur, NICHT an Funden gemessen -
    im deutschen Herbst regnet es zu oft, um einzelne Ausloeser zu
    trennen. Deshalb geht diese Angabe auch nicht in den Score ein,
    sondern steht nur als Hinweis.
    """
    from datetime import timedelta
    verzug = ARTEN[art].get("verzug")
    if not verzug or ereignistag is None:
        return None
    von, bis = verzug
    return ereignistag + timedelta(days=von), ereignistag + timedelta(days=bis)


def bewerte_band(wert, baender):
    """Erste passende Zeile gewinnt. Fehlender Wert gibt Teilpunkte."""
    if wert is None:
        beste = max((b[2] for b in baender), default=0)
        return round(beste * 0.35)

    for von, bis, punkte in baender:
        if von is not None and wert < von:
            continue
        if bis is not None and wert > bis:
            continue
        return punkte
    return 0


def _faktor_band(wert, baender):
    """Wie bewerte_band, aber fuer Faktoren. Fehlender Wert = neutral."""
    if wert is None or not baender:
        return 1.0
    for von, bis, f in baender:
        if von is not None and wert < von:
            continue
        if bis is not None and wert > bis:
            continue
        return f
    return 1.0


def baumart_schluessel(bezeichnung):
    """Nimmt englischen Namen oder Klassenzahl und liefert den Schluessel."""
    text = str(bezeichnung).strip()
    if text in BAUMART_SCHLUESSEL:
        return BAUMART_SCHLUESSEL[text]

    # Bindestrich und Gedankenstrich vereinheitlichen
    vereinfacht = text.replace("\u2013", "-").replace("\u2014", "-")
    for name, schluessel in BAUMART_SCHLUESSEL.items():
        if name.replace("\u2013", "-").replace("\u2014", "-") == vereinfacht:
            return schluessel

    try:
        return BAUMART_CODE.get(int(float(text)))
    except (ValueError, TypeError):
        return None


def baumart_faktor(einstellung, bestand):
    """
    Gewichteter Faktor aus den Baumartenanteilen einer Zelle.
    bestand: dict mit "anteile" {schluessel: 0..1} und "waldanteil".

    Ein Beispiel: 60 % Eiche, 30 % Kiefer, 10 % Birke ergibt beim
    Schwefelporling 0.6*1.0 + 0.3*0.1 + 0.1*0.3 = 0.66.
    """
    if not bestand:
        return None

    gewichte = einstellung.get("baumarten")
    anteile = bestand.get("anteile") or {}
    if not gewichte or not anteile:
        return None

    summe = sum(anteile.values())
    if summe <= 0:
        return None

    f = sum(anteil / summe * gewichte.get(art, 0.5)
            for art, anteil in anteile.items())

    # Waldanteil: schwache Daempfung, siehe die Erklaerung oben bei
    # WALDANTEIL_WIRKUNG. Der Sammler sucht im Waldstueck, nicht auf
    # der ganzen Zelle.
    wirkung = einstellung.get("waldanteil_wirkung", WALDANTEIL_WIRKUNG)
    waldanteil = bestand.get("waldanteil")

    if waldanteil is not None:
        if wirkung > 0:
            deckung = min(1.0, waldanteil / 0.30)
            f *= (1.0 - wirkung) + wirkung * deckung

        # Sehr wenig Wald: hier geht es nicht um Pilzdichte, sondern
        # darum, dass Baumarten und Boden aus wenigen Bildpunkten
        # stammen und entsprechend unsicher sind.
        if waldanteil < WALDANTEIL_UNSICHER:
            f *= 0.75

    return max(0.0, min(1.0, f))


def boden_faktor(einstellung, boden):
    """
    Bodeneinfluss als Multiplikator.

    pH- und Tonbaender sind an 468 Fundorten gegen 977 Waldpunkte im
    selben Gebiet gemessen. Bei Pfifferling und Sommersteinpilz reichte
    die Zahl der Fundorte nicht - dort stehen weiter Schaetzwerte.

    Vorbehalt: Tonreiche Boeden liegen in dieser Region im Sueden, wo
    auch mehr Menschen melden. Ein Teil des Effekts koennte
    Beobachterdichte sein. Dagegen spricht, dass der Birkenpilz genau
    umgekehrt reagiert - bei reiner Sammlerdichte muessten alle Arten
    in dieselbe Richtung zeigen.
    """
    if not boden:
        return 1.0
    # Ton statt Sand: Ton haelt Wasser, ist das staerkere Mass und
    # zu Sand ohnehin gegenlaeufig - beides zu nehmen zaehlte doppelt.
    f = (_faktor_band(boden.get("ph"), einstellung.get("boden_ph"))
         * _faktor_band(boden.get("clay"), einstellung.get("boden_ton")))
    return max(BODEN_MINDEST, min(1.0, f))


def saison_rohwert(einstellung, tag):
    """
    Saisonwert 0-1. Mit SAISON_WEICH wird zwischen den Monatswerten
    interpoliert, sonst springt der Wert am Monatsersten.
    """
    saison = einstellung["saison"]

    if not SAISON_WEICH or not hasattr(tag, "day"):
        monat = tag if isinstance(tag, int) else tag.month
        return saison.get(monat, 0.0)

    monat, tagnr = tag.month, tag.day

    # Position zwischen den Monatsmitten bestimmen
    if tagnr >= MONATSMITTE:
        von, bis = monat, monat % 12 + 1
        anteil = (tagnr - MONATSMITTE) / 30.0
    else:
        von, bis = (monat - 2) % 12 + 1, monat
        anteil = (tagnr + 30.0 - MONATSMITTE) / 30.0

    a = saison.get(von, 0.0)
    b = saison.get(bis, 0.0)
    return a + (b - a) * min(1.0, max(0.0, anteil))


def score(kennwerte, art, tag, waldtyp="unbekannt", boden=None,
          bestand=None):
    """
    kennwerte: dict aus kennwerte.berechne()
    tag: date-Objekt (oder Monatszahl, dann ohne weiche Kurve)
    boden: dict mit "ph" und "sand", oder None
    bestand: dict mit "anteile" und "waldanteil" aus baumarten.csv

    Rueckgabe: (endscore, wetterpunkte, saison, wald, boden, einzelteile)
    """
    einstellung = ARTEN[art]

    einzeln = {}
    wetter = 0
    for feld in MOEGLICHE_FELDER:
        baender = einstellung.get(feld)
        if not baender:
            continue
        p = bewerte_band(kennwerte.get(feld), baender)
        einzeln[feld] = p
        wetter += p

    af = einstellung.get("abzug_faktor", 1.0)

    # Ausgetrockneter Boden ohne frischen Regen
    bf = kennwerte.get("bf07")
    frisch = kennwerte.get("regen_frisch") or 0
    if bf is not None and bf < 0.17 and frisch < 1.0:
        ab = round(15 * af)
        wetter -= ab
        einzeln["trockenheit"] = -ab

    # Ueber 14 Tage ohne Regen von mindestens 3 mm (gemessen: 0.14)
    if (kennwerte.get("tage_seit_regen") or 0) > 14:
        ab = round(12 * af)
        wetter -= ab
        einzeln["lange_trocken"] = -ab

    # Frost beendet die Saison abrupt. An Funden gemessen: schon ein
    # bis zwei Frosttage druecken das Auswahlverhaeltnis auf 0.0 bis 0.7,
    # bei drei Tagen oder gefrorenem Boden auf 0.0 bis 0.3.
    # Der Schwefelporling ist als Holzbewohner ausgenommen.
    frostabzug = einstellung.get("frost_abzug")
    if frostabzug:
        leicht, stark = frostabzug
        frosttage = kennwerte.get("frosttage") or 0
        min_boden = kennwerte.get("min_boden")
        if frosttage >= 3 or (min_boden is not None and min_boden < -1.0):
            ab = round(stark * af)
        elif frosttage >= 1:
            ab = round(leicht * af)
        else:
            ab = 0
        if ab:
            wetter -= ab
            einzeln["frost"] = -ab

    wetter = max(0, min(100, wetter))

    roh_saison = saison_rohwert(einstellung, tag)
    saison = 1.0 - SAISON_STAERKE * (1.0 - roh_saison)
    # Gemessene Baumartenanteile schlagen die grobe Kategorie
    wald = baumart_faktor(einstellung, bestand)
    if wald is None:
        wald = einstellung["waldtyp"].get(waldtyp, 1.0)
    wald = round(wald, 2)

    bodenfaktor = boden_faktor(einstellung, boden)

    end = round(wetter * saison * wald * bodenfaktor)
    return (max(0, min(100, end)), wetter, round(saison, 2), wald,
            round(bodenfaktor, 2), einzeln)
