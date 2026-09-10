"""Georeferenzierte Waldkacheln auf ein gemeinsames Web-Mercator-Raster legen."""
import math
from contextlib import ExitStack
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin, array_bounds
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from rasterio.warp import transform_bounds


LEER = 255


def pruefe_kachel(pfad):
    with rasterio.open(pfad) as src:
        if src.crs is None or src.transform.is_identity or src.count != 1:
            raise ValueError(f"{pfad}: fehlende/ungeeignete Georeferenzierung")
        if not all(math.isfinite(x) for x in (*src.transform, *src.bounds)):
            raise ValueError(f"{pfad}: ungueltige Transformation")
        if abs(src.transform.determinant) < 1e-18:
            raise ValueError(f"{pfad}: singulaere Transformation")
        for _, win in src.block_windows(1):
            daten = src.read(1, window=win)
            if np.any((daten < 0) | (daten > 17)):
                raise ValueError(f"{pfad}: unerwartete Klassenwerte")
        return {"crs": src.crs.to_string(), "transform": list(src.transform),
                "bounds": list(src.bounds), "width": src.width, "height": src.height}


def zielraster(grenzen, meter=20):
    sued, west, nord, ost = grenzen
    if not (-85 < sued < nord < 85 and -180 <= west < ost <= 180):
        raise ValueError("Ungueltiges Ausgabegebiet")
    links, unten, rechts, oben = transform_bounds("EPSG:4326", "EPSG:3857", west, sued, ost, nord)
    pixel = meter / math.cos(math.radians((sued + nord) / 2))
    links = math.floor(links / pixel) * pixel
    oben = math.ceil(oben / pixel) * pixel
    breite = math.ceil((rechts - links) / pixel)
    hoehe = math.ceil((oben - unten) / pixel)
    return from_origin(links, oben, pixel, pixel), breite, hoehe


def anteilsfenster(pfade, transform, breite, hoehe, block=256):
    """2x2 Unterpixel je Ausgabezelle; erste Quelldatei gewinnt inklusive Klasse 0."""
    fein = transform * rasterio.Affine.scale(0.5, 0.5)
    with ExitStack() as stack:
        vrts = []
        for pfad in sorted(map(str, pfade)):
            src = stack.enter_context(rasterio.open(pfad))
            vrt = stack.enter_context(WarpedVRT(src, crs="EPSG:3857", transform=fein,
                width=breite * 2, height=hoehe * 2, resampling=Resampling.nearest,
                src_nodata=LEER, nodata=LEER, dtype="uint8", warp_mem_limit=64))
            vrts.append(vrt)
        for y in range(0, hoehe, block):
            for x in range(0, breite, block):
                h, w = min(block, hoehe-y), min(block, breite-x)
                mosaik = np.full((h*2, w*2), LEER, dtype=np.uint8)
                fenster = Window(x*2, y*2, w*2, h*2)
                for vrt in vrts:
                    a = vrt.read(1, window=fenster)
                    frei = (mosaik == LEER) & (a != LEER)
                    mosaik[frei] = a[frei]
                if np.any(mosaik == LEER):
                    raise ValueError(f"Unabgedeckter Bereich im Zielraster bei {x}/{y}")
                yield Window(x, y, w, h), mosaik


def geografische_grenzen(transform, breite, hoehe):
    bounds = array_bounds(hoehe, breite, transform)
    west, sued, ost, nord = transform_bounds("EPSG:3857", "EPSG:4326", *bounds)
    return [[sued, west], [nord, ost]]
