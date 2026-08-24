"""
Nimmt grosse Zwischendaten und Notizen aus der Git-Verfolgung.

Eine Regel in .gitignore wirkt nicht rueckwirkend: Was einmal
eingecheckt wurde, bleibt drin. Im Repository liegen deshalb
weiterhin die Thuenen-Kacheln (rund 72 MB), das Hoehenmodell und
hintergrund.csv - obwohl alle drei laengst in .gitignore stehen.

Jeder Cloud-Lauf laedt das mit herunter.

Dieses Skript zeigt erst, was betroffen ist, und fragt dann. Die
Dateien bleiben auf der Platte - sie werden nur nicht mehr
mitgefuehrt.
"""
import os
import subprocess

# Was aus der Verfolgung soll, mit Begruendung
RAUS = [
    ("kacheln", "Thuenen-Kacheln, werden von baumarten.py geholt"),
    ("dgm", "Hoehendaten, werden von dgm_holen.py geholt"),
    ("__pycache__", "von Python erzeugt"),
    ("hintergrund.csv", "96.000 Zeilen, von hintergrund.py erzeugt"),
    ("arten_vorher.py", "Sicherungskopie"),
    ("arten_vor_baumarten.py", "Sicherungskopie"),
    ("waldpunkte_vor_kennungen.csv", "Sicherungskopie"),
    ("waldpunkte_vor_luecken.csv", "Sicherungskopie"),
    ("waldpunkte_vorher.csv", "Sicherungskopie"),
    ("funde_arten_nur_gbif.csv", "Zwischenstand"),
    ("relief_grenzen.txt", "durch relief_grenzen.csv ersetzt"),
    (".vscode", "Editoreinstellungen"),
    ("CLAUDE.md", "Notizen fuer die Zusammenarbeit, bleiben lokal"),
    ("ABHAENGIGKEITEN.md", "wird erzeugt, bleibt lokal"),
    ("UEBERGABE.md", "Notizen, bleiben lokal"),
]

# Zeilen, die in .gitignore ergaenzt werden
ERGAENZEN = [
    "",
    "# Notizen fuer die Zusammenarbeit - bleiben lokal",
    "CLAUDE.md",
    "ABHAENGIGKEITEN.md",
    "UEBERGABE.md",
    "",
    "# Weitere Sicherungskopien",
    "arten_vor_baumarten.py",
    "waldpunkte_vor_*.csv",
    "waldpunkte_vorher.csv",
    "",
    "# Editoreinstellungen",
    ".vscode/",
]


def wird_verfolgt(pfad):
    e = subprocess.run(["git", "ls-files", "--error-unmatch", pfad],
                       capture_output=True, text=True)
    return e.returncode == 0


def groesse(pfad):
    if os.path.isfile(pfad):
        return os.path.getsize(pfad)
    gesamt = 0
    for wurzel, _, dateien in os.walk(pfad):
        for d in dateien:
            try:
                gesamt += os.path.getsize(os.path.join(wurzel, d))
            except OSError:
                pass
    return gesamt


def main():
    if not os.path.isdir(".git"):
        print("Kein Git-Ordner - im Projektordner ausfuehren.")
        return

    betroffen = []
    for pfad, grund in RAUS:
        if not os.path.exists(pfad):
            continue
        # Bei Ordnern zaehlt, ob irgendetwas darin verfolgt wird
        e = subprocess.run(["git", "ls-files", pfad],
                           capture_output=True, text=True)
        if not e.stdout.strip():
            continue
        anzahl = len(e.stdout.strip().split("\n"))
        betroffen.append((pfad, grund, anzahl, groesse(pfad)))

    if not betroffen:
        print("Nichts zu tun - alles schon sauber.")
    else:
        print("Diese Dateien werden mitgefuehrt, obwohl sie es nicht")
        print("sollten:\n")
        print(f"{'Pfad':<32}{'Dateien':>9}{'Groesse':>11}")
        gesamt = 0
        for pfad, grund, anzahl, gr in betroffen:
            gesamt += gr
            print(f"{pfad:<32}{anzahl:>9}{gr/1024/1024:>9.1f} MB")
            print(f"   {grund}")
        print(f"\nZusammen {gesamt/1024/1024:.1f} MB.")
        print("\nDie Dateien bleiben auf der Platte. Sie werden nur")
        print("nicht mehr ins Repository geladen.")
        print("\nHinweis: In der Versionsgeschichte bleiben sie")
        print("erhalten - das Repository wird also nicht kleiner,")
        print("aber neue Laeufe werden schneller.")

        print()
        if input("Aus der Verfolgung nehmen? (j/n) "
                 ).strip().lower()[:1] != "j":
            print("Abgebrochen.")
            return

        for pfad, _, _, _ in betroffen:
            befehl = ["git", "rm", "-r", "--cached", "--quiet", pfad]
            e = subprocess.run(befehl, capture_output=True, text=True)
            if e.returncode == 0:
                print(f"  {pfad}")
            else:
                print(f"  {pfad}: {e.stderr.strip()[:60]}")

    # .gitignore ergaenzen
    vorhanden = ""
    if os.path.exists(".gitignore"):
        vorhanden = open(".gitignore", "r", encoding="utf-8").read()

    neu = [z for z in ERGAENZEN
           if not z or z.startswith("#") or z not in vorhanden]
    # Nur ergaenzen, wenn wirklich etwas Neues dabei ist
    echte = [z for z in neu if z and not z.startswith("#")]

    if echte:
        with open(".gitignore", "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(neu) + "\n")
        print(f"\n{len(echte)} Zeilen in .gitignore ergaenzt.")

    print("\nWeiter mit:")
    print('  git commit -m "Zwischendaten und Notizen lokal halten"')
    print("  git push")


main()