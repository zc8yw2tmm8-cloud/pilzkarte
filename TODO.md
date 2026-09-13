# Pilzkarte — offene Punkte

Stand: 13. September 2026

---

## Rechtliches

**Impressum und Datenschutzerklärung fehlen weiterhin.** Die Website
enthält keines von beiden. Inzwischen sind die Konten in Betrieb —
E-Mail-Adressen, Fundorte, Routen und Zeitstempel werden also schon
gespeichert. Ich bin kein Jurist und kann nicht sagen, was genau nötig
ist, aber es ist der einzige Punkt auf dieser Liste, der ein Problem
werden könnte statt nur eine fehlende Funktion.

**Vorrangig klären.**

---

## Abruflimit bei Open-Meteo prüfen

`prognose.py` holt viermal täglich alle 1.632 Orte, `sammeln.py` fragt
dazu zwei Modelle ab (`icon_d2,best_match`). Mehr-Orte-Anfragen zählen
bei Open-Meteo je Ort, mehrere Modelle und viele Felder zählen
zusätzlich. Grob überschlagen liegt der Bedarf damit schon heute in der
Nähe der kostenlosen Tagesgrenze (nach meinem Stand etwa 10.000 — nicht
nachgeprüft).

Am 12. September scheiterten drei Prognoseläufe an 120, 40 und 120
fehlenden Orten; die Ursache war damals nicht protokolliert. Seitdem
schreibt `prognose.py` den HTTP-Status mit. **In den nächsten
Laufprotokollen auf HTTP 429 achten** und die aktuellen Bedingungen
auf open-meteo.com nachlesen. Falls das Limit greift: weniger
Prognoseläufe am Tag oder Felder sparen — und ein Grund mehr für den
DWD-Test unten.

---

## Ziel: Karte für ganz Deutschland

Das heutige Gebiet ist rund 89 × 71 km groß, Deutschland etwa 57-mal
so groß. Bei gleichem 2-km-Raster wären das grob 50.000 bis 90.000
Zellen statt 1.632. Ein Plan (`PLAN_DEUTSCHLAND.md`) ist noch nicht
geschrieben. Was feststeht:

**Wetterquelle.** `sammeln.py` und `prognose.py` fragen Open-Meteo je
Punkt ab. Bündel zählen dort je Ort, der heutige Bedarf liegt schon
bei grob 10.000 Ortsabrufen am Tag. Für Deutschland braucht es eine
Quelle, die ganze Raster liefert — naheliegend ICON-D2 direkt vom DWD
(opendata.dwd.de, GRIB). **Erster Schritt:** einen Lauf holen, Werte
für die heutigen 1.632 Punkte herausziehen und mit Open-Meteo
vergleichen. Offen ist vor allem die Bodenfeuchte.

**Auslieferung.** `web/daten.json` hat 5,4 MB — hochgerechnet rund
300 MB. Waldebenen (heute ein Gesamtbild 3563 × 4454) und Relief
müssen ebenfalls gekachelt werden, damit nur der sichtbare Ausschnitt
lädt.

**Grundlagendaten deutschlandweit.** Baumarten (Thünen) gibt es schon
bundesweit. Boden kommt heute punktweise von SoilGrids — bei
Zehntausenden Punkten besser als Rasterabzug. Das DGM1 des LGLN deckt
nur Niedersachsen ab; für Senken deutschlandweit das 25-m-Modell des
BKG nehmen.

**Neues Gitter.** Das jetzige ist nicht einheitlich (siehe unten). Beim
Neuaufbau für Deutschland von Anfang an ein sauberes Gitter anlegen.

**Schutzgebiete** sind bis dahin zurückgestellt (siehe unten).

Voraussetzung für alles davon: **das Arbeitsgebiet an einer Stelle**
(nächster Abschnitt).

---

## Technische Schulden

### Das Arbeitsgebiet steht in 13 Dateien

`SUED, WEST, NORD, OST = 52.05, 10.10, 52.85, 11.15` steht in
`aufwand_orte.py`, `aufwand_tage.py`, `baumarten.py`,
`baumarten_kalibrieren.py`, `funde_inaturalist.py`,
`luecken_fuellen.py`, `ortsnamen.py`, `raster_ausrichten.py`,
`schutzgebiete.py`, `waldebenen.py`, `waldraster.py` und
`waldraster_ergaenzen.py`, in `daten_export.py` als einzelne Zahlen.
Das größere Fundgebiet steht eigenständig in `funde_arten.py`,
`saison_weit.py` hat ein drittes.

