"""
Liest die Klassenbezeichnungen der Thuenen-Baumartenkarte aus.

Bei Rasterebenen steckt die Zuordnung in einer Farbtabelle, nicht in
Regeln - deshalb hat der erste Versuch nichts gefunden. Dieses Skript
probiert vier Wege durch und zeigt zur Not die Rohantwort.

Ergebnis: klassen.csv  (wert,name)
"""
import requests
import csv
import json
import re

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

BASIS = "https://atlas.thuenen.de/geoserver/ows"
EBENE = "geonode:Dominant_Species_Class"
HEADERS = {"User-Agent": "PilzkarteWolfsburg/1.0 (privates Lernprojekt)"}
DATEI = "klassen.csv"


def hole(parameter, timeout=90):
    try:
        antwort = requests.get(BASIS, params=parameter, headers=HEADERS,
                               timeout=timeout)
        if antwort.status_code != 200:
            return None, f"HTTP {antwort.status_code}"
        return antwort.text, None
    except Exception as e:
        return None, str(e)[:120]


def weg1_farbtabelle():
    """GetLegendGraphic als JSON - bei Rastern eine ColorMap."""
    text, fehler = hole({
        "service": "WMS", "version": "1.1.1",
        "request": "GetLegendGraphic", "layer": EBENE,
        "format": "application/json"})
    if fehler:
        return {}, fehler

    try:
        daten = json.loads(text)
    except Exception:
        return {}, "kein JSON"

    klassen = {}

    def durchsuchen(objekt):
        """Rekursiv nach Eintraegen mit quantity und label suchen."""
        if isinstance(objekt, dict):
            menge = objekt.get("quantity")
            name = objekt.get("label") or objekt.get("title")
            if menge is not None and name:
                try:
                    klassen[int(float(menge))] = str(name).strip()
                except (ValueError, TypeError):
                    pass
            for wert in objekt.values():
                durchsuchen(wert)
        elif isinstance(objekt, list):
            for wert in objekt:
                durchsuchen(wert)

    durchsuchen(daten)
    return klassen, None if klassen else "keine Farbtabelle gefunden"


def weg2_sld():
    """GetStyles liefert die Stildatei als XML."""
    text, fehler = hole({
        "service": "WMS", "version": "1.1.1",
        "request": "GetStyles", "layers": EBENE})
    if fehler:
        return {}, fehler

    treffer = re.findall(
        r'<(?:\w+:)?ColorMapEntry[^>]*?'
        r'(?=[^>]*quantity="([^"]+)")'
        r'(?=[^>]*label="([^"]+)")', text)
    klassen = {}
    for menge, name in treffer:
        try:
            klassen[int(float(menge))] = name.strip()
        except ValueError:
            pass

    if not klassen:
        # zweiter Anlauf mit umgekehrter Attributreihenfolge
        for m in re.finditer(r"<(?:\w+:)?ColorMapEntry([^>]*)>", text):
            attr = m.group(1)
            menge = re.search(r'quantity="([^"]+)"', attr)
            name = re.search(r'label="([^"]+)"', attr)
            if menge and name:
                try:
                    klassen[int(float(menge.group(1)))] = name.group(1).strip()
                except ValueError:
                    pass

    return klassen, None if klassen else "keine ColorMapEntry gefunden"


def weg3_beschreibung():
    """Die Ebenenbeschreibung enthaelt manchmal die Klassenliste."""
    text, fehler = hole({
        "service": "WMS", "version": "1.1.1",
        "request": "GetCapabilities"}, timeout=180)
    if fehler:
        return {}, fehler

    stelle = text.find(EBENE)
    if stelle < 0:
        return {}, "Ebene nicht in den Capabilities"

    ausschnitt = text[max(0, stelle - 3000):stelle + 4000]
    return {}, ausschnitt


def main():
    print(f"Ebene: {EBENE}\n")

    for name, funktion in [("Farbtabelle (GetLegendGraphic)", weg1_farbtabelle),
                           ("Stildatei (GetStyles)", weg2_sld)]:
        klassen, fehler = funktion()
        print(f"--- {name}")
        if klassen:
            print(f"    {len(klassen)} Klassen gefunden\n")
            for wert in sorted(klassen):
                print(f"      {wert:3d}  {klassen[wert]}")

            with open(DATEI, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["wert", "name"])
                for wert in sorted(klassen):
                    writer.writerow([wert, klassen[wert]])
            print(f"\nGespeichert in {DATEI}.")
            return
        print(f"    {fehler}")

    print("\n--- Rohausschnitt aus den Capabilities")
    _, ausschnitt = weg3_beschreibung()
    print(str(ausschnitt)[:2500])
    print("\nSchick mir diesen Ausschnitt, dann lese ich die Klassen daraus.")


main()