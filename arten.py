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

# Was gilt, wenn Baumarten oder Boden einer Zelle unbekannt sind?
#
# Naheliegend waere 1.0 - "kein Abzug ohne Grund". Das ist aber
# falsch herum: Eine Zelle, ueber die nichts bekannt ist, bekaeme
# dann einen hoeheren Wert als jede vermessene, und stuende in der
# Bestenliste ganz oben. Nicht weil sie gut ist, sondern weil nichts
# gegen sie spricht.
#
# Richtig ist der typische Wert der Region. Eine unbekannte Zelle
# wird damit als durchschnittlich behandelt, nicht als perfekt.
# Die Werte sind die Mediane ueber alle vermessenen Zellen.
UNBEKANNT_BESTAND = 0.78
UNBEKANNT_BODEN = 0.85


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
        # Gemessen gegen 2.378 Pilzmeldeorte (n=69): pH-Verhaeltnis
        # 0.68 bis 1.33, Ton 0.76 bis 1.28. Fast kein Signal.
        # Der frueher gemessene starke Zusammenhang kam aus dem
        # Vergleich gegen Waldpunkte und war Beobachterverzerrung.
        "boden_ph": [(5.1, 5.8, 1.0), (5.8, None, 0.9),
                     (None, 5.1, 0.85)],
        "boden_ton": [(15, 22, 1.0), (22, None, 0.9),
                      (None, 15, 0.95)],
        "saison": {1: 0.0, 2: 0.01, 3: 0.0, 4: 0.0, 5: 0.02, 6: 0.02,
                   7: 0.21, 8: 0.37, 9: 1.00, 10: 0.70, 11: 0.44, 12: 0.04},
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
        # warme Eichenbestaende, auch offen und licht
        "waldanteil_wirkung": 0.10,
        # geschaetzt - im Juni gibt es keinen Frost
        "frost_abzug": (15, 35),   # (leichter, starker Frost)
        # Zu wenige Fundorte mit Bodenwerten im
        # Vergleichsgebiet - deshalb neutral. Lieber kein
        # Faktor als ein erfundener.
        "boden_ph": [(None, None, 1.0)],
        "boden_ton": [(None, None, 1.0)],
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
        # Gemessen gegen Meldeorte (n=45): pH flach (1.05-1.15),
        # Sand leicht bevorzugt, Ton 16-21 % mit 1.51 am besten.
        "boden_ph": [(None, 5.7, 1.0), (5.7, None, 0.85)],
        "boden_ton": [(15, 21, 1.0), (21, 26, 0.85),
                      (None, 15, 0.9), (26, None, 0.8)],
        "saison": {1: 0.01, 2: 0.01, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.06,
                   7: 0.21, 8: 0.33, 9: 1.00, 10: 0.99, 11: 0.75, 12: 0.08},
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
        # am staerksten an geschlossenen Wald gebunden
        "waldanteil_wirkung": 0.14,
        # geschaetzt, zu wenige Spaetfunde
        "frost_abzug": (18, 40),   # (leichter, starker Frost)
        # Zu wenige Fundorte mit Bodenwerten im
        # Vergleichsgebiet - deshalb neutral. Lieber kein
        # Faktor als ein erfundener.
        "boden_ph": [(None, None, 1.0)],
        "boden_ton": [(None, None, 1.0)],
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
        # nur die Birke zaehlt - auch in Heide, Park, Garten
        "waldanteil_wirkung": 0.05,
        # KORREKTUR: nicht frosthart, wie die anderen
        "frost_abzug": (18, 40),   # (leichter, starker Frost)
        # Zu wenige Fundorte mit Bodenwerten im
        # Vergleichsgebiet - deshalb neutral. Lieber kein
        # Faktor als ein erfundener.
        "boden_ph": [(None, None, 1.0)],
        "boden_ton": [(None, None, 1.0)],
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
        # KORREKTUR: Gemessen gegen Meldeorte (n=88) genau
        # umgekehrt zur frueheren Annahme - hoeherer pH ist besser
        # (ab 5.7 Verhaeltnis 1.49), viel Sand besser (1.60),
        # wenig Ton besser (unter 21 % um 1.5).
        "boden_ph": [(5.5, None, 1.0), (5.2, 5.5, 0.85),
                     (None, 5.2, 0.75)],
        "boden_ton": [(None, 21, 1.0), (21, 26, 0.8),
                      (26, None, 0.7)],
        "saison": {1: 0.0, 2: 0.01, 3: 0.0, 4: 0.0, 5: 0.07, 6: 0.31,
                   7: 0.42, 8: 0.51, 9: 1.00, 10: 0.68, 11: 0.39, 12: 0.0},
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
        # KORREKTUR: Gemessen gegen Meldeorte (n=165). pH hoeher
        # ist besser (ab 5.7 Verhaeltnis 1.78, unter 5.1 nur 0.21) -
        # umgekehrt zur frueheren Annahme. Beim Ton bleibt die
        # Richtung, aber schwaecher: 21-26 % mit 1.56.
        "boden_ph": [(5.4, None, 1.0), (5.1, 5.4, 0.85),
                     (None, 5.1, 0.6)],
        "boden_ton": [(21, None, 1.0), (16, 21, 0.85),
                      (None, 16, 0.7)],
        "saison": {1: 0.02, 2: 0.01, 3: 0.02, 4: 0.07, 5: 1.00, 6: 0.50,
                   7: 0.13, 8: 0.19, 9: 0.19, 10: 0.03, 11: 0.02, 12: 0.02},
        "waldtyp": {"laub": 1.0, "bruch": 0.9, "misch": 0.7,
                    "nadel": 0.15, "unbekannt": 0.7},
        "abzug_faktor": 0.2,
    },

    # ------------------------------------------------------------
    # Die folgenden vier Arten sind NICHT kalibriert.
    #
    # Ihre Werte stammen aus der Pilzliteratur und aus dem Vergleich
    # mit den gemessenen Arten - nicht aus Fundmeldungen. Bei den
    # ersten sieben Arten hat sich sechsmal gezeigt, dass plausible
    # Annahmen falsch waren. Nimm diese Zahlen entsprechend
    # vorsichtig.
    #
    # Zum Kalibrieren: funde_arten.py und kalibrieren.py neu laufen
    # lassen, sobald genug Funde vorliegen.
    # ------------------------------------------------------------

    "hexenroehrling": {
        "name": "Flockenstieliger Hexenr\u00f6hrling",
        "gbif": "Neoboletus erythropus",
        # GESCHAETZT. Frueher und waermetoleranter als der Steinpilz,
        # sonst aehnliche Ansprueche.
        "bilanz_14": [(12, None, 22), (-2, 12, 17), (-15, -2, 10),
                      (-32, -15, 4)],
        "bt07": [(10, 16, 22), (16, 19, 16), (8, 10, 11), (19, 22, 6)],
        "bf07": [(0.30, None, 18), (0.22, 0.30, 15), (0.18, 0.22, 8),
                 (0.15, 0.18, 3)],
        "regen_reife": [(30, None, 15), (20, 30, 12), (12, 20, 7),
                        (6, 12, 3)],
        "regentage": [(7, None, 15), (5, 7, 11), (4, 5, 7), (2, 4, 4)],
        "temp": [(11, 19, 8), (19, 22, 4), (8, 11, 4)],
        "verzug": (8, 14),
        # Breite Mykorrhiza: Fichte, Buche, Eiche
        "baumarten": {"fichte": 1.0, "buche": 1.0, "eiche": 0.9,
                      "tanne": 0.85, "kiefer": 0.7, "douglasie": 0.5,
                      "laerche": 0.5, "laub_lang": 0.5, "birke": 0.35,
                      "laub_kurz": 0.3, "erle": 0.2},
        "waldanteil_wirkung": 0.12,
        "frost_abzug": (18, 40),
        # Zu wenige Fundorte mit Bodenwerten im
        # Vergleichsgebiet - deshalb neutral. Lieber kein
        # Faktor als ein erfundener.
        "boden_ph": [(None, None, 1.0)],
        "boden_ton": [(None, None, 1.0)],
        "saison": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.03, 6: 0.20,
                   7: 0.45, 8: 0.75, 9: 1.00, 10: 0.60, 11: 0.15,
                   12: 0.01},
        "waldtyp": {"laub": 1.0, "misch": 1.0, "nadel": 0.9,
                    "bruch": 0.4, "unbekannt": 0.9},
    },

    "netzhexe": {
        "name": "Netzstieliger Hexenr\u00f6hrling",
        "gbif": "Suillellus luridus",
        # GESCHAETZT. Der Kalkzeiger unter den Roehrlingen - im Elm
        # deutlich haeufiger als in der Heide.
        "bilanz_14": [(12, None, 22), (-2, 12, 17), (-15, -2, 10),
                      (-32, -15, 4)],
        "bt07": [(11, 17, 22), (17, 20, 15), (9, 11, 10), (20, 23, 5)],
        "bf07": [(0.30, None, 17), (0.22, 0.30, 14), (0.18, 0.22, 8),
                 (0.15, 0.18, 3)],
        "regen_reife": [(30, None, 15), (20, 30, 12), (12, 20, 7),
                        (6, 12, 3)],
        "regentage": [(7, None, 14), (5, 7, 11), (4, 5, 7), (2, 4, 4)],
        "temp": [(12, 20, 9), (20, 23, 5), (9, 12, 4)],
        "verzug": (8, 14),
        # Buche und Eiche auf Kalk, kaum Nadelholz
        "baumarten": {"buche": 1.0, "eiche": 0.95, "laub_lang": 0.7,
                      "birke": 0.4, "laub_kurz": 0.35, "fichte": 0.3,
                      "tanne": 0.3, "kiefer": 0.25, "laerche": 0.25,
                      "douglasie": 0.2, "erle": 0.2},
        "waldanteil_wirkung": 0.12,
        "frost_abzug": (18, 40),
        # Zu wenige Fundorte mit Bodenwerten im
        # Vergleichsgebiet - deshalb neutral. Lieber kein
        # Faktor als ein erfundener.
        "boden_ph": [(None, None, 1.0)],
        "boden_ton": [(None, None, 1.0)],
        "saison": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.05, 6: 0.30,
                   7: 0.55, 8: 0.80, 9: 1.00, 10: 0.55, 11: 0.12,
                   12: 0.0},
        "waldtyp": {"laub": 1.0, "misch": 0.9, "nadel": 0.35,
                    "bruch": 0.3, "unbekannt": 0.85},
    },

    "reizker": {
        "name": "Edelreizker",
        "gbif": "Lactarius deliciosus",
        # GESCHAETZT. An Kiefer gebunden - in dieser Region mit 45 %
        # Kiefernanteil eine der aussichtsreicheren Arten.
        # Spaete Art, vertraegt Kaelte besser als die Roehrlinge.
        "bilanz_14": [(10, None, 20), (-5, 10, 16), (-20, -5, 10),
                      (-35, -20, 4)],
        "bt07": [(7, 12, 22), (12, 15, 16), (4, 7, 12), (15, 18, 6)],
        "bf07": [(0.30, None, 18), (0.23, 0.30, 15), (0.19, 0.23, 9),
                 (0.16, 0.19, 4)],
        "regen_reife": [(30, None, 15), (20, 30, 12), (12, 20, 7),
                        (6, 12, 3)],
        "regentage": [(7, None, 14), (5, 7, 11), (4, 5, 7), (2, 4, 4)],
        "temp": [(7, 15, 9), (15, 18, 5), (4, 7, 5)],
        "verzug": (10, 16),
        # Fast ausschliesslich Kiefer
        "baumarten": {"kiefer": 1.0, "laerche": 0.35, "fichte": 0.25,
                      "douglasie": 0.2, "tanne": 0.2, "birke": 0.15,
                      "eiche": 0.1, "buche": 0.1, "laub_lang": 0.1,
                      "laub_kurz": 0.1, "erle": 0.1},
        "waldanteil_wirkung": 0.15,
        # Spaetherbstart, haelt Frost besser aus
        "frost_abzug": (10, 30),
        # Zu wenige Fundorte mit Bodenwerten im
        # Vergleichsgebiet - deshalb neutral. Lieber kein
        # Faktor als ein erfundener.
        "boden_ph": [(None, None, 1.0)],
        "boden_ton": [(None, None, 1.0)],
        "saison": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.02,
                   7: 0.10, 8: 0.40, 9: 0.90, 10: 1.00, 11: 0.45,
                   12: 0.05},
        "waldtyp": {"nadel": 1.0, "misch": 0.7, "laub": 0.15,
                    "bruch": 0.2, "unbekannt": 0.8},
    },

    "krauseglucke": {
        "name": "Krause Glucke",
        "gbif": "Sparassis crispa",
        # GESCHAETZT. Waechst an Wurzeln und Stuempfen alter Kiefern,
        # also nicht im Boden. Deshalb wirkt das Wetter schwaecher
        # als bei Mykorrhizapilzen - aehnlich wie beim
        # Schwefelporling.
        #
        # Besonderheit fuer Sammler: Sie kommt jahrelang an derselben
        # Wurzel wieder. Die Fundebene ist bei ihr wertvoller als
        # jede Wetterrechnung.
        "bilanz_14": [(5, None, 14), (-15, 5, 11), (-35, -15, 7)],
        "bt07": [(12, 19, 16), (9, 12, 12), (19, 22, 9), (6, 9, 6)],
        "bf07": [(0.26, None, 14), (0.20, 0.26, 11), (0.16, 0.20, 7)],
        "regen_reife": [(25, None, 12), (15, 25, 9), (8, 15, 5)],
        "regentage": [(6, None, 10), (4, 6, 7), (2, 4, 4)],
        "temp": [(13, 21, 8), (10, 13, 5), (21, 24, 4)],
        # Waechst langsam ueber Wochen, kein scharfer Schub
        "verzug": (14, 28),
        # An Kiefer gebunden, selten Laerche oder Douglasie
        "baumarten": {"kiefer": 1.0, "laerche": 0.4, "douglasie": 0.35,
                      "fichte": 0.2, "tanne": 0.2, "eiche": 0.1,
                      "buche": 0.1, "birke": 0.08, "laub_lang": 0.08,
                      "laub_kurz": 0.08, "erle": 0.05},
        # Waechst am einzelnen Baum, nicht am Bestand
        "waldanteil_wirkung": 0.06,
        # Wie der Schwefelporling geschuetzter als Bodenpilze
        "frost_abzug": (8, 25),
        # Zu wenige Fundorte mit Bodenwerten im
        # Vergleichsgebiet - deshalb neutral. Lieber kein
        # Faktor als ein erfundener.
        "boden_ph": [(None, None, 1.0)],
        "boden_ton": [(None, None, 1.0)],
        "saison": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.03,
                   7: 0.20, 8: 0.70, 9: 1.00, 10: 0.65, 11: 0.15,
                   12: 0.01},
        "waldtyp": {"nadel": 1.0, "misch": 0.7, "laub": 0.15,
                    "bruch": 0.2, "unbekannt": 0.8},
        # Wetter sagt bei Holzbewohnern weniger aus
        "abzug_faktor": 0.5,
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
        # Unbekannt heisst durchschnittlich, nicht perfekt
        return UNBEKANNT_BESTAND

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
        return UNBEKANNT_BODEN
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


