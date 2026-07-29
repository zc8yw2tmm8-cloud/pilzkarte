# Pilzkarte

Karte der Fundwahrscheinlichkeit für Speisepilze in der Region
Braunschweig – Wolfsburg – südliche Lüneburger Heide.

Für jede von 1.046 Waldzellen à 2 × 2 km wird täglich berechnet, wie
gut die Bedingungen für sieben Pilzarten gerade sind — aus Wetter,
Bodeneigenschaften, Baumbestand und Jahreszeit.

## Was diese Karte nicht kann

**Sie erkennt keine Pilze und sagt nichts über Essbarkeit.** Jeder Fund
ist selbst sicher zu bestimmen, im Zweifel über eine Pilzberatung.

Naturschutzgebiete sind eingezeichnet, die Angaben stammen aus
OpenStreetMap und sind nicht rechtsverbindlich. Maßgeblich ist das
jeweilige Landesverzeichnis.

## Wie die Zahlen zustande kommen

```
Score = Wetterpunkte × Saisonfaktor × Bestandsfaktor × Bodenfaktor
```

Die Schwellenwerte sind nicht geschätzt, sondern an 2.819
Fundmeldungen gegen rund 47.000 Vergleichstage gemessen. Die
Einzelheiten stehen auf der Infoseite, die beim Kartenlauf entsteht.

## Datenquellen

| Quelle | Verwendung | Bedingung |
|---|---|---|
| Open-Meteo | Wetter, Vorhersage | freie Nutzung |
| OpenStreetMap | Waldflächen, Schutzgebiete, Ortsnamen | ODbL |
| Thünen-Institut | Baumartenkarte 10 m | Geodaten-Nutzungsbestimmungen des Bundes |
| LGLN Niedersachsen | Höhenmodell DGM1 | CC BY 4.0 |
| ISRIC SoilGrids | Bodeneigenschaften | CC BY 4.0 |
| GBIF | Fundmeldungen zur Kalibrierung | je Datensatz |

## Aufbau

| Datei | Zweck |
|---|---|
| `kennwerte.py` | rechnet Kenngrößen aus Tagesreihen |
| `arten.py` | Artenkonfiguration — die Datei zum Nachjustieren |
| `karte.py` | erzeugt die Karten |
| `sammeln.py`, `prognose.py` | täglicher Datenabruf |
| `kalibrieren.py` | misst die Schwellenwerte an Funden |

Der tägliche Abruf läuft über GitHub Actions. Siehe `SETUP_GITHUB.md`.
