"""
Entfernt Git-Konfliktmarkierungen aus den Datendateien.

Beim Verschmelzen zweier Staende schreibt Git Zeilen wie

    <<<<<<< HEAD
    ...eine Fassung...
    =======
    ...die andere...
    >>>>>>> 8948129 (Beschreibung)

mitten in die Datei. In einer CSV sind das kaputte Zeilen - sie
tauchen als Datum oder Ortsname auf und verderben jede Auswertung.

Dieses Skript sucht sie in allen CSV-Dateien, zeigt sie, und
entfernt sie nach Rueckfrage. Von jeder geaenderten Datei wird
vorher eine Kopie mit der Endung .vor_reparatur angelegt.
"""
import os
import glob
import shutil

MARKEN = ("<<<<<<<", "=======", ">>>>>>>", "|||||||")

ORDNER = [".", "wetter_historie"]


def dateien():
    gefunden = []
    for o in ORDNER:
        if os.path.isdir(o):
            gefunden += sorted(glob.glob(os.path.join(o, "*.csv")))
    return gefunden


def pruefe(pfad):
    """Rueckgabe: (alle Zeilen, Zeilennummern mit Marken)"""
    with open(pfad, "r", encoding="utf-8", errors="replace") as f:
        zeilen = f.readlines()

    treffer = []
    for i, z in enumerate(zeilen):
        gestutzt = z.lstrip()
        if any(gestutzt.startswith(m) for m in MARKEN):
            treffer.append(i)
    return zeilen, treffer


def main():
    print("Suche Git-Konfliktmarkierungen in den Datendateien\n")

    betroffen = []
    for pfad in dateien():
        zeilen, treffer = pruefe(pfad)
        if treffer:
            betroffen.append((pfad, zeilen, treffer))
            print(f"{pfad}: {len(treffer)} Markierungen")
            for i in treffer[:4]:
                print(f"   Zeile {i+1}: {zeilen[i].strip()[:60]}")
            if len(treffer) > 4:
                print(f"   ... und {len(treffer)-4} weitere")
            print()

    if not betroffen:
        print("Keine gefunden - die Datendateien sind sauber.")
        return

    gesamt = sum(len(t) for _, _, t in betroffen)
    print("=" * 58)
    print(f"{gesamt} kaputte Zeilen in {len(betroffen)} Dateien.")
    print("Sie werden entfernt, der Rest bleibt unveraendert.")
    print()

    if input("Reparieren? (j/n) ").strip().lower()[:1] != "j":
        print("Abgebrochen.")
        return

    for pfad, zeilen, treffer in betroffen:
        shutil.copy(pfad, pfad + ".vor_reparatur")
        weg = set(treffer)
        with open(pfad, "w", encoding="utf-8") as f:
            for i, z in enumerate(zeilen):
                if i not in weg:
                    f.write(z)
        print(f"  {pfad}: {len(treffer)} Zeilen entfernt")

    print(f"\nFertig. Kopien liegen mit der Endung .vor_reparatur daneben.")
    print("\nWeiter mit:")
    print("  python karte.py")
    print("  python daten_export.py")
    print("  python web_bilder.py")


main()