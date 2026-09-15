"""
Holt die Naturschutzgebiete fuer die Karte.

Gezeigt werden nur Gebiete, in denen das Sammeln in der Regel
verboten ist: Naturschutzgebiete und die Kernzonen des
Biosphaerenreservats Droemling. Landschaftsschutz und Naturparks
fehlen mit Absicht - dort ist Sammeln meist erlaubt. Ob im einzelnen
Gebiet wirklich ein Sammelverbot gilt, steht in dessen Verordnung;
die Karte verlinkt sie, prueft sie aber nicht.

Quellen:
  Niedersachsen   amtlich vom NLWKN (Umweltkarten Niedersachsen),
                  mit Link zur Verordnung je Gebiet
  Sachsen-Anhalt  OpenStreetMap - der Ostteil des Gebiets
                  (Droemling, Lappwald, Ohreaue)

Frueher kam alles aus OpenStreetMap, und jedes Teilstueck einer
Grenze wurde einzeln geschlossen. Grosse Gebiete zerfielen so in
Dutzende gerade abgeschnittene Scheiben, ausgesparte Flaechen
wurden mit eingefaerbt. Hier werden die Teilstuecke erst zu Ringen
verkettet und Loecher als Loecher behandelt.

Die Datei wird eingecheckt und nicht im taeglichen Bau erzeugt -
Schutzgebiete aendern sich selten, und der Bau soll nicht an zwei
weiteren Diensten haengen. Nach Bedarf von Hand neu holen.

Ergebnis: web/schutzgebiete.json
"""
import json
import math
import os
from datetime import date

import requests

# Gleiche Bounding Box wie waldraster.py
SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15

DATEI = os.path.join("web", "schutzgebiete.json")

NI_DIENST = ("https://www.umweltkarten-niedersachsen.de/arcgis/rest/"
             "services/Natur_wms/MapServer/4/query")
# Gesicherter Abruf vom 11. September 2026, falls der Dienst ausfaellt
NI_ERSATZ = os.path.join("lokale_notizen", "schutzgebiete_neu",
                         "niedersachsen_nsg_rohdaten.geojson")

HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}

SERVER = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Die Flaechenabfrage liefert alles, was Sachsen-Anhalt beruehrt -
# also auch niedersaechsische Gebiete an der Landesgrenze. Die werden
# weiter unten gegen die amtlichen Flaechen aussortiert.
QUERY = f"""
[out:json][timeout:180];
area["ISO3166-2"="DE-ST"]->.st;
(
  way["leisure"="nature_reserve"]({SUED},{WEST},{NORD},{OST})(area.st);
  relation["leisure"="nature_reserve"]({SUED},{WEST},{NORD},{OST})(area.st);
  way["boundary"="protected_area"]({SUED},{WEST},{NORD},{OST})(area.st);
  relation["boundary"="protected_area"]({SUED},{WEST},{NORD},{OST})(area.st);
);
out geom;
"""

# Douglas-Peucker: Punkte, die weniger als so viele Meter von der
# vereinfachten Linie abweichen, fallen weg
TOLERANZ_M = 2.0
# 5 Nachkommastellen sind gut 1 m - genauer sind die Grenzen nicht
STELLEN = 5

# Meter je Grad in der Gebietsmitte
M_JE_GRAD_BREITE = 111320.0
M_JE_GRAD_LAENGE = 111320.0 * math.cos(math.radians((SUED + NORD) / 2))


# ---- Geometrie ------------------------------------------------------

def ringe_bauen(wege):
    """Verkettet Teilstuecke zu geschlossenen Ringen.

    wege: Liste von Punktlisten [(lon, lat), ...]. Stuecke duerfen in
    beliebiger Richtung und Reihenfolge kommen. Liefert (ringe, reste):
    geschlossene Ringe und die Zahl der Stuecke, die sich nicht
    schliessen liessen. Die werden verworfen, nicht mit einer geraden
    Linie zugemacht - genau das hat frueher die Scheiben erzeugt.
    """
    offen = [[tuple(p) for p in w] for w in wege if len(w) >= 2]
    ringe, reste = [], 0

    while offen:
        ring = offen.pop(0)
        while ring[0] != ring[-1]:
            for i, w in enumerate(offen):
                if w[0] == ring[-1]:
                    ring = ring + w[1:]
                elif w[-1] == ring[-1]:
                    ring = ring + w[-2::-1]
                elif w[-1] == ring[0]:
                    ring = w[:-1] + ring
                elif w[0] == ring[0]:
                    ring = w[:0:-1] + ring
                else:
                    continue
                offen.pop(i)
                break
            else:
                break

        if ring[0] == ring[-1] and len(ring) >= 4:
            ringe.append(ring)
        else:
            reste += 1

    return ringe, reste


