"""
Bilder so aufbauen, wie die Karte sie hinlegt.

Die Bildebenen entstehen zeilenweise in gleichen Breitengradschritten:
Zeile 10 liegt genauso weit unter Zeile 9 wie Zeile 9 unter Zeile 8.
MapLibre legt sie aber linear in die Mercator-Projektion zwischen die
vier Eckpunkte - und dort werden die Breitengrade nach Norden hin
auseinandergezogen.

An den Raendern trifft es sich, dazwischen nicht. Fuer das Gebiet von
52,05 bis 52,85 Grad sind es in der Mitte 202 Meter. Das sind fuenf
Bildpunkte der Waldebene und beim Hineinzoomen deutlich zu sehen:
Die gruene Flaeche liegt neben dem, was sie meint.

zieh_nach_mercator() verschiebt die Zeilen so, dass jede dort landet,
wo sie hingehoert. Naechster Nachbar, damit Klassenwerte nicht
vermischt werden - aus Kiefer und Buche darf keine Mischzahl werden.
"""
import math


def merc(lat):
    """Breitengrad -> Mercator-Hochwert (Einheitskugel)."""
    return math.log(math.tan(math.radians(45.0 + lat / 2.0)))


def entmerc(y):
    """Mercator-Hochwert -> Breitengrad."""
    return 2.0 * math.degrees(math.atan(math.exp(y))) - 90.0


def quellzeilen(sued, nord, hoehe):
    """Fuer jede Zielzeile die passende Quellzeile. Zeile 0 = Norden."""
    if hoehe < 3 or nord <= sued:
        return list(range(max(hoehe, 0)))
    yn, ys = merc(nord), merc(sued)
    zeilen = []
    for j in range(hoehe):
        anteil = j / (hoehe - 1)
        lat = entmerc(yn + anteil * (ys - yn))
        q = (nord - lat) / (nord - sued) * (hoehe - 1)
        zeilen.append(min(hoehe - 1, max(0, int(round(q)))))
    return zeilen


def zieh_nach_mercator(bild, sued, nord):
    """bild: numpy-Feld, Zeile 0 im Norden. Gibt das gezogene Bild."""
    hoehe = bild.shape[0]
    if hoehe < 3 or nord <= sued:
        return bild
    return bild[quellzeilen(sued, nord, hoehe)]


def groesster_versatz_m(sued, nord):
    """Wie weit lag das Bild vorher daneben? Nur zum Berichten."""
    yn, ys = merc(nord), merc(sued)
    groesst = 0.0
    for i in range(101):
        anteil = i / 100.0
        lat_bild = nord - anteil * (nord - sued)
        lat_karte = entmerc(yn + anteil * (ys - yn))
        groesst = max(groesst, abs(lat_karte - lat_bild) * 111000.0)
    return groesst
