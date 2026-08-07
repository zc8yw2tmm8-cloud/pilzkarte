# Pilzkarte — Projektanweisungen

Karte der Fundwahrscheinlichkeit für Speisepilze, Region
Braunschweig – Wolfsburg – Elm – südliche Lüneburger Heide.
Läuft öffentlich unter
https://zc8yw2tmm8-cloud.github.io/pilzkarte/

---

## Umgang

Julia ist Programmier-Anfängerin, denkt aber fachlich mit und hat
mehrfach Fehler im Ansatz gefunden. Erklärungen auf Augenhöhe,
keine Belehrung.

**Immer die Befehle mitschreiben**, nicht nur beschreiben was zu tun
ist. Sie arbeitet unter Windows mit PowerShell — dort Strichpunkte
zwischen Befehlen, keine Kommas.

Alles auf Deutsch: Antworten, Code-Kommentare, Variablennamen,
Ausgaben der Skripte. Keine Umlaute in Terminalausgaben (Windows-
Konsole), aber Umlaute in HTML und Markdown.

---

## Wie das System rechnet

```
Score = Wetterpunkte(0–100) × Saison × Bestand × Boden
```

Die Schwellenwerte sind **gemessen, nicht geschätzt**: rund 3.600
GBIF-Fundmeldungen gegen 47.000 Vergleichstage. Maß ist das
Auswahlverhältnis — Anteil bei Funden geteilt durch Anteil an
normalen Tagen.

**Elf Arten.** Sieben kalibriert, vier neu und noch geschätzt
(hexenroehrling, netzhexe, reizker, krauseglucke).

### Acht widerlegte Annahmen

Wichtig für jede neue Behauptung über Pilzbiologie: Bisher lagen
plausible Annahmen achtmal falsch.

- Schub 8–14 Tage nach Regen → traf auf 15,7 % zu, weniger als Zufall
- Marone als Sandpilz → verhält sich wie Steinpilz
- Parasol trockenheitsverträglich → ist er nicht
- Sommersteinpilz wärmeliebend → unter 17,4 °C am besten
- Marone und Birkenpilz frosthart → sind sie nicht
- Alle Arten meiden Kiefer → Beobachterverzerrung
- Beide Hexenröhrlinge als Herbstpilze → sind Sommerpilze
- Netzhexe als Kalkzeiger → noch ungeprüft, nur 10 Fundorte

**Nie Lehrbuchwerte einsetzen, ohne sie als geschätzt zu
kennzeichnen.**

### Beobachterverzerrung

Der wichtigste methodische Befund: Kiefer macht 45,3 % der
Waldfläche aus, aber nur 11,7 % der Pilzmeldeorte. Eiche 21,4 %
gegen 43,6 %.

Deshalb wird gegen **Meldeorte** verglichen, nicht gegen Fläche.
Dateien: `aufwand_orte.csv`, `bodendaten_aufwand.csv`.

---

## Aufbau

`karte.py` ist die Drehscheibe. Importiert `arten`, `farben`,
`historie`, `infoseite`, `kennwerte`, `waldebenen`, `weichzeichnen`
— und wird von `daten_export.py` importiert.

`arten.py` ist die Datei zum Nachjustieren: alle Bänder,
Saisonkurven, Baumarten- und Bodenfaktoren.

Vollständige Abhängigkeiten in `ABHAENGIGKEITEN.md`, erzeugt mit
`python abhaengigkeiten.py`.

### Reihenfolge beim Neurechnen

```
python nachfuellen.py; python baumarten.py; python bodendaten.py; python hoehen.py; python ortsnamen.py; python karte.py; python daten_export.py; python web_bilder.py
```

Bei `bodendaten.py` die Fundorte-Frage mit `n` beantworten, sonst
`echo n | python bodendaten.py`.

### Hochladen

```
git add .; git commit -m "..."; git pull --rebase; git push
```

Danach auf GitHub: **Actions → Seite bauen → Run workflow**. Der
Seitenbau läuft nicht automatisch nach einem Push.

---

## Regeln beim Ändern

**Module brauchen Startschutz.** Alles, was importiert wird
(`karte`, `arten`, `historie`, `weichzeichnen`, `waldebenen`,
`infoseite`, `kennwerte`, `farben`, `gebiete`, `konfig`), braucht
`if __name__ == "__main__":` vor `main()`. Sonst löst ein Import
einen vollständigen Rechenlauf aus.