# ------------------------------------------------------------
# Monatsnormale der Wetterpunkte
#
# Problem: Die Wetterpunkte sind im Herbst systematisch hoeher, weil
# der Boden dann feuchter und kuehler ist. Der Saisonfaktor sagt das
# aber schon - er wurde aus Fundmeldungen je Aufwand und Monat
# gerechnet und enthaelt den Wettereffekt des Monats bereits.
#
# Multipliziert man beides, zaehlt der Herbst zweimal. Gemessen an
# 31.535 Vergleichstagen verschiebt das bei vier Arten den
# Hoehepunkt um einen Monat nach hinten: Steinpilz, Marone,
# Birkenpilz und Parasol landeten im Oktober statt im September.
#
# Diese Tabelle sagt, wie hoch die Wetterpunkte in einem Monat
# NORMALERWEISE liegen - bezogen auf das Jahresmittel. Die
# Wetterpunkte werden daran geteilt. Damit drueckt das Wetter nur
# noch aus, ob dieser Tag besser oder schlechter ist als ein
# gewoehnlicher Tag desselben Monats.
#
# Erzeugt aus dem Hintergrund mit monatsnormale.py.
MONATSNORMALE = {
    "birkenpilz": {1: 0.936, 2: 0.974, 3: 1.051, 4: 1.071, 5: 1.056, 6: 0.779, 7: 0.679, 8: 0.653, 9: 0.986, 10: 1.521, 11: 1.272, 12: 1.022},
    "hexenroehrling": {1: 0.705, 2: 0.765, 3: 0.797, 4: 0.923, 5: 1.113, 6: 1.026, 7: 1.002, 8: 0.929, 9: 1.209, 10: 1.625, 11: 1.111, 12: 0.794},
    "krauseglucke": {1: 0.84, 2: 0.866, 3: 0.82, 4: 0.865, 5: 1.023, 6: 1.076, 7: 1.084, 8: 1.007, 9: 1.211, 10: 1.359, 11: 1.007, 12: 0.842},
    "marone": {1: 0.707, 2: 0.797, 3: 0.939, 4: 1.156, 5: 1.196, 6: 0.851, 7: 0.757, 8: 0.733, 9: 1.082, 10: 1.72, 11: 1.266, 12: 0.796},
    "netzhexe": {1: 0.683, 2: 0.746, 3: 0.764, 4: 0.845, 5: 1.089, 6: 1.108, 7: 1.091, 8: 1.003, 9: 1.271, 10: 1.558, 11: 1.059, 12: 0.783},
    "parasol": {1: 0.644, 2: 0.78, 3: 0.838, 4: 1.006, 5: 1.168, 6: 0.934, 7: 0.86, 8: 0.805, 9: 1.132, 10: 1.844, 11: 1.215, 12: 0.773},
    "pfifferling": {1: 0.893, 2: 0.962, 3: 1.058, 4: 0.948, 5: 0.862, 6: 0.888, 7: 0.864, 8: 0.813, 9: 1.042, 10: 1.387, 11: 1.257, 12: 1.027},
    "reizker": {1: 0.858, 2: 0.983, 3: 1.081, 4: 1.129, 5: 1.006, 6: 0.755, 7: 0.704, 8: 0.681, 9: 0.926, 10: 1.556, 11: 1.347, 12: 0.973},
    "schwefelporling": {1: 1.064, 2: 1.064, 3: 1.066, 4: 1.044, 5: 0.989, 6: 0.9, 7: 0.871, 8: 0.872, 9: 0.939, 10: 1.051, 11: 1.072, 12: 1.066},
    "sommersteinpilz": {1: 1.044, 2: 1.098, 3: 1.111, 4: 0.997, 5: 0.913, 6: 0.781, 7: 0.729, 8: 0.685, 9: 0.963, 10: 1.347, 11: 1.239, 12: 1.094},
    "steinpilz": {1: 0.759, 2: 0.859, 3: 0.879, 4: 1.004, 5: 1.106, 6: 0.871, 7: 0.793, 8: 0.761, 9: 1.057, 10: 1.799, 11: 1.256, 12: 0.856},
}