`konfig.py` liegt fertig da, ist aber nirgends eingebunden. Die
Umstellung sollte **Datei für Datei mit Prüfung dazwischen**
passieren, nicht mechanisch — beim letzten Sammelumbau ist so eine
Funktion verlorengegangen.

Dasselbe gilt für `RASTER_KM` (8 Dateien), `MAX_UNSICHERHEIT` (4,
davon `funde_wetter2.py` mit 5000 statt 500) und die Artenliste
(`arten.py`, `funde_arten.py`, `funde_inaturalist.py`,
`saison_weit.py`, `konfig.py`). `python abhaengigkeiten.py` listet
alle mehrfach gesetzten Konstanten.

### Zwei Karten, die auseinanderlaufen

`karte.py` erzeugt die örtliche Karte, `daten_export.py` die
Webfassung. Beide rechnen dieselben Scores, aber mit teils anderen
Einstellungen — Fundfenster 21 (`FUNDE_FENSTER`) gegen 30 Tage
(`fund_fenster`).

**Auf Dauer sollte die örtliche Karte wegfallen.** Die Webfassung kann
inzwischen alle Waldebenen und das Relief; es fehlen nur noch die
Schutzgebiete.

### Kein einheitliches Gitter

`pruefe_raster.py` am 13. September: 1.632 Punkte auf 90 Breiten- und
72 Längenlagen, 8 bzw. 34 verschiedene Gitterlagen, kleinster
Ost-West-Abstand 0 m. Die Karte gleicht das beim Zeichnen aus, aber
benachbarte Zellen überlappen sich in den Daten.

`raster_ausrichten.py` würde Punkte verschieben — dann passten
Baumarten und Bodenwerte nicht mehr zum Ort, an dem sie erhoben
wurden. **Nicht nachträglich reparieren, sondern beim
Deutschland-Umbau neu anlegen.**

`pruefe_raster.py` empfiehlt am Ende trotzdem noch „Behebung: python
raster_ausrichten.py". Diesen Hinweis anpassen, damit ihn niemand
blind befolgt.

### Begleitdateien passen nicht ganz zu den Punkten

Gegen `waldpunkte.csv` geprüft am 13. September:

| Datei | Zeilen ohne Punkt | Punkte ohne Zeile |
|---|---:|---:|
| `bodendaten.csv` | 156 | 118 |
| `hoehen.csv` | 162 | 0 |
| `baumarten.csv` | 0 | 6 |
| `ortsnamen.csv` | 0 | 0 |

Die 118 Punkte ohne Bodenwerte liegen auch nicht unter einer anderen
Kennung am selben Ort vor; sie rechnen mit dem Regionswert. Klären, ob
SoilGrids dort nichts liefert oder der Abruf fehlte. Die überzähligen
Zeilen sind harmlos, täuschen aber Vollständigkeit vor.

### Wetterdateien in der Versionsgeschichte

`wetter_prognose.csv` wird viermal täglich komplett ersetzt (derzeit
11.424 Zeilen). Sauber wäre, sie nicht einzuchecken und nur im
Bauvorgang zu erzeugen.

`wetter_historie.csv` steht in `.gitignore`, wird aber noch von Git
verfolgt. Ihr Inhalt liegt inzwischen in den Monatsdateien unter
`wetter_historie/`; vor dem Entfernen die Messwerte vergleichen.

### Dateinamen beim Herunterladen

Aus `dgm_holen.py` wird `Dgm holen.py`. Das hat schon dreimal
zugeschlagen. `pruefe_code.py` meldet das. **Nach jedem Herunterladen
laufen lassen.**

### rasterio fehlt in der lokalen Python-Umgebung

Python 3.12 auf dem Laptop hat kein `rasterio`, obwohl es in
`requirements.txt` steht. Die Walddaten-Skripte und die Tests
`test_wald_cache.py` und `test_wald_geo.py` laufen nur mit dem
Beiordner `lokale_notizen/python_gis` im Suchpfad — dann bestehen
beide. Sauber wäre `pip install -r requirements.txt`, damit nichts von
einem Notizordner abhängt.

### Nicht im Repository

Datenbankschema, Migrationen und Zugriffsregeln der Supabase-Datenbank
sind nirgends versioniert. Eine Anleitung zu den Konten fehlt ebenfalls.

---

## Aus der Prüfung vom 7. September

