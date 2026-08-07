# Abhängigkeiten im Code

Aus dem Code erzeugt mit `abhaengigkeiten.py`. Bei Änderungen neu erzeugen.

## Wer benutzt wen

| Skript | benutzt | wird benutzt von |
|---|---|---|
| `arten.py` | — | `daten_export`, `infoseite`, `karte`, `web_bilder` |
| `daten_export.py` | `arten`, `karte`, `kennwerte` | — |
| `dgm_holen.py` | `gebiete` | — |
| `farben.py` | — | `infoseite`, `karte`, `weichzeichnen` |
| `funde_wetter2.py` | `kennwerte` | — |
| `gebiete.py` | — | `dgm_holen`, `relief` |
| `historie.py` | — | `historie_aufteilen`, `karte`, `nachfuellen`, `raster_ausrichten`, `sammeln` |
| `historie_aufteilen.py` | `historie` | — |
| `infoseite.py` | `arten`, `farben` | `karte` |
| `kalibrieren.py` | `kennwerte` | — |
| `karte.py` | `arten`, `farben`, `historie`, `infoseite`, `kennwerte`, `waldebenen`, `weichzeichnen` | `daten_export` |
| `kennwerte.py` | — | `daten_export`, `funde_wetter2`, `kalibrieren`, `karte` |
| `nachfuellen.py` | `historie` | — |
| `raster_ausrichten.py` | `historie` | — |
| `relief.py` | `gebiete` | — |
| `sammeln.py` | `historie` | — |
| `waldebenen.py` | — | `karte` |
| `web_bilder.py` | `arten`, `weichzeichnen` | — |
| `weichzeichnen.py` | `farben` | `karte`, `web_bilder` |

## Namen, die über Dateigrenzen benutzt werden

Ändert sich einer davon, bricht der Aufrufer.

### `arten.py`

- `most_common` — benutzt von `pruefen`

### `farben.py`

- `hex_farbe` — benutzt von `karte`
- `rgb` — benutzt von `weichzeichnen`
- `thema` — benutzt von `infoseite`, `karte`, `weichzeichnen`

### `gebiete.py`

- `aktive` — benutzt von `dgm_holen`, `relief`
- `append` — benutzt von `karte`

### `hintergrund.py`

- `most_common` — benutzt von `baumarten_kalibrieren`
- `values` — benutzt von `baumarten_kalibrieren`

### `historie.py`

- `ALT` — benutzt von `historie_aufteilen`
- `SPALTEN` — benutzt von `nachfuellen`, `sammeln`
- `anhaengen` — benutzt von `nachfuellen`, `sammeln`
- `dateien` — benutzt von `historie_aufteilen`
- `lese` — benutzt von `karte`, `raster_ausrichten`
- `spanne` — benutzt von `historie_aufteilen`, `nachfuellen`
- `umziehen` — benutzt von `historie_aufteilen`
- `vorhandene` — benutzt von `nachfuellen`, `sammeln`

### `hoehen.py`

- `get` — benutzt von `daten_export`, `karte`
- `max` — benutzt von `relief`, `relief_weit`
- `min` — benutzt von `relief`, `relief_weit`

### `infoseite.py`

- `schreibe` — benutzt von `karte`

### `karte.py`

- `get_root` — benutzt von `karte`
- `save` — benutzt von `karte`

### `kennwerte.py`

- `KENNWERT_SPALTEN` — benutzt von `funde_wetter2`
- `berechne` — benutzt von `daten_export`, `funde_wetter2`, `kalibrieren`, `karte`
- `finde_ereignisse` — benutzt von `karte`
- `get` — benutzt von `arten`
- `zahl` — benutzt von `kalibrieren`, `karte`

### `legende.py`

- `get` — benutzt von `baumarten`

### `waldebenen.py`

- `erzeuge` — benutzt von `karte`

### `weichzeichnen.py`

- `BILDORDNER` — benutzt von `web_bilder`
- `erzeuge` — benutzt von `karte`, `web_bilder`

## Datendateien

