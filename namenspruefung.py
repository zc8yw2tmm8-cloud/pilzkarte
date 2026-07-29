"""
Prueft, ob jedes benutzte Modul-eigene Symbol auch definiert ist.

ast.parse findet nur Syntaxfehler. Wenn beim Umbauen eine Funktion
verlorengeht, faellt das erst zur Laufzeit auf - moeglicherweise
mitten in einem langen Lauf.
"""
import ast
import os
import builtins

EIGENE = {d[:-3] for d in os.listdir(".") if d.endswith(".py")}


def pruefe(datei):
    quelle = open(datei, encoding="utf-8").read()
    baum = ast.parse(quelle)

    bekannt = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    for k in ast.walk(baum):
        if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
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
        elif isinstance(k, (ast.comprehension,)):
            pass

    fehlend = set()
    for k in ast.walk(baum):
        if isinstance(k, ast.Name) and isinstance(k.ctx, ast.Load):
            if k.id not in bekannt:
                fehlend.add(k.id)
    return sorted(fehlend)


def main():
    print("Pruefe, ob alle benutzten Namen definiert sind\n")
    probleme = 0
    for datei in sorted(d for d in os.listdir(".") if d.endswith(".py")):
        try:
            fehlend = pruefe(datei)
        except SyntaxError as e:
            print(f"{datei}: SYNTAXFEHLER Zeile {e.lineno}")
            probleme += 1
            continue
        if fehlend:
            print(f"{datei}: nicht definiert - {', '.join(fehlend)}")
            probleme += 1

    if probleme:
        print(f"\n{probleme} Dateien mit Auffaelligkeiten.")
        print("Namen aus anderen Modulen sind normal, wenn sie mit")
        print("Modulpraefix benutzt werden. Alles andere pruefen.")
    else:
        print("Alles in Ordnung.")


main()