# Abschalten, falls sich der Umbau als falsch erweist
MONATSAUSGLEICH = True

# Wie stark das Wetter ueberhaupt ausschlagen darf.
#
# Die Baender wurden gegen ZUFAELLIGE Tage kalibriert. Gegen
# Meldetage nachgerechnet - also mit herausgerechnetem
# Sammlerverhalten - bleiben von 660 gemessenen Werten nur 233
# statistisch belastbar, und deren Median liegt bei 0.72.
#
# Beispiel Sommersteinpilz, viel Regen: Das Verhaeltnis fiel von
# 3.05 auf 1.22. Zwei Drittel des scheinbaren Wettereffekts waren
# die Frage, wann Menschen sammeln gehen.
#
# Die Baender bleiben deshalb in ihrer Struktur - die Richtung
# stimmt vermutlich, denn eine Verzerrung verstaerkt einen echten
# Effekt, sie erfindet ihn selten. Aber ihre Spannweite wird
# gestaucht: Der Abstand zwischen bestem und schlechtestem Wetter
# schrumpft auf diesen Anteil.
#
# 1.0 = wie kalibriert (uebertrieben)
# 0.0 = Wetter spielt keine Rolle
WETTER_SPANNE = 0.62

# Auf welchen Wert hin gestaucht wird: den Mittelwert der
# erreichbaren Punkte. So bleibt ein durchschnittlicher Tag etwa
# gleich bewertet, nur die Ausschlaege werden kleiner.


