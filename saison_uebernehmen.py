"""
Traegt die kalibrierten Saisonfaktoren aus kalibrierung.txt in arten.py ein.

Sicherheitshalber wird vorher eine Kopie als arten_vorher.py abgelegt.
Vor dem Schreiben zeigt das Skript alle Aenderungen und fragt nach.

Ablauf:
    python funde_arten.py
    python kalibrieren.py
    python saison_uebernehmen.py
"""
import os
import re
import shutil

BERICHT = "kalibrierung.txt"
ZIEL = "arten.py"
KOPIE = "arten_vorher.py"

MONATE = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
          "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def lies_bericht():
    """Sucht je Art die Zeile mit den Saisonfaktoren."""
    if not os.path.exists(BERICHT):
        return {}

    with open(BERICHT, "r", encoding="utf-8") as f:
        zeilen = f.read().replace("\r", "").split("\n")

    gefunden = {}
    art = None
    for zeile in zeilen:
        treffer = re.search(r"Saisonfaktor\s+(\w+)", zeile)
        if treffer:
            art = treffer.group(1).lower()
            continue
        if art and zeile.strip().startswith('"saison":'):
            gefunden[art] = zeile.strip().rstrip(",")
            art = None
    return gefunden


def zerlege(zeile):
    """Aus der Textzeile ein dict {monat: wert} machen."""
    werte = {}
    for m, w in re.findall(r"(\d+):\s*([\d.]+)", zeile):
        werte[int(m)] = float(w)
    return werte


def alte_werte(quelltext, art):
    start = quelltext.find(f'    "{art}": {{')
    if start < 0:
        return None, None, None
    stelle = quelltext.find('"saison": {', start)
    if stelle < 0:
        return None, None, None
    ende = quelltext.find("},", stelle)
    if ende < 0:
        return None, None, None
    ende += 2
    return stelle, ende, zerlege(quelltext[stelle:ende])


def balken(werte):
    zeichen = []
    for m in range(1, 13):
        w = werte.get(m, 0.0)
        zeichen.append("#" if w >= 0.7 else "+" if w >= 0.35
                       else "." if w > 0.05 else " ")
    return "".join(zeichen)


def main():
    neu = lies_bericht()
    if not neu:
        print(f"Keine Saisonfaktoren in {BERICHT} gefunden.")
        print("Erst funde_arten.py und kalibrieren.py laufen lassen.")
        return

    with open(ZIEL, "r", encoding="utf-8") as f:
        quelltext = f.read()

    print(f"{len(neu)} Arten im Bericht\n")
    print("        " + "".join(f"{m[0]}" for m in MONATE)
          + "   Hoehepunkt")

    aenderungen = []
    for art, zeile in neu.items():
        stelle, ende, alt = alte_werte(quelltext, art)
        if stelle is None:
            print(f"  {art}: in {ZIEL} nicht gefunden - uebersprungen")
            continue

        werte = zerlege(zeile)
        if not werte:
            continue

        hoch_alt = max(alt, key=alt.get) if alt else 0
        hoch_neu = max(werte, key=werte.get)

        print(f"\n  {art}")
        print(f"    alt {balken(alt)}   {MONATE[hoch_alt - 1]}")
        print(f"    neu {balken(werte)}   {MONATE[hoch_neu - 1]}")

        if hoch_alt != hoch_neu:
            print(f"    -> Hoehepunkt verschiebt sich von "
                  f"{MONATE[hoch_alt-1]} nach {MONATE[hoch_neu-1]}")

        aenderungen.append((art, stelle, ende, zeile))

    if not aenderungen:
        print("\nNichts zu aendern.")
        return

    print("\n" + "=" * 58)
    print("Pruefe die Hoehepunkte:")
    print("  Steinpilz, Marone, Birkenpilz, Parasol -> Sep oder Okt")
    print("  Sommersteinpilz -> Jun oder Jul")
    print("  Pfifferling -> Jul bis Sep")
    print("  Schwefelporling -> Mai oder Jun")
    print()
    antwort = input("Uebernehmen? (j/n) ").strip().lower()
    if not antwort.startswith("j"):
        print("Abgebrochen, nichts geaendert.")
        return

    shutil.copy(ZIEL, KOPIE)

    # Von hinten nach vorn ersetzen, damit die Stellen gueltig bleiben
    for art, stelle, ende, zeile in sorted(aenderungen, key=lambda x: -x[1]):
        quelltext = quelltext[:stelle] + zeile + "," + quelltext[ende:]

    with open(ZIEL, "w", encoding="utf-8") as f:
        f.write(quelltext)

    try:
        import ast
        ast.parse(quelltext)
        print(f"\n{len(aenderungen)} Arten aktualisiert. "
              f"Kopie liegt in {KOPIE}.")
        print("Weiter mit: python karte.py")
    except SyntaxError as e:
        shutil.copy(KOPIE, ZIEL)
        print(f"\nFehler im Ergebnis ({e}) - Aenderung zurueckgenommen.")


main()