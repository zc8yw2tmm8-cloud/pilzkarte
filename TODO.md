# Pilzkarte — offene Punkte

Stand: 3. August 2026

---

## Rechtliches

**Impressum und Datenschutzerklärung.** Die Seite ist öffentlich
erreichbar. Mit Stufe 3 kämen personenbezogene Daten dazu —
E-Mail-Adressen, Standorte, Zeitstempel. Ich bin kein Jurist und kann
nicht sagen, was genau nötig ist, aber es ist der einzige Punkt auf
dieser Liste, der ein Problem werden könnte statt nur eine fehlende
Funktion.

**Vor Stufe 3 klären.**

---

## Technische Schulden

Nichts davon ist dringend. Alles davon wird irgendwann teuer.

### Das Arbeitsgebiet steht in elf Dateien

`SUED, WEST, NORD, OST` sind in `aufwand_orte.py`, `baumarten.py`,
`baumarten_kalibrieren.py`, `funde_arten.py`, `funde_inaturalist.py`,
`ortsnamen.py`, `relief_weit.py`, `saison_weit.py`, `waldebenen.py`,
`waldraster_ergaenzen.py` und `konfig.py` jeweils eigenständig
gesetzt. Wer die Region wechseln will, muss alle finden.

`konfig.py` liegt fertig da, ist aber nirgends eingebunden. Die
Umstellung sollte **Datei für Datei mit Prüfung dazwischen**
passieren, nicht mechanisch — beim letzten Sammelumbau ist so eine
Funktion verlorengegangen.

Dasselbe gilt für `RASTER_KM` (5 Dateien), `MAX_UNSICHERHEIT` (5) und
die Artenliste (4).

### Zwei Karten, die auseinanderlaufen

`karte.py` erzeugt die örtliche Karte, `daten_export.py` die
Webfassung. Beide rechnen dieselben Scores, aber mit teils anderen
Einstellungen — Fundfenster 21 gegen 30 Tage.

Das ist gewollt, aber in drei Monaten weiß es niemand mehr.

**Auf Dauer sollte die örtliche Karte wegfallen.** `karte.py` würde
dann nur noch die Bilder für die Website liefern. Voraussetzung:
Die Webfassung muss erst Schutzgebiete und alle Waldebenen können.

### Dateinamen beim Herunterladen

Aus `dgm_holen.py` wird `Dgm holen.py`. Das hat schon dreimal
zugeschlagen und war jedes Mal schwer zu finden, weil das Skript
scheinbar grundlos eine alte Fassung benutzte.

`pruefe_code.py` meldet das jetzt. **Nach jedem Herunterladen laufen
lassen.**

### Zwei versetzte Gitter

Die urspruenglichen 1.046 Punkte und die 695 nachtraeglich
ergaenzten liegen auf zwei Gittern, die um eine halbe Zelle
gegeneinander versetzt sind — 89 Breitengrade auf 0,8 Grad statt der
erwarteten 44.

Die Karte gleicht das aus, indem sie die Kacheln aus dem
tatsaechlichen Punktabstand berechnet statt aus der Rastergroesse.
Das sieht richtig aus, aber der Zustand bleibt unsauber: Jeder Punkt
traegt Daten fuer eine 2-km-Zelle, gezeichnet wird er als 1-km-Kachel.
Benachbarte Zellen ueberlappen sich also in den Daten.

Sauber waere ein einheitliches Gitter. Das hiesse aber, etwa 200
Punkte zu verwerfen oder ihre Koordinaten zu verschieben — und dann
passten Baumarten und Bodenwerte nicht mehr zum Ort, an dem sie
erhoben wurden.

**Kein Handlungsdruck.** Aber beim naechsten grossen Umbau
mitdenken.

### Prognosedatei in der Versionsgeschichte

`wetter_prognose.csv` wird viermal täglich komplett ersetzt — 7.300
Zeilen raus, 7.300 rein. Nach einem Jahr sind das Millionen Zeilen
Versionsgeschichte für Daten, deren alte Fassungen niemand braucht.

Sauber wäre, sie gar nicht einzuchecken und nur im Bauvorgang zu
erzeugen. Kein Handlungsdruck, aber der Grund, warum es irgendwann
geändert werden sollte.

---

## Aus der Pruefung vom 4. August

