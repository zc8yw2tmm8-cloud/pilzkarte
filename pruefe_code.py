"""
Prueft den Code auf Fallen, die erst spaeter auffallen.

Fuenf Dinge, die schon einmal Aerger gemacht haben:

1. Fehlende Namen - eine Funktion beim Umbauen verloren. Faellt sonst
   erst mitten in einem langen Lauf auf.
2. Module ohne Startschutz - wer sie importiert, loest ungewollt einen
   ganzen Rechenlauf aus.
3. Auseinanderlaufende Einstellungen - karte.py und daten_export.py
   muessen dasselbe rechnen, sonst zeigen oertliche und Web-Karte
   verschiedene Zahlen.
4. Dateinamen mit Leerzeichen - entstehen beim Herunterladen und
   brechen Importe.
5. Ungeschuetzte Divisionen durch leere Listen.

Nach jeder groesseren Aenderung laufen lassen. Dauert Sekunden.
"""
import ast
import os
import re
import builtins

EIGENE_MODULE = ["karte", "infoseite", "weichzeichnen", "waldebenen",
                 "kennwerte", "arten", "farben", "historie", "gebiete",
                 "konfig"]

probleme = []


def melde(datei, text):
    probleme.append((datei, text))


def pruefe_namen(datei, quelle, baum):
    bekannt = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    for k in ast.walk(baum):
        if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            bekannt.add(k.name)
        elif isinstance(k, ast.Name) and isinstance(k.ctx, ast.Store):
            bekannt.add(k.id)
        elif isinstance(k, ast.arg):
            bekannt.add(k.arg)
        elif isinstance(k, ast.Import):
            for a in k.names:
                bekannt.add((a.asname or a.name).split(".")[0])
        elif isinstance(k, ast.ImportFrom):
            for a in k.names:
                bekannt.add(a.asname or a.name)
        elif isinstance(k, ast.ExceptHandler) and k.name:
            bekannt.add(k.name)

    for k in ast.walk(baum):
        if isinstance(k, ast.Name) and isinstance(k.ctx, ast.Load):
            if k.id not in bekannt:
                melde(datei, f"Name nicht definiert: {k.id}")


def pruefe_startschutz(datei, quelle):
    name = datei[:-3]
    if name not in EIGENE_MODULE:
        return
    if re.search(r"^main\(\)\s*$", quelle, re.M):
        melde(datei, "wird importiert, ruft aber main() beim Laden auf - "
                     'braucht: if __name__ == "__main__":')


def pruefe_divisionen(datei, quelle):
    """
    Division durch len() ohne Schutz.

    Sucht bis zum Anfang der umgebenden Funktion nach einer
    Absicherung - eine Pruefung 30 Zeilen weiter oben zaehlt genauso.
    """
    zeilen = quelle.split("\n")

    for i, zeile in enumerate(zeilen, 1):
        treffer = re.search(r"/ *len\((\w+)\)", zeile)
        if not treffer:
            continue
        if "max(" in zeile or " if " in zeile:
            continue

        name = treffer.group(1)

        # Rueckwaerts bis zum Funktionsanfang suchen
        geschuetzt = False
        for j in range(i - 2, max(0, i - 60), -1):
            z = zeilen[j]
            if re.match(r"^(def |class )", z):
                break
            if re.search(rf"if not {name}\b|if len\({name}\)|"
                         rf"if {name}:|if not \w+ or |{name} = \[\]",
                         z):
                geschuetzt = True
                break

        if not geschuetzt:
            melde(datei, f"Zeile {i}: {zeile.strip()[:50]}")


def pruefe_dateinamen():
    for d in os.listdir("."):
        if not d.endswith(".py"):
            continue
        if " " in d:
            melde(d, "Leerzeichen im Namen - Importe schlagen fehl. "
                     "Umbenennen mit Unterstrich.")
        if d != d.lower():
            melde(d, "Grossbuchstaben im Namen - beim Herunterladen "
                     "entstanden, umbenennen")


def pruefe_gleichlauf():
    """karte.py und daten_export.py muessen dasselbe rechnen."""
    if not (os.path.exists("karte.py")
            and os.path.exists("daten_export.py")):
        return

    k = open("karte.py", encoding="utf-8").read()
    d = open("daten_export.py", encoding="utf-8").read()

    for name in ["ZIELTAGE", "RASTER_KM", "FENSTER"]:
        eigen = re.search(rf"^{name} = ", d, re.M)
        if eigen and f"k.{name}" not in d:
            melde("daten_export.py",
                  f"{name} eigenstaendig gesetzt statt aus karte.py - "
                  f"die beiden Karten koennen auseinanderlaufen")

    if "farben" in k and "weichzeichnen" in d:
        pass


def main():
    print("Pruefe den Code auf spaetere Fallen\n")

    pruefe_dateinamen()
    pruefe_gleichlauf()

    for datei in sorted(x for x in os.listdir(".") if x.endswith(".py")):
        try:
            quelle = open(datei, encoding="utf-8").read()
            baum = ast.parse(quelle)
        except SyntaxError as e:
            melde(datei, f"SYNTAXFEHLER Zeile {e.lineno}: {e.msg}")
            continue
        except Exception as e:
            melde(datei, f"nicht lesbar: {e}")
            continue

        pruefe_namen(datei, quelle, baum)
        pruefe_startschutz(datei, quelle)
        pruefe_divisionen(datei, quelle)

    if not probleme:
        print("Nichts gefunden.")
        return

    letzte = None
    for datei, text in probleme:
        if datei != letzte:
            print(f"\n{datei}")
            letzte = datei
        print(f"   {text}")

    print(f"\n{len(probleme)} Auffaelligkeiten.")
    print("Nicht jede ist ein Fehler - aber jede ist einen Blick wert.")


main()