| Datei | erwähnt in |
|---|---|
| `aufwand.csv` | `funde_arten`, `kalibrieren`, `pruefen` |
| `aufwand_orte.csv` | `aufwand_orte`, `baumarten_kalibrieren`, `boden_aufwand` |
| `baumarten.csv` | `baumarten`, `dgm_holen`, `karte`, `pruefen`, `relief`, `waldpunkte_filtern` |
| `baumarten_gewichte.txt` | `baumarten_kalibrieren` |
| `bodendaten.csv` | `bodenanalyse`, `bodendaten`, `karte`, `pruefen` |
| `bodendaten_aufwand.csv` | `boden_aufwand`, `bodenanalyse` |
| `bodendaten_funde.csv` | `bodenanalyse`, `bodendaten`, `pruefen` |
| `daten.json` | `daten_export`, `finde_loch`, `luecken_fuellen`, `pruefe_felder`, `web_bilder` |
| `funde_arten.csv` | `baumarten_kalibrieren`, `bodenanalyse`, `bodendaten`, `funde_arten`, `funde_inaturalist`, `funde_wetter2`, `… und 3 weitere` |
| `funde_arten_nur_gbif.csv` | `funde_zusammenfuegen` |
| `funde_inat.csv` | `funde_inaturalist`, `funde_zusammenfuegen` |
| `funde_wetter2.csv` | `funde_wetter2`, `kalibrieren`, `pruefen` |
| `hintergrund.csv` | `hintergrund`, `kalibrieren`, `pruefen` |
| `hoehen.csv` | `hoehen`, `karte`, `pruefen` |
| `kalibrierung.txt` | `kalibrieren`, `saison_uebernehmen` |
| `karten.json` | `web_bilder` |
| `klassen.csv` | `baumarten`, `legende` |
| `ortsnamen.csv` | `karte`, `ortsnamen`, `pruefen` |
| `relief.json` | `relief_web` |
| `relief_grenzen.csv` | `karte`, `relief`, `relief_web` |
| `relief_grenzen.txt` | `karte` |
| `relief_weit_feuchte.png` | `relief_weit` |
| `relief_weit_grenzen.txt` | `karte`, `relief_weit` |
| `relief_weit_schummerung.png` | `relief_weit` |
| `saison_weit.txt` | `saison_weit` |
| `schutzgebiete.geojson` | `karte` |
| `uebersicht.csv` | `dgm_holen` |
| `uebersicht.geojson` | `dgm_holen`, `relief_weit` |
| `uebersicht.json` | `dgm_holen` |
| `wald.json` | `web_wald` |
| `wald_gesamt.png` | `waldebenen` |
| `wald_grenzen.txt` | `pruefe_stand`, `waldebenen`, `web_wald` |
| `waldpunkte.csv` | `baumarten`, `bodendaten`, `dgm_holen`, `finde_loch`, `hintergrund`, `hoehen`, `… und 14 weitere` |
| `waldpunkte_vor_filter.csv` | `waldpunkte_filtern` |
| `waldpunkte_vor_kennungen.csv` | `reparatur_kennungen` |
| `waldpunkte_vor_luecken.csv` | `luecken_fuellen` |
| `waldpunkte_vorher.csv` | `raster_ausrichten` |
| `waldraster_stand.csv` | `waldraster_ergaenzen` |
| `waldtypen.csv` | `karte` |
| `wetter_historie.csv` | `historie`, `pruefen` |
| `wetter_prognose.csv` | `karte`, `prognose`, `pruefen` |

## Konstanten, die an mehreren Stellen stehen

Bei Änderungen überall nachziehen.

