"""
Umrechnungen fuer die Reliefbilder, fuer ganze numpy-Felder auf einmal.

Das Hoehenmodell liegt im UTM-Gitter (Zone 32). Die Karte legt Bilder
dagegen linear in die Mercator-Projektion zwischen vier Eckpunkte. Die
UTM-Gitterlinien stehen dort schraeg - in den Revieren um gut ein Grad.
Ein UTM-Bild einfach als Rechteck hingelegt, lag an den Ecken 300 bis
500 m daneben.

Dazu die Waldmaske: dieselbe Gesamtwald-Ebene, die die Karte zeigt
(web/wald.json und web/wald/wald_gesamt.png). So liegen Relief und
Wald auf der Karte deckungsgleich.
"""
import os
import json
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

A = 6378137.0
F = 1 / 298.257223563
K0 = 0.9996
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)
ZONE = 32
LAMBDA0 = np.radians((ZONE - 1) * 6 - 180 + 3)

WALD_INDEX = os.path.join("web", "wald.json")
WALD_BILD = os.path.join("web", "wald", "wald_gesamt.png")


def merc(lat):
    """Breitengrad -> Mercator-Hochwert (Einheitskugel)."""
    lat = np.asarray(lat, dtype=np.float64)
    return np.log(np.tan(np.radians(45.0 + lat / 2.0)))


def entmerc(y):
    """Mercator-Hochwert -> Breitengrad."""
    return 2.0 * np.degrees(np.arctan(np.exp(y))) - 90.0


def wgs84_zu_utm(lat, lon):
    """
    Breite/Laenge in Grad -> (Ost, Nord) in Metern, Zone 32.

    Reihenentwicklung nach Snyder. Bis drei Grad neben dem
    Mittelmeridian auf Millimeter genau - Niedersachsen liegt darin.
    """
    phi = np.radians(np.asarray(lat, dtype=np.float64))
    lam = np.radians(np.asarray(lon, dtype=np.float64))
    sin, cos, tan = np.sin(phi), np.cos(phi), np.tan(phi)
    n = A / np.sqrt(1 - E2 * sin ** 2)
    t = tan ** 2
    c = EP2 * cos ** 2
    a = cos * (lam - LAMBDA0)
    e4, e6 = E2 ** 2, E2 ** 3
    m = A * ((1 - E2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
             - (3 * E2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * np.sin(2 * phi)
             + (15 * e4 / 256 + 45 * e6 / 1024) * np.sin(4 * phi)
             - (35 * e6 / 3072) * np.sin(6 * phi))
    ost = 500000.0 + K0 * n * (
        a + (1 - t + c) * a ** 3 / 6
        + (5 - 18 * t + t ** 2 + 72 * c - 58 * EP2) * a ** 5 / 120)
    nord = K0 * (m + n * tan * (
        a ** 2 / 2 + (5 - t + 9 * c + 4 * c ** 2) * a ** 4 / 24
        + (61 - 58 * t + t ** 2 + 600 * c - 330 * EP2) * a ** 6 / 720))
    return ost, nord


def utm_zu_wgs84(ost, nord):
    """(Ost, Nord) in Metern, Zone 32 -> Breite/Laenge in Grad."""
    e1 = (1 - np.sqrt(1 - E2)) / (1 + np.sqrt(1 - E2))
    x = np.asarray(ost, dtype=np.float64) - 500000.0
    y = np.asarray(nord, dtype=np.float64)
    mu = (y / K0) / (A * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * np.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * np.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * np.sin(6 * mu))
    n1 = A / np.sqrt(1 - E2 * np.sin(phi1) ** 2)
    t1 = np.tan(phi1) ** 2
    c1 = EP2 * np.cos(phi1) ** 2
    r1 = A * (1 - E2) / (1 - E2 * np.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * K0)
    breite = phi1 - (n1 * np.tan(phi1) / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * EP2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * EP2
           - 3 * c1 ** 2) * d ** 6 / 720)
    laenge = (d - (1 + 2 * t1 + c1) * d ** 3 / 6
              + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * EP2
                 + 24 * t1 ** 2) * d ** 5 / 120) / np.cos(phi1)
    return np.degrees(breite), np.degrees(LAMBDA0 + laenge)


