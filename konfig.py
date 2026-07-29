"""
Gemeinsame Einstellungen fuer alle Skripte.

Bisher standen das Arbeitsgebiet in neun Dateien, die Artenliste in
vier und die Baumartenklassen in fuenf. Wer die Region wechseln will,
muesste alle finden. Hier stehen sie einmal.

Neue Region: Nur die vier Zahlen unten aendern, dann der Reihe nach
waldraster.py, hoehen.py, ortsnamen.py, schutzgebiete.py,
baumarten.py, bodendaten.py und hintergrund.py neu laufen lassen.
"""

# --- Arbeitsgebiet -----------------------------------------------------
# Braunschweig - Wolfsburg - Elm - suedliche Lueneburger Heide
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15

# Groesseres Gebiet fuer Fundmeldungen. Die Kalibrierung braucht mehr
# Funde, als die Kernregion hergibt.
FUNDE_SUED, FUNDE_WEST, FUNDE_NORD, FUNDE_OST = 51.5, 9.0, 53.5, 12.0

RASTER_KM = 2.0


# --- Pilzarten ---------------------------------------------------------
# Schluessel -> wissenschaftlicher Name fuer GBIF und iNaturalist
PILZARTEN = {
    "steinpilz": "Boletus edulis",
    "sommersteinpilz": "Boletus reticulatus",
    "marone": "Imleria badia",
    "pfifferling": "Cantharellus cibarius",
    "birkenpilz": "Leccinum scabrum",
    "schwefelporling": "Laetiporus sulphureus",
    "parasol": "Macrolepiota procera",
}


# --- Baumarten der Thuenen-Karte ---------------------------------------
BAUMART_WERTE = {
    2: "birke", 3: "buche", 4: "douglasie", 5: "eiche", 6: "erle",
    8: "fichte", 9: "kiefer", 10: "laerche", 14: "tanne",
    16: "laub_lang", 17: "laub_kurz",
}

BAUMART_NAMEN = {
    "birke": "Birke", "buche": "Buche", "douglasie": "Douglasie",
    "eiche": "Eiche", "erle": "Erle", "fichte": "Fichte",
    "kiefer": "Kiefer", "laerche": "Laerche", "tanne": "Tanne",
    "laub_lang": "sonst. Laubholz langlebig",
    "laub_kurz": "sonst. Laubholz kurzlebig",
}

# Englische Bezeichnungen, wie sie aus dem Thuenen-Dienst kommen
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


# --- Anlaufstellen -----------------------------------------------------
KENNUNG = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

OVERPASS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