**Nach jeder Änderung prüfen:**

```
python pruefe_code.py     # fehlende Namen, Startschutz, Dateinamen
python abhaengigkeiten.py # Karte neu erzeugen
```

**Bei Textersetzungen die Funktionsliste vorher und nachher
vergleichen.** Zweimal ist beim Umbauen eine Funktion verloren
gegangen — `hole_tag` in `sammeln.py`, `zeigeWeichbild` in
`index.html`. Beide Male blieb die Datei syntaktisch gültig, der
Fehler kam erst zur Laufzeit.

**JavaScript nicht nur auf Syntax prüfen, sondern ausführen.** Mit
Node und Beispieldaten aus `web/daten.json`.

**Keine Rundungen bei Koordinaten und Gitterschritten.** Fünf
Nachkommastellen sind auf 1 m genau — ein Punkt dicht an einer
Feldgrenze kippt dadurch ins Nachbarfeld, und auf der Karte
erscheinen Löcher und doppelte Kacheln. Das ist zweimal passiert.

**Konstanten stehen mehrfach.** `ARTEN` in vier Dateien mit
verschiedenen Inhalten, `SUED/WEST/NORD/OST` in elf, `RASTER_KM` in
fünf. Beim Hinzufügen einer Art alle vier ARTEN-Vorkommen nachziehen.

---

## Entscheidungen, die begründet sind

Nicht ohne Not umkehren.

**Walddämpfung wirkt nur schwach** (`WALDANTEIL_WIRKUNG` um 0,10).
Der Waldanteil misst, wie wahrscheinlich eine *zufällige* Stelle
Wald ist. Ein Sammler fragt aber, wie seine Chancen in *dem
Waldstück dort* stehen — dafür ist egal, ob drumherum Acker liegt.

**Das Gitter deckt die ganze Region ab, nicht nur Wald.** Julias
Argument: Brachliegende Felder tragen Parasole, und wer die Karte
benutzt, sucht von selbst keinen Steinpilz auf dem Maisacker. Wer
wissen will, ob dort Wald steht, blendet die Baumartenebene ein.

**Unbekannte Zellen bekommen 0,78 bzw. 0,85, nicht 1,0.** Sonst
stünde eine Zelle ohne Daten über jeder vermessenen.

**Die weiche Darstellung kommt als vorgerechnetes Bild.** Im Browser
lässt sie sich nicht nachbauen: Halbdurchsichtige Flächen addieren
sich auf, statt sich zu mitteln.

**Je Gitterfeld nur eine Kachel.** Die Karte fasst selbst zusammen,
damit doppelte Daten nie doppelt gefärbt erscheinen.

**Kein Warnkasten beim Seitenaufruf.** Der Hinweis steht als schmale
Zeile am unteren Kartenrand.

---

## Offene Punkte

Vollständig in `TODO.md`. Das Wichtigste:

1. **Impressum und Datenschutzerklärung** — blockiert Stufe 3
   (Konten, Fundtagebuch, Routen; vorbereitet in `stufe3/`)
2. **Schutzgebiete in die Webkarte** — `schutzgebiete.geojson` liegt
   vor, örtlich eingebunden, online fehlend
3. **Bodenkalibrierung gegen Meldeorte** — `boden_aufwand.py` holt
   die Daten, dauert Stunden

---

## Grenzen der Dienste

**Open-Meteo** drosselt bei etwa 10.000 gewichteten Aufrufen am Tag.
Zurückgesetzt um 2 Uhr nachts. Der Cloud-Lauf holt viermal täglich
die Prognose für 1.632 Punkte — bei örtlichen Läufen wird es eng.
`nachfuellen.py` und `hoehen.py` setzen fort.

**SoilGrids** hört nach einigen hundert Abfragen zeitweise auf zu
antworten, meist ohne Fehlermeldung.

**Overpass** antwortet oft mit HTTP 504. Drei Server werden
nacheinander probiert. `ortsnamen.py` schreibt unvollständig, wenn
nur eine der beiden Abfragen scheitert — dann Waldnamen neu holen.