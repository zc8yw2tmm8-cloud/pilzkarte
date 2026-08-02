"""
Reviere fuer die Feinkarten aus dem 1-m-Hoehenmodell.

Je Gebiet ein Rechteck. dgm_holen.py laedt die Hoehenkacheln - aber
nur die, die tatsaechlich Wald beruehren -, relief.py rechnet daraus
die Feuchtekarte, karte.py und die Website binden sie ein.

Eine Kachel deckt 1 x 1 km ab und ist etwa 1,5 MB gross. Ein Gebiet
von 15 x 15 km sind also rund 250 Kacheln, davon nach Waldfilter
etwa die Haelfte.

Zum Ergaenzen: Zeile kopieren, Namen und Grenzen anpassen. Die
Koordinaten findest du, indem du in der Pilzkarte auf eine Zelle
klickst - sie stehen im Popup.
"""

GEBIETE = {
    "wolfsburg": {
        "name": "Wolfsburg",
        "beschreibung": "Stadtforst, Klieversberg, Barnbruch, Droemling",
        "sued": 52.36, "nord": 52.49,
        "west": 10.66, "ost": 10.88,
    },
    "braunschweig": {
        "name": "Braunschweig",
        "beschreibung": "Riddagshausen, Querumer Forst, Buchhorst",
        "sued": 52.20, "nord": 52.34,
        "west": 10.44, "ost": 10.66,
    },
    "koenigslutter": {
        "name": "Koenigslutter",
        "beschreibung": "Rieseberg, Dorm, Lutterspring",
        "sued": 52.20, "nord": 52.32,
        "west": 10.74, "ost": 10.94,
    },
    "elm": {
        "name": "Elm",
        "beschreibung": "Kalkbuchenwald, Reitlingstal",
        "sued": 52.11, "nord": 52.26,
        "west": 10.76, "ost": 10.98,
    },
    "ehra_lessien": {
        "name": "Ehra-Lessien",
        "beschreibung": "Suedheide, Kiefernforste, Bruchwaelder",
        "sued": 52.60, "nord": 52.74,
        "west": 10.55, "ost": 10.80,
    },
}


def aktive():
    return GEBIETE


def kacheln_zaehlen(gebiet):
    """Grobe Zahl der 1-km-Kacheln fuer ein Gebiet."""
    import math
    km_lat = 111.0
    km_lon = 111.0 * math.cos(
        math.radians((gebiet["sued"] + gebiet["nord"]) / 2))
    breite = (gebiet["ost"] - gebiet["west"]) * km_lon
    hoehe = (gebiet["nord"] - gebiet["sued"]) * km_lat
    return int(math.ceil(breite) + 1) * int(math.ceil(hoehe) + 1)
