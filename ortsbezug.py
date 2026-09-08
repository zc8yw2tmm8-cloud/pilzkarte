"""
Gehoert ein Wert wirklich zu dem Punkt, unter dessen Kennung er steht?

Warum das ein eigenes Modul ist: Boden, Hoehen, Baumarten und Wetter
werden ueberall allein ueber die Kennung verknuepft. Stimmt die
Kennung, wird der Wert genommen - auch wenn er in Wahrheit 100 km
entfernt gemessen wurde. Bei 1.632 Punkten faellt so etwas noch von
Hand auf; bei Zehntausenden nicht mehr. Deshalb steht die Regel
einmal hier statt viermal verteilt im Code.

Die zehn Meter sind eine Rundungsgrenze fuer dieses Raster, keine
fachliche Aussage darueber, wie weit ein Messwert tragen darf.

pruefe_orte.py berichtet, was im Bestand nicht passt. Dieses Modul
verhindert, dass es weiter benutzt oder neu erzeugt wird.
"""
import os
import csv
import math

PUNKTE_DATEI = "waldpunkte.csv"
TOLERANZ_M = 10


def abstand(lat1, lon1, lat2, lon2):
    """Meter zwischen zwei Koordinaten, genau genug fuer kurze Wege."""
    mlat = (lat1 + lat2) / 2
    dx = (lon1 - lon2) * 111320 * math.cos(math.radians(mlat))
    dy = (lat1 - lat2) * 111320
    return math.hypot(dx, dy)


def am_ort(zeile, lat, lon, toleranz=TOLERANZ_M):
    """Passt die Koordinate der Zeile zu (lat, lon)?

    Keine Zeile heisst nein - da ist nichts, was passen koennte.
    Eine Zeile ohne Koordinatenspalten heisst ja: Sie laesst sich
    nicht widerlegen, und stillschweigend wegzuwerfen waere schlimmer
    als sie zu behalten.
    """
    if not zeile:
        return False
    if not zeile.get("lat") or not zeile.get("lon"):
        return True
    try:
        d = abstand(float(zeile["lat"]), float(zeile["lon"]),
                    float(lat), float(lon))
    except (TypeError, ValueError):
        return False
    return d <= toleranz


def lade_punkte(pfad=PUNKTE_DATEI):
    """Kennung -> (lat, lon) aus dem Raster. None, wenn es fehlt."""
    if not os.path.exists(pfad):
        return None
    with open(pfad, "r", encoding="utf-8") as f:
        return {z["id"]: (float(z["lat"]), float(z["lon"]))
                for z in csv.DictReader(f)}
