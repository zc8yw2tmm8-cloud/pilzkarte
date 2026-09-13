# Reihenfolge zum Ausführen

Alle Befehle im Ordner `C:\Users\Julia\pilzkarte`.

## Läuft von selbst (GitHub Actions)

| Workflow | Wann | Was |
|---|---|---|
| `taeglich.yml` | 4 × täglich, kurz nach den ICON-D2-Läufen | `sammeln.py` (Vortag), `prognose.py` (6 Tage voraus), sonntags früh zusätzlich `nachfuellen.py` |
| `seite.yml` | nach jedem erfolgreichen Sammellauf | `daten_export.py`, `web_bilder.py`, dann Veröffentlichung |

Die Messwerte landen in Monatsdateien unter `wetter_historie/`, die
Vorhersage in `wetter_prognose.csv`. `prognose.py` ersetzt die Datei
nur, wenn mindestens 98 % der Orte vollständig geliefert wurden.

Lokal läuft täglich nichts. `taeglich.py` ist nur noch ein Rückfall —
nicht parallel zur Cloud laufen lassen, sonst gibt es Konflikte beim
`git pull`.

## Grundlagen neu erzeugen

Nur nötig, wenn sich Gebiet oder Raster ändern:

| # | Befehl | Erzeugt |
|---|---|---|
| 1 | `python waldraster.py` | `waldpunkte.csv` |
| 2 | `python hoehen.py` | `hoehen.csv` |
| 3 | `python ortsnamen.py` | `ortsnamen.csv` |
| 4 | `python schutzgebiete.py` | `schutzgebiete.geojson` |
| 5 | `python baumarten.py` | `baumarten.csv` (Thünen-Kacheln) |
| 6 | `python bodendaten.py` | `bodendaten.csv` (SoilGrids) |
| 7 | `python hintergrund.py` | `hintergrund.csv` (Vergleichstage) |
| 8 | `python nachfuellen.py` | Wetterhistorie, setzt fort |

Danach `python pruefe_orte.py` — prüft, ob alle Daten am richtigen
Ort hängen.

## Kalibrierung

| # | Befehl | Erzeugt |
|---|---|---|
| 1 | `python funde_arten.py` | `funde_arten.csv`, `aufwand.csv` |
| 2 | `python aufwand_orte.py`, `python aufwand_tage.py` | Meldeorte und -tage als Maßstab |
| 3 | `python funde_wetter2.py` | `funde_wetter2.csv` |
| 4 | `python kalibrieren.py` | `kalibrierung.txt` |
| 5 | `python saison_uebernehmen.py` | Saisonfaktoren in `arten.py` |
| 6 | `python baumarten_kalibrieren.py` | `baumarten_gewichte.txt` |
| 7 | `python gewichte_uebernehmen.py` | Baumartengewichte in `arten.py` |

Beide Kalibrierungen schreiben ins `kalibrierung_protokoll.md`, damit
nachvollziehbar bleibt, aus welchen Daten die Zahlen stammen.
iNaturalist-Funde kommen mit `funde_inaturalist.py` und
`funde_zusammenfuegen.py` vor Schritt 3 dazu.

## Bildebenen der Website

| Ebene | Befehle | Ergebnis |
|---|---|---|
| Wald und Baumarten | `waldebenen.py`, dann `web_wald.py` | `web/wald/`, `web/wald.json` |
| Relief | `dgm_holen.py`, `relief.py`, dann `relief_web.py` | `web/relief/`, `web/relief.json` |

Beide Ebenen werden **nicht** in der Cloud erzeugt und müssen nach
einer Änderung eingecheckt werden.

## Örtliche Karten

```
python karte.py
```

Ergebnis: `karte_<art>.html` für alle elf Arten. **Achtung:** Bei
veralteten Wetterdaten holt `karte.py` selbst den neuen Stand per
`git pull --rebase --autostash`.

## Prüfen

| Befehl | prüft |
|---|---|
| `python pruefe_code.py` | fehlende Namen, Startschutz, Dateinamen — nach jedem Herunterladen |
| `python pruefe_stand.py` | ob alle Dateien den neuesten Stand haben |
| `python pruefe_orte.py` | Kennung und Koordinate aller Begleitdaten |
| `python pruefe_raster.py` | ob die Punkte auf einem einheitlichen Gitter liegen |
| `python herkunft.py` | was gemessen und was geschätzt ist |

Tests: siehe `README.md`.

---

# Was die Dateien tun

**arten.py** — die elf Pilzarten mit Schwellenwerten, Saisonfaktoren
und Baumartengewichten. **Die Datei zum Nachjustieren.** Neue Art =
neuer Eintrag, kein Eingriff in den Rest.

**kennwerte.py** — rechnet aus einer Tagesreihe alle Kenngrößen. Wird
von Karte, Export, Fundauswertung und Kalibrierung benutzt, damit alle
garantiert dasselbe rechnen. Nicht direkt ausführen.

**historie.py** — liest und schreibt die Monatsdateien der
Wetterhistorie. Nicht direkt ausführen.

**hintergrund.py** — die komplette Tagesreihe seit 2019 für
Vergleichspunkte. Ohne sie sagt „Funde bei 31 % Bodenfeuchte" nichts.

**kalibrieren.py** — rechnet das Auswahlverhältnis: Fundanteil
geteilt durch Anteil an Meldetagen, getrennt je Monatsgruppe.
Verhältnis 1,0 = kein Signal.

**karte.py** — örtliche Karten und Ladefunktionen für
`daten_export.py`. Beide müssen zusammenpassen.

**konfig.py** — gemeinsame Einstellungen, **noch nirgends
eingebunden** (siehe `TODO.md`).
