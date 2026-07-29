# Reihenfolge zum Ausführen

Alle Dateien gehören in `C:\Users\Julia\pilzkarte` — neben `waldpunkte.csv`.

## Einmalig, in dieser Reihenfolge

| # | Befehl | Dauer | Erzeugt |
|---|---|---|---|
| 1 | `python test_felder.py` | 2 s | nichts — prüft nur, ob die neuen Wetterfelder liefern |
| 2 | `python hoehen.py` | 30 s | `hoehen.csv` |
| 3 | `python hintergrund.py` | ~2 min | `hintergrund.csv` (ca. 30 MB) |
| 4 | `python funde_arten.py` | ~5 min | `funde_arten.csv`, `aufwand.csv` |
| 5 | `python funde_wetter2.py` | 10–20 min | `funde_wetter2.csv` |
| 6 | `python kalibrieren.py` | 1–2 min | `kalibrierung.txt` |

**Schritt 1 ist Pflicht.** Wenn dort ein Feld fehlt, brechen 3, 5 und 6 ab.

## Historie neu aufbauen (Spalten haben sich geändert)

`wetter_historie.csv` und `wetter_prognose.csv` **löschen**, dann:

| # | Befehl | Dauer |
|---|---|---|
| 7 | `python nachfuellen.py` | ~5 min (90 Tage, ein Aufruf pro Punkt) |
| 8 | `python sammeln.py` | ~5 min |
| 9 | `python prognose.py` | ~5 min |
| 10 | `python karte.py` | 10 s |

## Täglich (Aufgabenplanung)

`python taeglich.py` — ruft `sammeln.py` und `prognose.py` auf.

---

# Was die Dateien tun

**kennwerte.py** — gemeinsames Modul. Rechnet aus einer Tagesreihe alle
Kenngrößen. Wird von Karte, Fundauswertung und Kalibrierung benutzt, damit
alle drei garantiert dasselbe rechnen. Nicht direkt ausführen.

**arten.py** — die fünf Pilzarten mit ihren Schwellenwerten, Saisonfaktoren
und Waldtyp-Gewichten. **Das ist die Datei zum Nachjustieren.** Neue Art =
neuer Eintrag, kein Eingriff in den Rest.

**test_felder.py** — prüft die neuen Open-Meteo-Felder.

**hoehen.py** — Höhenlage für alle Waldpunkte, 11 API-Aufrufe.

**hintergrund.py** — der wichtigste neue Baustein. Holt für 100 Waldpunkte
die komplette Tagesreihe seit 2019. Das ist die Referenz: ohne sie sagt
"Funde bei 31 % Bodenfeuchte" nichts.

**funde_arten.py** — Funde für alle fünf Arten von GBIF, plus die monatliche
Zahl *aller* Pilzmeldungen als Aufwandskorrektur.

**funde_wetter2.py** — ordnet jedem Fund die Wetterlage davor zu, inklusive
tiefer Bodenschichten, Verdunstung und 60-Tage-Bilanz.

**kalibrieren.py** — rechnet das Auswahlverhältnis: Fundanteil geteilt durch
Hintergrundanteil, getrennt je Monatsgruppe. Verhältnis 1,0 = kein Signal.
Liefert außerdem den Saisonfaktor zum Einsetzen in `arten.py`.

**karte.py** — oben `ART = "steinpilz"` ändern für andere Arten. Ergebnis:
`karte_steinpilz.html` usw.

---

# Was am Score neu ist

- **Timing-Regel gestrichen.** Traf nur auf 15,7 % der echten Funde zu.
- **Bodentemperatur-Fenster 9–16 °C** statt 12–19 °C. Ein Viertel aller
  Funde lag unter 10,3 °C.
- **Saisonfaktor.** Ein kühler, nasser Juli ergibt jetzt nicht mehr
  90 Punkte für Steinpilz. Stärke einstellbar über `SAISON_STAERKE`
  in `arten.py`.
- **Waldtyp-Faktor.** Wirkt, sobald `waldtypen.csv` gefüllt ist.
- **Wasserbilanz** (Regen minus Verdunstung) über 14 und 60 Tage.
  Ein Trockensommer dämpft jetzt bis in den Herbst.
- **Tiefe Bodenschicht 7–28 cm** wird gesammelt und angezeigt. Ob sie
  trennschärfer ist als 0–7 cm, sagt dir die Kalibrierung.
- **Höhenlage** wird mitgeführt — wichtig, weil ein Drittel der
  Fundmeldungen aus dem Harz kommt.

# Was noch offen ist

Die Werte für Regen und Lufttemperatur in `arten.py` sind noch geschätzt.
Ersetze sie durch die Bereiche, in denen `kalibrierung.txt` ein
Verhältnis über etwa 1,15 zeigt. Die vier Arten außer Steinpilz sind
komplett geschätzt — auch dafür liefert die Kalibrierung Zahlen, sofern
genug Funde zusammenkommen.