| Name | Wert | steht in |
|---|---|---|
| `ARBEITER` | **verschieden!** | `bodendaten`, `dgm_holen`, `funde_wetter2`, `nachfuellen`, `prognose`, `sammeln` |
| `ARTEN` | **verschieden!** | `arten`, `funde_arten`, `funde_inaturalist`, `saison_weit` |
| `AUFWAND` | **verschieden!** | `bodenanalyse`, `kalibrieren` |
| `AUFWAND_DATEI` | **verschieden!** | `baumarten_kalibrieren`, `funde_arten` |
| `AUFWAND_GRUPPE` | 'Agaricomycetes' | `funde_arten`, `saison_weit` |
| `AUSGABE` | **verschieden!** | `abhaengigkeiten`, `baumarten_kalibrieren`, `saison_weit` |
| `BASIS` | **verschieden!** | `aufwand_orte`, `baumarten`, `funde_arten`, `funde_inaturalist`, `legende`, `saison_weit` … 1 weitere |
| `BAUMART_NAMEN` | {'birke': 'Birke', 'buche': 'Buche', 'do | `arten`, `konfig` |
| `BAUMART_SCHLUESSEL` | {'Birch (Betula spp)': 'birke', 'Beech ( | `arten`, `konfig` |
| `BAUMART_WERTE` | {2: 'birke', 3: 'buche', 4: 'douglasie', | `arten`, `konfig` |
| `BERICHT` | 'kalibrierung.txt' | `kalibrieren`, `saison_uebernehmen` |
| `BILDORDNER` | 'bilder' | `relief`, `relief_weit`, `waldebenen` |
| `BLOCK` | **verschieden!** | `hoehen`, `waldraster_ergaenzen` |
| `BUENDEL` | **verschieden!** | `nachfuellen`, `prognose`, `sammeln` |
| `D` | **verschieden!** | `test_baumarten`, `test_dgm2` |
| `DATEI` | **verschieden!** | `aufwand_orte`, `baumarten`, `boden_aufwand`, `bodendaten`, `daten_export`, `funde_arten` … 12 weitere |
| `DUNKEL` | True | `karte`, `web_bilder` |
| `EBENE` | 'geonode:Dominant_Species_Class' | `baumarten`, `legende`, `test_baumarten` |
| `EIGENSCHAFTEN` | **verschieden!** | `bodendaten`, `test_boden_ph` |
| `FELDER` | **verschieden!** | `boden_aufwand`, `bodenanalyse`, `funde_wetter2`, `hintergrund`, `nachfuellen`, `prognose` … 2 weitere |
| `FUNDE` | **verschieden!** | `bodenanalyse`, `kalibrieren` |
| `FUNDE_DATEI` | 'funde_arten.csv' | `baumarten_kalibrieren`, `bodendaten`, `funde_wetter2`, `karte` |
| `GRENZEN_DATEI` | **verschieden!** | `relief`, `relief_weit` |
| `HEADERS` | {'User-Agent': 'PilzkarteWolfsburg/1.0 ( | `aufwand_orte`, `baumarten`, `boden_aufwand`, `bodendaten`, `dgm_holen`, `funde_arten` … 12 weitere |
| `KACHELORDNER` | 'kacheln' | `baumarten`, `baumarten_kalibrieren`, `waldebenen` |
| `KLASSEN` | **verschieden!** | `baumarten`, `baumarten_kalibrieren`, `waldebenen` |
| `KOPIE` | **verschieden!** | `funde_zusammenfuegen`, `luecken_fuellen`, `raster_ausrichten`, `reparatur_kennungen`, `saison_uebernehmen`, `waldpunkte_filtern` |
| `LEERWERT` | -9999.0 | `relief`, `relief_weit` |
| `MAX_BREITE` | **verschieden!** | `relief_web`, `web_wald` |
| `MAX_UNSICHERHEIT` | **verschieden!** | `aufwand_orte`, `baumarten_kalibrieren`, `funde_inaturalist`, `funde_wetter2` |
| `MONATE` | **verschieden!** | `kalibrieren`, `saison_uebernehmen` |
| `MONATSNAMEN` | ['Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun | `infoseite`, `saison_weit` |
| `NAEHE_KM` | **verschieden!** | `dgm_holen`, `relief_weit` |
| `ORDNER` | **verschieden!** | `daten_export`, `dgm_holen`, `historie`, `reparatur_dubletten`, `reparatur_konflikt`, `weichzeichnen` |
| `OVERPASS` | ['https://overpass.kumi.systems/api/inte | `konfig`, `waldraster_ergaenzen` |
| `PAUSE` | **verschieden!** | `bodendaten`, `nachfuellen`, `prognose`, `sammeln` |
| `PUNKTE` | **verschieden!** | `finde_loch`, `test_baumarten`, `test_boden_ph`, `waldpunkte_filtern` |
| `PUNKTE_DATEI` | 'waldpunkte.csv' | `baumarten`, `bodendaten`, `hintergrund`, `hoehen`, `karte`, `nachfuellen` … 4 weitere |
| `QUELLE` | **verschieden!** | `boden_aufwand`, `relief_web`, `web_wald` |
| `RASTER_KM` | 2.0 | `baumarten`, `karte`, `konfig`, `luecken_fuellen`, `pruefe_raster`, `raster_ausrichten` … 1 weitere |
| `RECHTECK` | **verschieden!** | `test_kachel`, `test_stac` |
| `SPALTEN` | **verschieden!** | `bodendaten`, `funde_arten`, `funde_inaturalist`, `funde_zusammenfuegen`, `hintergrund`, `historie` … 1 weitere |
| `SPARSAM` | **verschieden!** | `relief`, `waldebenen` |
| `STAC` | 'https://dgm.stac.lgln.niedersachsen.de' | `dgm_holen`, `test_kachel`, `test_stac` |
| `STAND` | **verschieden!** | `relief_weit`, `waldraster_ergaenzen` |
| `STUFEN` | ['research', 'needs_id'] | `funde_inaturalist`, `funde_zusammenfuegen` |
| `TEILER` | **verschieden!** | `boden_aufwand`, `bodendaten`, `test_boden_ph` |
| `TIEFEN` | ['0-5cm', '5-15cm', '15-30cm'] | `bodendaten`, `test_boden_ph` |
| `UMGEBUNG_M` | **verschieden!** | `relief`, `relief_weit` |
| `URL` | 'https://rest.isric.org/soilgrids/v2.0/p | `bodendaten`, `test_boden_ph` |
| `ZIEL` | **verschieden!** | `saison_uebernehmen`, `web_wald` |

## Reihenfolge beim Neurechnen

```
# Daten beschaffen
python nachfuellen.py      # Wetter, setzt fort
python baumarten.py        # Thünen-Kacheln
python bodendaten.py       # SoilGrids
python hoehen.py           # Open-Meteo
python ortsnamen.py        # Overpass

# Rechnen und ausgeben
python karte.py            # örtliche HTML-Karten
python daten_export.py     # web/daten.json
python web_bilder.py       # die weichen Bilder
```

`daten_export.py` importiert `karte.py` und benutzt dessen Ladefunktionen — beide müssen zusammenpassen.