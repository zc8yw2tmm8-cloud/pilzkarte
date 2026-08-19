"""
Traegt die gemessenen Baumartengewichte in arten.py ein.

baumarten_kalibrieren.py schreibt sie nach baumarten_gewichte.txt.
Von Hand zu uebertragen ist fehleranfaellig - hier passiert es
geprueft, mit Kopie und Syntaxpruefung.

Arten, fuer die keine Messung vorliegt, bleiben unveraendert. Ihre
Werte stammen dann weiter aus der Literatur, was herkunft.py
anzeigt.
"""
import os
import re
import ast
import shutil

QUELLE = "baumarten_gewichte.txt"
ZIEL = "arten.py"
KOPIE = "arten_vor_baumarten.py"


def lies_gewichte():
    """Aus der Ausgabedatei je Art das Gewichtswoerterbuch lesen."""
    if not os.path.exists(QUELLE):
        return {}

    text = open(QUELLE, "r", encoding="utf-8").read()
    ergebnis = {}

    # Aufbau: "# artname" gefolgt von der baumarten-Zeile
    for m in re.finditer(r"^# (\w+)\s*\n\s*(\"baumarten\": \{[^}]*\}),",
                         text, re.M):
        art = m.group(1)
        zeile = m.group(2)
        try:
            werte = ast.literal_eval("{" + zeile + "}")["baumarten"]
        except (ValueError, SyntaxError, KeyError):
            continue
        ergebnis[art] = werte
    return ergebnis


def main():
    gewichte = lies_gewichte()
    if not gewichte:
        print(f"{QUELLE} fehlt oder ist leer.")
        print("Erst baumarten_kalibrieren.py laufen lassen.")
        return

    import arten
    quelle = open(ZIEL, "r", encoding="utf-8").read()

    print(f"{len(gewichte)} Arten in {QUELLE}\n")
    print(f"{'Art':<24}{'Baumart':<14}{'alt':>7}{'neu':>7}")
    print("-" * 52)

    aenderungen = []
    for art, neu in sorted(gewichte.items()):
        e = arten.ARTEN.get(art)
        if not e:
            print(f"{art}: in arten.py unbekannt")
            continue

        alt = e.get("baumarten") or {}
        unterschiede = sorted(
            ((abs(neu.get(b, 0) - alt.get(b, 0)), b) for b in neu),
            reverse=True)[:4]

        unveraendert = [b for b in alt if b not in neu]

        print(f"\n{e['name']}  ({len(neu)} gemessen, "
              f"{len(unveraendert)} unveraendert)")
        for d, b in unterschiede:
            print(f"{'':<24}{b:<14}{alt.get(b, 0):>7.2f}"
                  f"{neu.get(b, 0):>7.2f}")
        if unveraendert:
            print(f"{'':<24}behalten: {', '.join(unveraendert)}")

        aenderungen.append((art, neu))

    if not aenderungen:
        print("\nNichts zu aendern.")
        return

    print(f"\n{len(aenderungen)} Arten werden geaendert.")
    print("Die uebrigen behalten ihre Literaturwerte.")
    print(f"Kopie in {KOPIE}.\n")

    if input("Uebernehmen? (j/n) ").strip().lower()[:1] != "j":
        print("Abgebrochen.")
        return

    shutil.copy(ZIEL, KOPIE)

    for art, neu in aenderungen:
        start = quelle.index(f'    "{art}": {{')
        ende = quelle.index("\n    },", start)
        block = quelle[start:ende]

        # Alte Werte behalten, wo nicht neu gemessen wurde.
        # Sonst faellt ein gut gestuetzter Wert weg, nur weil in
        # diesem Lauf zu wenige Fundorte zusammenkamen.
        alt_werte = dict(arten.ARTEN[art].get("baumarten") or {})
        zusammen = alt_werte
        zusammen.update(neu)

        eintraege = ", ".join(
            f'"{b}": {w}' for b, w in
            sorted(zusammen.items(), key=lambda x: -x[1]))
        zeile = f'        "baumarten": {{{eintraege}}},'

        muster = re.compile(r'^        "baumarten": \{[^}]*\},$', re.M)
        neuer, n = muster.subn(zeile, block, count=1)
        if n:
            quelle = quelle[:start] + neuer + quelle[ende:]
        else:
            print(f"  {art}: baumarten-Zeile nicht gefunden")

    open(ZIEL, "w", encoding="utf-8").write(quelle)

    try:
        ast.parse(quelle)
        print(f"\n{ZIEL} geschrieben, Syntax in Ordnung.")
    except SyntaxError as e:
        print(f"\nSYNTAXFEHLER Zeile {e.lineno}: {e.msg}")
        print(f"{KOPIE} zurueckkopieren!")
        return

    print("\nWeiter mit:")
    print("  python herkunft.py        (was ist jetzt gemessen?)")
    print("  python monatsnormale.py   (Normale neu rechnen)")
    print("  python karte.py")
    print("  python daten_export.py")
    print("  python web_bilder.py")


main()