# Pilzkarte

Karte der Fundwahrscheinlichkeit für Speisepilze in der Region
Braunschweig – Wolfsburg – Elm – südliche Lüneburger Heide.

**→ [zc8yw2tmm8-cloud.github.io/pilzkarte](https://zc8yw2tmm8-cloud.github.io/pilzkarte/)**

Für jede von **1.632 Zellen à 2 × 2 km** wird mehrmals täglich
berechnet, wie gut die Bedingungen für **elf Pilzarten** gerade sind —
aus Wetter, Jahreszeit, Baumbestand und Boden.

## Was diese Karte nicht kann

**Sie erkennt keine Pilze und sagt nichts über Essbarkeit.** Jeder
Fund ist selbst sicher zu bestimmen, im Zweifel über eine
Pilzberatung.

Sie sagt auch nicht, ob an einer Stelle etwas steht — nur, ob die
Bedingungen dort gerade zu einer Art passen. Die Auflösung von 2 km
beantwortet „wohin fahre ich", nicht „wo genau".

Naturschutzgebiete sind in den örtlichen Karten eingezeichnet, auf der
Website noch nicht. Die Angaben stammen aus OpenStreetMap und sind
nicht rechtsverbindlich.

## Wie die Zahlen zustande kommen

```
Score = Wetterpunkte × Saisonfaktor × Bestandsfaktor × Bodenfaktor
```

Die Schwellenwerte sind **gemessen, nicht geschätzt**: an 3.834
GBIF-Fundmeldungen gegen rund 47.000 Vergleichstage. Maß ist das
Auswahlverhältnis — wie viel häufiger eine Bedingung bei Funden
auftritt als sonst.

### Der Maßstab ist entscheidend

Menschen gehen nicht überall und nicht jederzeit gleich oft in den
Wald. Kiefer macht 45 % der Waldfläche aus, aber nur 14 % der
Meldeorte; Eiche umgekehrt 21 % gegen 45 %.

Verglichen wird deshalb nicht gegen die Fläche, sondern gegen die
**Orte und Tage, an denen überhaupt Pilze gemeldet wurden**. Ohne
diese Korrektur misst man Sammlerverhalten statt Biologie.

Beim Wetter macht das viel aus: Beim Sommersteinpilz fiel das
Verhältnis bei viel Regen von 3,05 auf 1,22, sobald gegen Meldetage
gerechnet wurde. Der Wettereinfluss ist deshalb auf 62 % gedämpft
(`WETTER_SPANNE` in `arten.py`).

### Was gemessen ist und was nicht

| Faktor | gemessen für |
|---|---|
| Wetter | alle 11 Arten |
| Jahreszeit | alle 11 Arten |
| Bäume | Steinpilz, Marone, Parasol, Schwefelporling |
| Boden | dieselben vier |

`python herkunft.py` zeigt es je Art. Wo die Funde nicht reichten,
stammen die Werte aus der Literatur — oder es gibt gar keinen Faktor.

**Noch nicht geprüft:** Ob hohe Werte tatsächlich häufiger zu Funden
führen, weiß niemand. Dafür braucht es eine Saison mit eingetragenen
Funden *und* vergeblichen Suchen.

## Datenquellen

| Quelle | Verwendung | Bedingung |
|---|---|---|
| Open-Meteo | Wetter, Vorhersage, Höhen | freie Nutzung |
| OpenStreetMap | Waldflächen, Schutzgebiete, Ortsnamen | ODbL |
| Thünen-Institut | Baumartenkarte 10 m | Geodaten-Nutzungsbestimmungen des Bundes |
| LGLN Niedersachsen | Höhenmodell DGM1 | CC BY 4.0 |
| ISRIC SoilGrids | Bodeneigenschaften | CC BY 4.0 |
| GBIF | Fundmeldungen zur Kalibrierung | je Datensatz |

## Aufbau

| Datei | Zweck |
|---|---|
| `arten.py` | Artenkonfiguration — die Datei zum Nachjustieren |
| `kennwerte.py` | rechnet Kenngrößen aus Tagesreihen |
| `karte.py` | örtliche Karten, liefert Funktionen an den Export |
| `daten_export.py` | `web/daten.json` für die Website |
| `web/index.html` | die Website |
| `sammeln.py`, `prognose.py` | Datenabruf, läuft in der Cloud |
| `kalibrieren.py` | misst die Wetterschwellen an Funden |
| `baumarten_kalibrieren.py` | misst die Baumartengewichte |

### Prüfskripte

| Datei | prüft |
|---|---|
| `pruefe_code.py` | fehlende Namen, Startschutz, Dateinamen |
| `pruefe_stand.py` | ob alle Dateien aktuell und nicht vertauscht sind |
| `herkunft.py` | was gemessen und was geschätzt ist |
| `abhaengigkeiten.py` | erzeugt die Abhängigkeitskarte |

### Neu rechnen

```
python nachfuellen.py; python baumarten.py; python bodendaten.py; python hoehen.py; python ortsnamen.py; python karte.py; python daten_export.py; python web_bilder.py
```

Der tägliche Abruf läuft über GitHub Actions, viermal am Tag. Die
Website wird nach jedem erfolgreichen Lauf neu gebaut. Siehe
`SETUP_GITHUB.md` und `REIHENFOLGE.md`.

## Konten und Fundtagebuch

Optional, über Supabase. Wer angemeldet ist, kann Funde und
**Nullfunde** eintragen und Routen aufzeichnen. Anleitung in
`stufe3/ANLEITUNG_KONTEN.md`.

Die Nullfunde sind der eigentliche Zweck: Ohne sie lässt sich nicht
prüfen, ob die Karte stimmt.