def flaeche(ring):
    """Vorzeichenbehaftete Flaeche in Grad^2, positiv = gegen den
    Uhrzeigersinn."""
    return sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
               for i in range(len(ring) - 1)) / 2


def im_ring(punkt, ring):
    """Strahlentest: liegt der Punkt im Ring?"""
    x, y = punkt
    drin = False
    for i in range(len(ring) - 1):
        (x1, y1), (x2, y2) = ring[i], ring[i + 1]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                drin = not drin
    return drin


def liegt_in(innen, aussen):
    """Liegt Ring innen in Ring aussen? Drei Stuetzpunkte stimmen ab -
    ein einzelner koennte genau auf einer gemeinsamen Grenze liegen."""
    n = len(innen) - 1
    proben = [innen[0], innen[n // 3], innen[2 * n // 3]]
    return sum(im_ring(p, aussen) for p in proben) >= 2


def polygone_ordnen(ringe):
    """Macht aus losen Ringen Polygone mit Loechern.

    Ein Ring ist ein Loch, wenn er in einer ungeraden Zahl anderer
    Ringe liegt. Die Rollen aus OSM ("outer"/"inner") und die
    Umlaufrichtung aus ArcGIS werden bewusst nicht verwendet - beide
    sind nicht verlaesslich. Jedes Loch kommt zum kleinsten
    umgebenden Aussenring.

    Aussenringe laufen gegen den Uhrzeigersinn, Loecher mit ihm (wie
    GeoJSON es verlangt). MapLibre erkennt Loecher an der Richtung -
    stimmt sie nicht, wird das Loch als eigene Flaeche eingefaerbt.
    """
    groesse = [abs(flaeche(r)) for r in ringe]
    tiefe = [sum(1 for j, b in enumerate(ringe)
                 if j != i and groesse[j] > groesse[i] and liegt_in(a, b))
             for i, a in enumerate(ringe)]

    aussen = [i for i in range(len(ringe)) if tiefe[i] % 2 == 0]
    polygone = {i: [richtung(ringe[i], True)] for i in aussen}

    for i in range(len(ringe)):
        if tiefe[i] % 2 == 0:
            continue
        umgebend = [j for j in aussen
                    if groesse[j] > groesse[i] and liegt_in(ringe[i], ringe[j])]
        if umgebend:
            j = min(umgebend, key=lambda k: groesse[k])
            polygone[j].append(richtung(ringe[i], False))

    return [polygone[i] for i in aussen]


def richtung(ring, gegen_uhrzeiger):
    if (flaeche(ring) > 0) != gegen_uhrzeiger:
        return ring[::-1]
    return ring


def _abstand_m(p, a, b):
    """Abstand von p zur Strecke a-b in Metern."""
    px, py = p[0] * M_JE_GRAD_LAENGE, p[1] * M_JE_GRAD_BREITE
    ax, ay = a[0] * M_JE_GRAD_LAENGE, a[1] * M_JE_GRAD_BREITE
    bx, by = b[0] * M_JE_GRAD_LAENGE, b[1] * M_JE_GRAD_BREITE
    dx, dy = bx - ax, by - ay
    laenge2 = dx * dx + dy * dy
    if laenge2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / laenge2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def vereinfachen(ring, toleranz_m=TOLERANZ_M):
    """Douglas-Peucker fuer einen geschlossenen Ring, ohne Rekursion.

    Der Ring wird am ersten und am weitesten entfernten Punkt geteilt,
    damit beide Haelften eine echte Strecke als Grundlinie haben.
    Liefert None, wenn weniger als ein Dreieck uebrig bliebe.
    """
    punkte = [(round(x, STELLEN), round(y, STELLEN)) for x, y in ring]
    punkte = [p for i, p in enumerate(punkte) if i == 0 or p != punkte[i - 1]]
    if len(punkte) < 4 or punkte[0] != punkte[-1]:
        return None

    n = len(punkte)
    weit = max(range(n - 1), key=lambda i: _abstand_m(punkte[i], punkte[0],
                                                      punkte[0]))
    behalten = [False] * n
    behalten[0] = behalten[weit] = behalten[n - 1] = True

    stapel = [(0, weit), (weit, n - 1)]
    while stapel:
        anfang, ende = stapel.pop()
        bester, index = 0.0, None
        for i in range(anfang + 1, ende):
            d = _abstand_m(punkte[i], punkte[anfang], punkte[ende])
            if d > bester:
                bester, index = d, i
        if index is not None and bester > toleranz_m:
            behalten[index] = True
            stapel += [(anfang, index), (index, ende)]

    ergebnis = [p for p, b in zip(punkte, behalten) if b]
    return ergebnis if len(ergebnis) >= 4 else None


def geometrie_aufbereiten(ringe):
    """Lose Ringe -> vereinfachtes MultiPolygon oder None."""
    ringe = [r for r in ringe if len(r) >= 4 and r[0] == r[-1]]
    polygone = []
    for poly in polygone_ordnen(ringe):
        aussen = vereinfachen(poly[0])
        if aussen is None:
            continue
        loecher = [l for l in (vereinfachen(r) for r in poly[1:]) if l]
        polygone.append([aussen] + loecher)
    if not polygone:
        return None
    return {"type": "MultiPolygon",
            "coordinates": [[[list(p) for p in r] for r in poly]
                            for poly in polygone]}


def alle_ringe(geometrie):
    """Alle Ringe eines GeoJSON-Polygons oder -MultiPolygons, lose."""
    if geometrie["type"] == "Polygon":
        teile = [geometrie["coordinates"]]
    elif geometrie["type"] == "MultiPolygon":
        teile = geometrie["coordinates"]
    else:
        return []
    return [[tuple(p[:2]) for p in r] for poly in teile for r in poly]


def im_multipolygon(punkt, polygone):
    """polygone: Liste [aussen, loch, ...] - wie polygone_ordnen."""
    for poly in polygone:
        if im_ring(punkt, poly[0]) and not any(im_ring(punkt, l)
                                               for l in poly[1:]):
            return True
    return False


def innenpunkt(polygone):
    """Ein Punkt, der sicher in der groessten Flaeche liegt - der
    Schwerpunkt, oder falls der ausserhalb liegt (Sichelform) die
    Mitte zwischen zwei Randpunkten, die im Innern liegt."""
    poly = max(polygone, key=lambda p: abs(flaeche(p[0])))
    ring = poly[0]
    kandidaten = [(sum(p[0] for p in ring[:-1]) / (len(ring) - 1),
                   sum(p[1] for p in ring[:-1]) / (len(ring) - 1))]
    n = len(ring) - 1
    for k in range(1, 8):
        a, b = ring[0], ring[k * n // 8]
        kandidaten.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    for p in kandidaten:
        if im_multipolygon(p, [poly]):
            return p
    return ring[0]


# ---- Quellen --------------------------------------------------------

def hole_niedersachsen():
    """Amtliche NSG-Grenzen als GeoJSON-Features."""
    parameter = {
        "geometry": f"{WEST},{SUED},{OST},{NORD}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "kennz_ffn,name,nsg_url",
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "geojson",
    }
    try:
        antwort = requests.get(NI_DIENST, params=parameter,
                               headers=HEADERS, timeout=120)
        antwort.raise_for_status()
        features = antwort.json()["features"]
        print(f"Niedersachsen: {len(features)} Gebiete vom NLWKN")
        return features, "NLWKN, abgerufen " + date.today().isoformat()
    except Exception as e:
        print("Niedersachsen: Dienst nicht erreichbar:", e)

    if not os.path.exists(NI_ERSATZ):
        return [], None
    with open(NI_ERSATZ, "r", encoding="utf-8") as f:
        features = json.load(f)["features"]
    print(f"Niedersachsen: {len(features)} Gebiete aus {NI_ERSATZ}")
    return features, "NLWKN, Abruf vom 2026-09-11"


def hole_osm():
    for url in SERVER:
        print(f"Sachsen-Anhalt: versuche {url.split('/')[2]} ...")
        try:
            antwort = requests.post(url, data={"data": QUERY},
                                    headers=HEADERS, timeout=300)
        except Exception as e:
            print("  Verbindungsfehler:", e)
            continue
        if antwort.status_code != 200:
            print(f"  HTTP {antwort.status_code}: {antwort.text[:150]}")
            continue
        try:
            return antwort.json()
        except Exception:
            print("  Kein JSON:", antwort.text[:200])
    return None


def sammelverbot_osm(tags):
    """Naturschutzgebiet oder Kernzone? Naturparks (Klasse 5) und
    Landschaftsschutz fallen heraus."""
    titel = tags.get("protection_title", "").lower()
    klasse = tags.get("protect_class", "")
    if "naturschutzgebiet" in titel or "kernzone" in titel:
        return True
    return klasse in ("1", "1a", "1b", "2", "4")


def nur_https(url):
    url = (url or "").strip()
    return url if url.startswith("https://") else ""


def niedersachsen_features(rohdaten):
    features, polygone = [], []
    for f in rohdaten:
        p = f.get("properties") or {}
        geometrie = geometrie_aufbereiten(alle_ringe(f["geometry"]))
        if geometrie is None:
            continue
        polygone.append(polygone_ordnen(alle_ringe(f["geometry"])))
        features.append({
            "type": "Feature",
            "properties": {
                "name": p.get("name") or "ohne Namen",
                "art": "Naturschutzgebiet",
                "land": "NI",
                "kennung": p.get("kennz_ffn") or "",
                "url": nur_https(p.get("nsg_url")),
            },
            "geometry": geometrie,
        })
    return features, polygone


def osm_features(daten, ni_polygone):
    features, reste_gesamt, doppelt = [], 0, []
    for element in daten.get("elements", []):
        tags = element.get("tags", {})
        if not sammelverbot_osm(tags):
            continue

        if element["type"] == "way":
            wege = [[(p["lon"], p["lat"]) for p in element.get("geometry", [])]]
        else:
            wege = [[(p["lon"], p["lat"]) for p in m["geometry"]]
                    for m in element.get("members", [])
                    if m.get("type") == "way" and "geometry" in m
                    and m.get("role") in ("outer", "inner", "")]
        ringe, reste = ringe_bauen(wege)
        reste_gesamt += reste
        if not ringe:
            continue

        # Liegt die Flaeche in einem amtlichen niedersaechsischen
        # Gebiet, ist sie dort schon enthalten
        punkt = innenpunkt(polygone_ordnen(ringe))
        if any(im_multipolygon(punkt, p) for p in ni_polygone):
            doppelt.append(tags.get("name", "ohne Namen"))
            continue

        geometrie = geometrie_aufbereiten(ringe)
        if geometrie is None:
            continue
        titel = tags.get("protection_title") or "Naturschutzgebiet"
        features.append({
            "type": "Feature",
            "properties": {
                "name": tags.get("name") or titel,
                "art": titel,
                "land": "ST",
                "kennung": "",
                "url": nur_https(tags.get("website") or tags.get("url")),
            },
            "geometry": geometrie,
        })
    return features, reste_gesamt, doppelt


def main():
    ni_roh, ni_stand = hole_niedersachsen()
    ni, ni_polygone = niedersachsen_features(ni_roh)

    osm = hole_osm()
    if osm is None:
        print("OpenStreetMap-Abfrage fehlgeschlagen - nichts geschrieben.")
        return
    st, reste, doppelt = osm_features(osm, ni_polygone)

    if not ni:
        print("Keine niedersaechsischen Gebiete - nichts geschrieben.")
        return

    ergebnis = {
        "type": "FeatureCollection",
        "stand": date.today().isoformat(),
        "quellen": [ni_stand,
                    "OpenStreetMap-Mitwirkende (ODbL), abgerufen "
                    + date.today().isoformat()],
        "features": ni + st,
    }
    os.makedirs(os.path.dirname(DATEI), exist_ok=True)
    with open(DATEI, "w", encoding="utf-8") as f:
        json.dump(ergebnis, f, ensure_ascii=False, separators=(",", ":"))

    punkte = sum(len(r) for x in ergebnis["features"]
                 for poly in x["geometry"]["coordinates"] for r in poly)
    loecher = sum(len(poly) - 1 for x in ergebnis["features"]
                  for poly in x["geometry"]["coordinates"])
    print(f"\nNiedersachsen: {len(ni)} Gebiete")
    print(f"Sachsen-Anhalt: {len(st)} Gebiete")
    if doppelt:
        print(f"  schon amtlich enthalten, uebersprungen: {', '.join(doppelt)}")
    if reste:
        print(f"  {reste} OSM-Teilstuecke liessen sich nicht schliessen "
              "und wurden verworfen")
    print(f"{punkte} Punkte, {loecher} Loecher")
    print(f"{DATEI}: {os.path.getsize(DATEI) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