def umschliessendes_raster(rahmen, breite_px):
    """
    Kartenraster, das ein UTM-Rechteck ganz umschliesst.

    rahmen: (ost_min, nord_min, ost_max, nord_max) in Metern.
    Rueckgabe: sued, west, nord, ost in Grad und die Bildhoehe, bei der
    ein Bildpunkt in Nord-Sued- und Ost-West-Richtung gleich lang ist.
    Abgetastet wird der ganze Rand - in Grad sind die Kanten gebogen.
    """
    ost_min, nord_min, ost_max, nord_max = rahmen
    t = np.linspace(0.0, 1.0, 101)
    e = np.concatenate([ost_min + t * (ost_max - ost_min),
                        np.full_like(t, ost_max),
                        ost_max - t * (ost_max - ost_min),
                        np.full_like(t, ost_min)])
    n = np.concatenate([np.full_like(t, nord_min),
                        nord_min + t * (nord_max - nord_min),
                        np.full_like(t, nord_max),
                        nord_max - t * (nord_max - nord_min)])
    lat, lon = utm_zu_wgs84(e, n)
    sued, nord = float(lat.min()), float(lat.max())
    west, ost = float(lon.min()), float(lon.max())
    hoehe_px = int(round(breite_px * float(merc(nord) - merc(sued))
                         / np.radians(ost - west)))
    return sued, west, nord, ost, hoehe_px


def rasterzeilen(sued, nord, hoehe_px, y0, y1):
    """Breitengrade der Bildzeilen y0..y1-1, Mitte des Bildpunkts."""
    yn, ys = float(merc(nord)), float(merc(sued))
    anteil = (np.arange(y0, y1) + 0.5) / hoehe_px
    return entmerc(yn - anteil * (yn - ys))


def rasterspalten(west, ost, breite_px):
    """Laengengrade der Bildspalten, Mitte des Bildpunkts."""
    return west + (np.arange(breite_px) + 0.5) / breite_px * (ost - west)


class Waldmaske:
    """Gesamtwald der Karte als Nachschlagetabelle: Wald ja oder nein."""

    def __init__(self, alpha, sued, west, nord, ost):
        self.alpha = alpha
        self.west, self.ost = west, ost
        self.yn, self.ys = float(merc(nord)), float(merc(sued))

    @classmethod
    def laden(cls, index=WALD_INDEX, bild=WALD_BILD):
        """None, wenn die Waldebene fehlt."""
        if not (os.path.exists(index) and os.path.exists(bild)):
            return None
        with open(index, "r", encoding="utf-8") as f:
            g = json.load(f)["grenzen"]
        with Image.open(bild) as b:
            alpha = np.array(b.convert("RGBA").getchannel("A"))
        return cls(alpha, g[0][0], g[0][1], g[1][0], g[1][1])

    def wald(self, lat, lon):
        """
        True, wo die Waldebene deckt. Das Bild liegt auf der Karte
        linear in Mercator zwischen seinen Ecken - genauso wird hier
        nachgeschlagen.
        """
        hoehe, breite = self.alpha.shape
        spalte = np.floor((np.asarray(lon) - self.west)
                          / (self.ost - self.west) * breite).astype(np.int64)
        zeile = np.floor((self.yn - merc(lat))
                         / (self.yn - self.ys) * hoehe).astype(np.int64)
        innen = ((spalte >= 0) & (spalte < breite)
                 & (zeile >= 0) & (zeile < hoehe))
        ergebnis = np.zeros(spalte.shape, dtype=bool)
        ergebnis[innen] = self.alpha[zeile[innen], spalte[innen]] > 0
        return ergebnis

    def fuer_utm_gitter(self, form, rahmen, schritt, streifen=256):
        """Maske fuer ein UTM-Gitter, Zeile 0 im Norden. In Streifen,
        damit der Speicher auch bei 8000 x 8000 Punkten reicht."""
        hoehe, breite = form
        ost_min, _, _, nord_max = rahmen
        maske = np.zeros(form, dtype=bool)
        ost = ost_min + (np.arange(breite) + 0.5) * schritt
        for y0 in range(0, hoehe, streifen):
            y1 = min(hoehe, y0 + streifen)
            nord = nord_max - (np.arange(y0, y1) + 0.5) * schritt
            e, n = np.meshgrid(ost, nord)
            lat, lon = utm_zu_wgs84(e, n)
            maske[y0:y1] = self.wald(lat, lon)
        return maske
