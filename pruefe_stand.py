"""
Prueft, ob alle Dateien auf dem neuesten Stand sind.

Hintergrund: In VS Code eingefuegter Code landet erst mit Strg+S auf
der Festplatte. Ohne das liest Python weiter die alte Fassung, und
Git sieht keine Aenderung - der Fehler ist dann kaum zu finden, weil
im Editor alles richtig aussieht.

Dieses Skript sucht in jeder Datei nach Merkmalen, die nur in der
neuesten Fassung vorkommen.

Ein Fehlen bedeutet nicht immer ein Problem: Vielleicht wurde die
Datei absichtlich nie ausgetauscht. Aber es ist der schnellste Weg,
um zu sehen, wo man nachschauen sollte.
"""
import os

# Datei -> Merkmale, die in der neuesten Fassung stehen muessen
MERKMALE = {
    "karte.py": [
        ("gueltige_punkte", "Filter auf waldpunkte.csv"),
        ("juengste_messung", "Altersangabe der Daten"),
        ("feldgrenzen" if False else "PUNKTE_DATEI", "Punktdatei"),
        ("schub_hinweis", "Regenereignis-Hinweis"),
        ("if __name__", "Startschutz beim Import"),
        ("ZIELTAGE = [0, 1, 2, 3, 4, 5, 6]", "sieben Stichtage"),
    ],
    "arten.py": [
        ("UNBEKANNT_BESTAND", "Wert fuer unbekannte Zellen"),
        ("frost_abzug", "gemessener Frostabzug"),
        ("waldanteil_wirkung", "artspezifische Walddaempfung"),
        ("boden_ton", "Tongehalt statt Sand"),
        ("schubfenster", "Schubfenster je Art"),
    ],
    "kennwerte.py": [
        ("finde_ereignisse", "Regenereignisse"),
        ("EREIGNIS_MM", "Schwelle fuer ein Ereignis"),
    ],
    "hoehen.py": [
        ("lade_vorhandene", "setzt fort statt neu zu holen"),
        ("ANLAEUFE", "mehrere Anlaeufe je Block"),
    ],
    "daten_export.py": [
        ("letzter_regen", "letzter Regen im Popup"),
        ("gitter_angaben", "Kacheln am Gitter ausrichten"),
        ("gemessen_bis", "Altersangabe"),
        ("regen_ereignis", "Regenereignis"),
    ],
    "sammeln.py": [
        ("hole_buendel", "mehrere Orte je Anfrage"),
        ("buendel_moeglich", "Buendelung wird geprueft"),
        ("historie.anhaengen", "Monatsdateien"),
    ],
    "prognose.py": [
        ("hole_buendel", "mehrere Orte je Anfrage"),
    ],
    "nachfuellen.py": [
        ("hole_buendel", "mehrere Orte je Anfrage"),
        ("ARCHIV_VERZUG", "Zeitraum am Archivrand teilen"),
        ("historie.anhaengen", "Monatsdateien"),
    ],
    "historie.py": [
        ("monatsdatei", "Wetterdaten nach Monaten"),
    ],
    "weichzeichnen.py": [
        ("_GEOMETRIE", "Geometrie wird wiederverwendet"),
        ("BILDORDNER", "Zielordner einstellbar"),
        ("STREUUNG_KM = 1.4", "Streuung fuer 2-km-Raster"),
    ],
    "web_bilder.py": [
        ("z[\"scores\"][art][i] or 0", "alle Zellen je Bild"),
    ],
    "waldraster_ergaenzen.py": [
        ("ALLE_ZELLEN", "Schalter fuer lueckenloses Gitter"),
        ("frage_block", "gebuendelte Abfrage"),
        ("hoechste_nummer", "keine doppelten Kennungen"),
    ],
    "waldebenen.py": [
        ("BILDORDNER", "Zielordner einstellbar"),
        ("wald_grenzen.txt", "Grenzen fuer die Website"),
    ],
    "infoseite.py": [
        ("Waldanteil", "Erklaerung zum Waldanteil"),
    ],
    "web/index.html": [
        ("pfeilknopf", "Pfeile am Ausblick-Regler"),
        ("regenzeilen", "letzter Regen im Popup"),
        ("feldgrenzen", "Kacheln am Gitter"),
        ("setzeDeckkraft", "Deckkraft fuer beide Ansichten"),
        ("zeigeWeichbild", "weiche Darstellung"),
        ("gemessen_bis", "Warnung bei alten Daten"),
        ("cluster: true", "Fundpunkte gebuendelt"),
        ('data-stil="hart">Raster', "Raster als Voreinstellung"),
    ],
    "web/info.html": [
        ("Sechsmal danebengelegen", "Erklaerseite neu"),
        ("artwahl", "Beispiel zum Durchklicken"),
    ],
}


def main():
    print("Pruefe, ob alle Dateien den neuesten Stand haben\n")

    fehlend_gesamt = 0
    fehlende_dateien = []

    for datei, merkmale in MERKMALE.items():
        pfad = datei.replace("/", os.sep)
        if not os.path.exists(pfad):
            print(f"{datei}: DATEI FEHLT")
            fehlende_dateien.append(datei)
            continue

        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            inhalt = f.read()

        fehlt = [(m, w) for m, w in merkmale if m not in inhalt]
        if fehlt:
            fehlend_gesamt += len(fehlt)
            print(f"{datei}  -  {len(fehlt)} von {len(merkmale)} fehlen:")
            for m, w in fehlt:
                print(f"     {w}")
            print()

    if not fehlend_gesamt and not fehlende_dateien:
        print("Alle Dateien sind aktuell.")
        return

    print("=" * 58)
    print("Diese Dateien noch einmal ablegen - und danach in VS Code")
    print("mit Strg+S speichern.")
    print()
    print("Tipp: File -> Auto Save einschalten, dann kann es nicht")
    print("mehr passieren.")


main()
