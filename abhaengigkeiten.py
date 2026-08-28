"""
Erzeugt eine Karte der Abhaengigkeiten zwischen den Skripten.

Wer importiert wen, wer liest und schreibt welche Datei, welche
Namen werden ueber Modulgrenzen hinweg benutzt.

Zweck: In ein neues Gespraech mitgeben, damit dort kein Code
entsteht, der nicht zum Bestehenden passt. Aus dem Code erzeugt,
also immer aktuell.

Ergebnis: ABHAENGIGKEITEN.md
"""
import os
import ast
import re

AUSGABE = "ABHAENGIGKEITEN.md"

EIGENE = {d[:-3] for d in os.listdir(".") if d.endswith(".py")}

# Skripte, die nur einmalig laufen oder Testzwecken dienen
NEBENSACHE = {"test_", "pruefe_", "reparatur_", "abhaengigkeiten",
              "namenspruefung", "finde_loch"}


def nebensache(name):
    return any(name.startswith(p) for p in NEBENSACHE)


def dateien_im_code(quelle):
    """Erwaehnte CSV-, JSON- und PNG-Dateien."""
    treffer = set(re.findall(
        r'["\']([\w./-]+\.(?:csv|json|txt|geojson|png|yml))["\']', quelle))
    return {t for t in treffer if not t.startswith("http")}


def analysiere(datei):
    quelle = open(datei, encoding="utf-8").read()
    try:
        baum = ast.parse(quelle)
    except SyntaxError:
        return None

    name = datei[:-3]
    importe = set()
    benutzt = set()

    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            for a in k.names:
                m = (a.asname or a.name).split(".")[0]
                if a.name in EIGENE:
                    importe.add(a.name)
        elif isinstance(k, ast.ImportFrom):
            if k.module in EIGENE:
                importe.add(k.module)
                for a in k.names:
                    benutzt.add(f"{k.module}.{a.name}")
        elif isinstance(k, ast.Attribute) and isinstance(k.value, ast.Name):
            if k.value.id in EIGENE:
                benutzt.add(f"{k.value.id}.{k.attr}")

    # Kurzbeschreibung aus dem Dateikopf
    doku = ast.get_docstring(baum) or ""
    zweck = doku.strip().split("\n")[0] if doku else ""

    # Konstanten in Grossbuchstaben
    konstanten = {}
    for k in baum.body:
        if isinstance(k, ast.Assign):
            for ziel in k.targets:
                if isinstance(ziel, ast.Name) and ziel.id.isupper():
                    try:
                        konstanten[ziel.id] = ast.literal_eval(k.value)
                    except Exception:
                        pass

    return {
        "name": name, "zweck": zweck, "importe": importe,
        "benutzt": benutzt, "dateien": dateien_im_code(quelle),
        "konstanten": konstanten,
        "zeilen": len(quelle.split("\n")),
    }


def main():
    alle = {}
    for datei in sorted(d for d in os.listdir(".") if d.endswith(".py")):
        e = analysiere(datei)
        if e:
            alle[e["name"]] = e

    zeilen = ["# Abhängigkeiten im Code", "",
              "Aus dem Code erzeugt mit `abhaengigkeiten.py`. "
              "Bei Änderungen neu erzeugen.", ""]

    # --- Wer importiert wen ---
    zeilen += ["## Wer benutzt wen", "",
               "| Skript | benutzt | wird benutzt von |",
               "|---|---|---|"]
    for name, e in sorted(alle.items()):
        if nebensache(name):
            continue
        nutzer = sorted(n for n, x in alle.items()
                        if name in x["importe"] and not nebensache(n))
        if not e["importe"] and not nutzer:
            continue
        zeilen.append(f"| `{name}.py` | "
                      f"{', '.join('`'+i+'`' for i in sorted(e['importe'])) or '—'} | "
                      f"{', '.join('`'+n+'`' for n in nutzer) or '—'} |")

    # --- Welche Namen ueber Modulgrenzen ---
    zeilen += ["", "## Namen, die über Dateigrenzen benutzt werden", "",
               "Ändert sich einer davon, bricht der Aufrufer.", ""]
    nach_modul = {}
    for e in alle.values():
        if nebensache(e["name"]):
            continue
        for eintrag in e["benutzt"]:
            modul, attribut = eintrag.split(".", 1)
            nach_modul.setdefault(modul, {}).setdefault(
                attribut, set()).add(e["name"])

    for modul in sorted(nach_modul):
        zeilen += [f"### `{modul}.py`", ""]
        for attribut in sorted(nach_modul[modul]):
            nutzer = sorted(nach_modul[modul][attribut])
            zeilen.append(f"- `{attribut}` — benutzt von "
                          f"{', '.join('`'+n+'`' for n in nutzer)}")
        zeilen.append("")

    # --- Dateien ---
    zeilen += ["## Datendateien", "",
               "| Datei | erwähnt in |", "|---|---|"]
    nach_datei = {}
    for e in alle.values():
        for d in e["dateien"]:
            nach_datei.setdefault(d, set()).add(e["name"])
    for d in sorted(nach_datei):
        nutzer = sorted(nach_datei[d])
        if len(nutzer) > 6:
            nutzer = nutzer[:6] + [f"… und {len(nach_datei[d])-6} weitere"]
        zeilen.append(f"| `{d}` | "
                      f"{', '.join('`'+n+'`' for n in nutzer)} |")

    # --- Konstanten, die mehrfach vorkommen ---
    zeilen += ["", "## Konstanten, die an mehreren Stellen stehen", "",
               "Bei Änderungen überall nachziehen.", "",
               "| Name | Wert | steht in |", "|---|---|---|"]
    nach_konstante = {}
    for e in alle.values():
        for k, v in e["konstanten"].items():
            nach_konstante.setdefault(k, []).append((e["name"], v))
    for k in sorted(nach_konstante):
        eintraege = nach_konstante[k]
        if len(eintraege) < 2:
            continue
        werte = {repr(v)[:40] for _, v in eintraege}
        wert = list(werte)[0] if len(werte) == 1 else "**verschieden!**"
        wo = ", ".join(f"`{n}`" for n, _ in sorted(eintraege)[:6])
        if len(eintraege) > 6:
            wo += f" … {len(eintraege)-6} weitere"
        zeilen.append(f"| `{k}` | {wert} | {wo} |")

    # --- Reihenfolge ---
    zeilen += ["", "## Reihenfolge beim Neurechnen", "", "```",
               "# Daten beschaffen",
               "python nachfuellen.py      # Wetter, setzt fort",
               "python baumarten.py        # Thünen-Kacheln",
               "python bodendaten.py       # SoilGrids",
               "python hoehen.py           # Open-Meteo",
               "python ortsnamen.py        # Overpass",
               "",
               "# Rechnen und ausgeben",
               "python karte.py            # örtliche HTML-Karten",
               "python daten_export.py     # web/daten.json",
               "python web_bilder.py       # die weichen Bilder",
               "```", "",
               "`daten_export.py` importiert `karte.py` und benutzt "
               "dessen Ladefunktionen — beide müssen zusammenpassen.",
               ""]

    with open(AUSGABE, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen))

    print(f"{len(alle)} Dateien untersucht")
    print(f"{AUSGABE} geschrieben ({len(zeilen)} Zeilen)")


main()