Erledigt: Ortszuordnung bereinigt (`pruefe_orte.py`), gespeicherte
Texte sicher ausgegeben, Fundscore passend zu Art und Datum, Prognose
nur bei 98 % Abdeckung ersetzt, fehlende Scores grau statt null.

Offen:

- **Popups bleiben beim Tages- oder Artwechsel stehen.**
  `aktualisiere()` in `web/index.html` schließt ein offenes Popup
  nicht und rechnet es auch nicht neu.
- **Wetterfenster sind einen Tag länger als benannt.** `kennwerte.py`
  zählt mit `<= 14`, `<= 60`, `<= 5` den Stichtag mit — also 15, 61 und
  6 Tage. Erst fachlich entscheiden, dann Grenzen und Kalibrierung
  gemeinsam anpassen, nicht nur `<=` gegen `<` tauschen.
- **`ortsnamen.py` schreibt unvollständig**, wenn nur eine der beiden
  Overpass-Abfragen scheitert (bricht nur ab, wenn beide leer sind).
- **`pruefe_code.py` meldet vier mögliche Divisionen durch null**
  (`bodenanalyse.py` 171, `monatsnormale.py` 101/102,
  `wetter_pruefen.py` 150). Prüfen, ob davor abgesichert ist.
- **`pruefe_stand.py` vermisst in `web_bilder.py` die Stelle „alle
  Zellen je Bild".** Klären, ob die Prüfregel veraltet ist oder der
  Code.
- **`requirements.txt`** nennt nur Mindestversionen (außer rasterio).

---

## Fehlende Funktionen

### Klein

- **iNaturalist-Funde einbauen.** 279 Beobachtungen liegen in
  `funde_inat.csv`, `funde_arten.csv` enthält bisher nur die 3.834
  GBIF-Funde. `funde_zusammenfuegen.py`, dann `funde_wetter2.py` und
  `kalibrieren.py`.
- **Mehr Funde für Pfifferling (149) und Sommersteinpilz (114).** Für
  Boden und Bäume reicht das nicht — dort stehen noch Schätzwerte.
  `saison_weit.py` liegt bereit.

### Schutzgebiete — zurückgestellt bis zur Deutschlandkarte

`schutzgebiete.geojson` (OpenStreetMap) ist in den örtlichen Karten
drin, online nicht. Gezeigt werden sollen nur einzeln belegte
Sammelverbote, keine pauschale Einstufung jedes Naturschutzgebiets.
Ausgesparte Flächen und zusammengesetzte Grenzen müssen erhalten
bleiben — der jetzige OSM-Import ignoriert Innenringe. Quellen:
Geodatendienst Niedersachsen mit Verordnungslinks, BfN-WFS für
Deutschland.

### Reviere und eigene Zahlen

Aus den aufgezeichneten Routen **Reviere** bilden: ein Umkreis von
50 bis 100 m um den Weg. Dazu eigene Auswertungen — Funde je Stunde,
je Kilometer, welches Revier trägt am meisten.

Und, sobald mehrere Nutzer dabei sind: *„Dieses Revier teilst du dir
mit 3 anderen."* Dafür wäre die Sicht `fund_gerastert` schon
vorbereitet — sie zeigt gerasterte Funde erst ab drei Meldungen von
zwei Personen.

Voraussetzung ist eine Saison mit Aufzeichnungen.

### Auswertung der Nullfunde

Funde und Nullfunde lassen sich eintragen. Sobald eine Saison
zusammengekommen ist: prüfen, ob hohe Werte tatsächlich häufiger zu
Funden führen, und die Schwellen von beiden Seiten nachjustieren.

---

## Was zuerst?

1. **Rechtliches klären** — die Konten sind schon in Betrieb
2. **Wetter direkt vom DWD testen** — entscheidet, wie die
   Deutschlandkarte gebaut wird; danach `PLAN_DEUTSCHLAND.md`
3. **Konfig zusammenführen** — Datei für Datei, wenn Zeit ist

Alles andere ist Kür.

---

## Und der Punkt, der auf keiner Liste steht

Jetzt ist September: mit der Karte losgehen und schauen, ob sie
stimmt — und jeden Gang eintragen, auch die ohne Fund.

Bisher ist alles Statistik gegen Statistik. Ob im Elm tatsächlich
steht, was die Karte verspricht, weiß niemand — und das ist die
einzige Prüfung, die wirklich zählt. Bevor das Modell auf ganz
Deutschland ausgerollt wird, sollte es hier einmal bestanden sein.