def bremse(wetter, saison, bestand, boden):
    """
    Welcher Faktor drueckt den Score am staerksten?

    Eine 3 kann heissen: falsche Jahreszeit, falscher Wald, oder
    schlicht zu trocken. Das steht sonst nirgends, und ohne diese
    Angabe ist eine niedrige Zahl nicht zu deuten.

    Rueckgabe: (Kurzwort, Erklaerung, Wert) oder None, wenn nichts
    besonders bremst.
    """
    teile = [
        # Wetter auf dieselbe Skala wie die Faktoren bringen
        (wetter / 100.0, "Wetter", "zu trocken oder falsche Temperatur"),
        (saison, "Jahreszeit", "nicht die Zeit dieser Art"),
        (bestand, "Bestand", "die passenden Baeume fehlen"),
        (boden, "Boden", "Saeuregrad oder Tongehalt passen nicht"),
    ]
    schwaechster = min(teile, key=lambda x: x[0])
    if schwaechster[0] >= 0.7:
        return None
    return schwaechster[1], schwaechster[2], round(schwaechster[0], 2)


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

    # Monatsausgleich: Die Wetterpunkte durch den Monatsnormalwert
    # teilen, damit sie nur die Abweichung vom gewoehnlichen Tag
    # dieses Monats ausdruecken. Sonst zaehlt der Herbst zweimal -
    # einmal ueber das Wetter, einmal ueber die Saison.
    if MONATSAUSGLEICH:
        normal = MONATSNORMALE.get(art, {}).get(tag.month)
        if normal and normal > 0.2:
            # Nach dem Teilen wieder auf eine ganze Zahl - sonst
            # steht in der Anzeige 63.829787234042556
            wetter = wetter / normal

    # Spannweite stauchen, siehe WETTER_SPANNE oben. Um 50 herum,
    # weil das etwa einem durchschnittlichen Tag entspricht.
    if WETTER_SPANNE < 1.0:
        wetter = 50 + (wetter - 50) * WETTER_SPANNE

    wetter = max(0, min(100, round(wetter)))

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
