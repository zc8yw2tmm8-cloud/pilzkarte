"""
Wird von der Windows-Aufgabenplanung aufgerufen.
Holt den Vortag und die neue Prognose.
"""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
python = sys.executable

for skript in ["sammeln.py", "prognose.py"]:
    print(f"\n=== starte {skript} ===")
    ergebnis = subprocess.run([python, skript])
    if ergebnis.returncode != 0:
        print(f"{skript} endete mit Fehler {ergebnis.returncode}")