Behoben:

- **hoehen.py verlor Daten.** Es holte alles neu und schrieb am Ende
  nur die erfolgreichen Bloecke — ein gescheiterter Lauf hat den
  halben Bestand geloescht. Setzt jetzt fort und sichert nach jedem
  Block.
- **Unbekannte Zellen bekamen zu hohe Werte.** Fehlten Boden oder
  Baumarten, wurde mit Faktor 1,0 gerechnet — eine Zelle ohne Daten
  stand damit ueber jeder vermessenen. Jetzt gilt der typische
  Regionswert.
- **Keine Warnung bei veralteten Daten.** Faellt der taegliche Lauf
  aus, rechnete die Karte stillschweigend weiter. Jetzt warnt sie ab
  drei Tagen, im Terminal und auf der Website.

Offen, nicht dringend:

- **baumarten.py ueberspringt Punkte ausserhalb der Kachelgrenzen,
  ohne es zu melden.** Bei 1.614 Punkten wurden 1.571 geschrieben.
  Die 43 fehlenden bekommen jetzt den Durchschnittswert, aber man
  erfaehrt nicht welche.
- **Begleitdateien enthalten Eintraege entfernter Punkte.**
  ortsnamen.csv und baumarten.csv haben noch Zeilen von Punkten, die
  aus dem Raster geflogen sind. Harmlos, aber die Zahlen in der
  Ausgabe taeuschen Vollstaendigkeit vor.
- **ortsnamen.py schreibt unvollstaendig**, wenn nur eine der beiden
  Overpass-Abfragen scheitert.

## Fehlende Funktionen

### Klein

- **Schutzgebiete in die Webkarte.** `schutzgebiete.geojson` liegt
  vor, örtlich sind sie drin, online fehlen sie. Bei einer
  öffentlichen Karte die auffälligste Lücke.
- **iNaturalist-Funde einbauen.** 83 zusätzliche liegen in
  `funde_inat.csv`. `funde_zusammenfuegen.py`, dann
  `funde_wetter2.py`.
- **Mehr Funde für Pfifferling und Sommersteinpilz.** Bei beiden
  reichen die Zahlen nicht für Boden und Bäume — dort stehen noch
  Schätzwerte. `saison_weit.py` liegt bereit.
- **Favicon.** Das Symbol im Browsertab fehlt.

### Mittel

- **Stufe 3: Konten, Fundtagebuch, Routen.** Vorbereitet in
  `stufe3/`, noch nicht eingebaut. Erst nach dem Rechtlichen.
- **Nullfunde.** Teil von Stufe 3, aber der eigentliche Gewinn: Ohne
  sie lassen sich die Schwellen nur einseitig prüfen.

### Reviere und eigene Zahlen

Aus den aufgezeichneten Routen **Reviere** bilden: ein Umkreis von
50 bis 100 m um den Weg. Dazu eigene Auswertungen — Funde je Stunde,
je Kilometer, welches Revier trägt am meisten.

Und, sobald mehrere Nutzer dabei sind: *„Dieses Revier teilst du dir
mit 3 anderen."* Dafür wäre die Sicht `fund_gerastert` schon
vorbereitet — sie zeigt gerasterte Funde erst ab drei Meldungen von
zwei Personen.

Voraussetzung ist eine Saison mit Aufzeichnungen. Vorher gäbe es
nichts auszuwerten.

### Groß

- **Senken deutschlandweit** in 25 m über das BKG-Höhenmodell. Zwei
  Abende, großer Sprung.
- **Deutschlandweite Scores.** Zwei bis drei Wochen, grundsätzlicher
  Umbau. Siehe `PLAN_DEUTSCHLAND.md`.

---

## Was zuerst?

1. **Rechtliches klären** — blockiert Stufe 3
2. **Schutzgebiete online** — ein Abend, schließt eine echte Lücke
3. **Konfig zusammenführen** — Datei für Datei, wenn Zeit ist

Alles andere ist Kür.

---

## Und der Punkt, der auf keiner Liste steht

Im September mit der Karte losgehen und schauen, ob sie stimmt.

Bisher ist alles Statistik gegen Statistik. Ob im Elm tatsächlich
steht, was die Karte verspricht, weiß niemand — und das ist die
einzige Prüfung, die wirklich zählt.
