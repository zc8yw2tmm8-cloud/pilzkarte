# Stufe 1: Der tägliche Lauf in die Cloud

Danach sammelt die Pilzkarte selbstständig weiter, auch wenn dein
Laptop aus ist. Rechne mit **einem bis zwei Abenden**.

Alles, was du brauchst, liegt fertig vor. Diese Anleitung sagt nur
noch, in welcher Reihenfolge.

---

## Schritt 1 — Historie aufteilen

**Am PC, vor allem anderen:**

```
python historie_aufteilen.py
```

Aus `wetter_historie.csv` werden Monatsdateien im Ordner
`wetter_historie/`. Prüfe die ausgegebenen Zahlen — Zeilen und
Zeitraum müssen zur alten Datei passen.

Dann einmal zur Kontrolle:

```
python karte.py
```

Läuft das durch und stimmt die Zeitspanne, kann `wetter_historie.csv`
gelöscht werden. `sammeln.py`, `nachfuellen.py` und `karte.py` sind
bereits umgestellt.

**Warum das sein muss:** Die Datei wächst um 1.000 Zeilen am Tag.
Täglich eingecheckt, speichert Git jedes Mal eine vollständige Kopie —
nach einem Jahr mehrere Gigabyte für 40 MB Nutzdaten. Mit
Monatsdateien wächst nur die des laufenden Monats.

---

## Schritt 2 — Git installieren

Falls noch nicht vorhanden: **git-scm.com**, Standardeinstellungen.

Prüfen:

```
git --version
```

---

## Schritt 3 — Repository anlegen

Auf **github.com** oben rechts auf **+** → **New repository**.

| Feld | Wert |
|---|---|
| Name | `pilzkarte` |
| Sichtbarkeit | **Public** |
| README, .gitignore, Lizenz | **nichts ankreuzen** |

Auf **Create repository** klicken. Die angezeigte Adresse merken, sie
sieht so aus: `https://github.com/deinname/pilzkarte.git`

**Warum öffentlich:** GitHub Actions ist für öffentliche Repositories
unbegrenzt kostenlos, für private nur 2.000 Minuten im Monat. Und die
Daten sind ohnehin frei — Wetter, OpenStreetMap, Thünen, GBIF.

**Was NICHT hineingehört:** persönliche Fundorte. Die kommen später in
Supabase, nicht ins Repository. `.gitignore` schließt außerdem die
großen Zwischendaten aus.

---

## Schritt 4 — Hochladen

Im Terminal, im Ordner `pilzkarte`:

```
git init
git add .
git commit -m "Pilzkarte, erster Stand"
git branch -M main
git remote add origin https://github.com/DEINNAME/pilzkarte.git
git push -u origin main
```

`DEINNAME` ersetzen. Beim ersten Mal fragt Git nach Anmeldedaten —
GitHub verlangt statt des Passworts einen **Personal Access Token**:
Einstellungen → Developer settings → Personal access tokens → Tokens
(classic) → Generate new token, Haken bei `repo`. Den Token wie ein
Passwort eingeben.

**Vorher prüfen, was hochgeht:**

```
git status
```

Erscheinen dort `kacheln/`, `dgm/` oder `bilder/`, greift `.gitignore`
nicht — dann Bescheid sagen, bevor du weitermachst. Das wären hunderte
Megabyte.

---

## Schritt 5 — Ersten Lauf auslösen

Auf GitHub im Repository auf **Actions**. Falls eine Nachfrage kommt,
Workflows zulassen.

Links **Wetterdaten sammeln** anklicken, rechts **Run workflow**.

Nach zwei bis fünf Minuten sollte ein grüner Haken stehen. Bei einem
roten Kreuz: auf den Lauf klicken, die Ausgabe kopieren und mir
schicken.

Ab dann läuft es jeden Morgen um sechs Uhr UTC von selbst — acht Uhr
im Sommer, sieben im Winter.

---

## Schritt 6 — Aufgabenplanung abschalten

Auf dem Laptop die Aufgabenplanung öffnen, `Pilzdaten sammeln`
deaktivieren. Sonst sammeln zwei Stellen dasselbe.

Der Laptop kann jetzt aus bleiben.

---

## Der tägliche Ablauf danach

Wenn du die Karte sehen willst:

```
git pull
python karte.py
```

Das erste holt die neuen Wetterdaten aus der Cloud, das zweite baut
die Karte. In Stufe 2 entfällt auch das — dann steht die Karte im Netz.

---

## Was schiefgehen kann

**Der Lauf schlägt fehl mit einem Abruffehler.** GitHub-Rechner teilen
sich Adressen, Open-Meteo drosselt möglicherweise stärker als von
zuhause. Die Skripte wiederholen bis zu viermal; hilft das nicht,
senken wir die Zahl gleichzeitiger Abrufe.

**Der geplante Lauf setzt nach 60 Tagen aus.** GitHub schaltet Zeitpläne
in Repositories ohne Aktivität ab. Da täglich etwas eingecheckt wird,
sollte das nicht eintreten — falls doch, kommt eine Mail.

**Ein Tag fehlt.** Nicht schlimm, die Fenster sind 14 und 60 Tage lang.
Der sonntägliche Lauf von `nachfuellen.py` schließt Lücken automatisch.

**Zwei Stellen ändern dieselbe Datei.** Wenn du lokal `sammeln.py`
ausführst und die Cloud auch, gibt es beim `git pull` einen Konflikt.
Deshalb Schritt 6 nicht vergessen.
