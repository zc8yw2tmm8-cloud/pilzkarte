"""
Prueft, ob die Begleitdaten wirklich zu dem Ort gehoeren, an dem sie
stehen. Aendert nichts - schreibt nur einen Bericht.

Warum das noetig ist: Boden, Hoehen, Baumarten und Wetter werden
ueber die Kennung verknuepft, nie ueber die Koordinate. Stimmt die
Kennung, wird der Wert genommen - auch wenn er in Wahrheit 100 km
entfernt gemessen wurde. Und weil bodendaten.py und hoehen.py
vorhandene Kennungen als erledigt betrachten, holt ein erneuter Lauf
solche Zeilen nicht neu.

Ausgabe:
  - eine Zusammenfassung im Terminal
  - ortspruefung.csv mit jeder auffaelligen Zeile

Die zehn Meter Toleranz sind eine Rundungsgrenze fuer dieses Raster,
keine fachliche Aussage darueber, wie weit ein Messwert tragen darf.
"""
import os
import csv
import math
import glob

PUNKTE = "waldpunkte.csv"
BERICHT = "ortspruefung.csv"
TOLERANZ_M = 10

# Begleitdateien mit eigenen Koordinatenspalten
BEGLEITER = ["bodendaten.csv", "hoehen.csv", "baumarten.csv"]

# Wetterdateien: Monatsdateien plus die Vorhersage
def wetterdateien():
    dateien = sorted(glob.glob(os.path.join("wetter_historie", "*.csv")))
    # Sicherungskopien (.vor_reparatur usw.) gehoeren nicht dazu
    dateien = [d for d in dateien if d.endswith(".csv")]
    if os.path.exists("wetter_prognose.csv"):
        dateien.append("wetter_prognose.csv")
    return dateien


def abstand(a, b):
    """Meter zwischen zwei (lat, lon)-Paaren, fuer kurze Strecken."""
    mlat = (a[0] + b[0]) / 2
    dx = (a[1] - b[1]) * 111320 * math.cos(math.radians(mlat))
    dy = (a[0] - b[0]) * 111320
    return math.hypot(dx, dy)


def lade_punkte():
    with open(PUNKTE, "r", encoding="utf-8") as f:
        return {z["id"]: (float(z["lat"]), float(z["lon"]))
                for z in csv.DictReader(f)}


def zielkennung(pos, aktiv):
    """Welche aktive Kennung liegt an der gespeicherten Position?

    Gibt (kennung, abstand) zurueck oder (None, None). Bei mehreren
    Treffern None - im Raster gibt es doppelt belegte Positionen, und
    Naehe allein ist dann keine eindeutige Zuordnung.
    """
    treffer = [(k, abstand(pos, p)) for k, p in aktiv.items()
               if abstand(pos, p) <= TOLERANZ_M]
    if len(treffer) == 1:
        return treffer[0]
    return None, None


def spalten_von(zeilen):
    """Welche Spalte traegt die Kennung, gibt es ein Datum?"""
    spalten = zeilen[0].keys()
    kennung = "id" if "id" in spalten else "ort"
    datum = "datum" if "datum" in spalten else None
    hat_ort = "lat" in spalten and "lon" in spalten
    return kennung, datum, hat_ort


def pruefe_datei(pfad, aktiv):
    """Liest eine Datei und sammelt die falsch verorteten Zeilen."""
    with open(pfad, "r", encoding="utf-8") as f:
        zeilen = list(csv.DictReader(f))

    if not zeilen:
        return [], {"zeilen": 0, "fehlende_aktive": [],
                    "ausgeschiedene": [], "hat_ort": False}

    kennungsspalte, datumsspalte, hat_ort = spalten_von(zeilen)

    befunde = []
    gesehen = set()
    ausgeschieden = set()

    for nr, z in enumerate(zeilen, start=2):      # Zeile 1 ist der Kopf
        kennung = z.get(kennungsspalte, "")
        gesehen.add(kennung)

        if kennung not in aktiv:
            ausgeschieden.add(kennung)
            continue
        if not hat_ort or not z.get("lat") or not z.get("lon"):
            continue

        gespeichert = (float(z["lat"]), float(z["lon"]))
        d = abstand(gespeichert, aktiv[kennung])
        if d <= TOLERANZ_M:
            continue

        ziel, _ = zielkennung(gespeichert, aktiv)
        befunde.append({
            "datei": pfad.replace(os.sep, "/"),
            "zeile": nr,
            "kennung": kennung,
            "datum": z.get(datumsspalte, "") if datumsspalte else "",
            "gespeichert_lat": z["lat"],
            "gespeichert_lon": z["lon"],
            "soll_lat": f"{aktiv[kennung][0]:.5f}",
            "soll_lon": f"{aktiv[kennung][1]:.5f}",
            "abstand_km": f"{d/1000:.1f}",
            "passt_zu": ziel or "",
            "einordnung": "",          # wird spaeter gefuellt
        })

    return befunde, {
        "zeilen": len(zeilen),
        "fehlende_aktive": sorted(set(aktiv) - gesehen),
        "ausgeschiedene": sorted(ausgeschieden),
        "hat_ort": hat_ort,
    }


def einordnen(befunde, aktiv):
    """Sagt je Befund, was mit der Zeile ueberhaupt moeglich waere.

    Das ist die eigentliche Entscheidungshilfe. Eine falsche Kopie
    neben einem vorhandenen Original kann ausgesondert werden. Wo das
    Original fehlt, waere eine Umbenennung denkbar - aber nur nach
    Sichtpruefung, nie automatisch.
    """
    for datei in sorted({b["datei"] for b in befunde}):
        with open(datei, "r", encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        kennungsspalte, datumsspalte, hat_ort = spalten_von(zeilen)

        # Welche Kennungen haben hier schon eine richtig verortete Zeile?
        korrekt = set()
        paare = set()
        for z in zeilen:
            k = z.get(kennungsspalte, "")
            if datumsspalte:
                paare.add((z.get(datumsspalte, ""), k))
            if k in aktiv and z.get("lat") and z.get("lon"):
                p = (float(z["lat"]), float(z["lon"]))
                if abstand(p, aktiv[k]) <= TOLERANZ_M:
                    korrekt.add(k)

        for b in befunde:
            if b["datei"] != datei:
                continue
            ziel = b["passt_zu"]
            if not ziel:
                b["einordnung"] = "kein eindeutiges Ziel"
            elif datumsspalte:
                # Wetter: je Tag eine Zeile. Gibt es die Zielzeile schon?
                if (b["datum"], ziel) in paare:
                    b["einordnung"] = "Dublette, Zielzeile existiert"
                else:
                    b["einordnung"] = "Ziel hat fuer diesen Tag nichts"
            elif ziel in korrekt:
                b["einordnung"] = "falsche Kopie, Original vorhanden"
            else:
                b["einordnung"] = "Ziel hat noch keine richtige Zeile"


def zeile(text=""):
    print(text, flush=True)


def main():
    if not os.path.exists(PUNKTE):
        zeile(f"{PUNKTE} fehlt - im Projektordner ausfuehren.")
        return

    aktiv = lade_punkte()
    zeile(f"Ortspruefung gegen {len(aktiv)} aktive Punkte, "
          f"Toleranz {TOLERANZ_M} m\n")

    alle = []

    # --- Begleitdateien -------------------------------------------------
    zeile(f"{'Datei':<22}{'Zeilen':>8}{'fehlend':>9}"
          f"{'ausgesch.':>11}{'falsch verortet':>17}")
    zeile("-" * 67)

    for pfad in BEGLEITER + [p for p in ["ortsnamen.csv"]
                             if os.path.exists(p)]:
        if not os.path.exists(pfad):
            continue
        befunde, z = pruefe_datei(pfad, aktiv)
        alle += befunde
        hinweis = "" if z["hat_ort"] else "  (ohne Koordinaten)"
        zeile(f"{pfad:<22}{z['zeilen']:>8}"
              f"{len(z['fehlende_aktive']):>9}"
              f"{len(z['ausgeschiedene']):>11}"
              f"{len(befunde):>17}{hinweis}")

    # --- Wetter ---------------------------------------------------------
    zeile()
    zeile(f"{'Wetterdatei':<34}{'Zeilen':>9}{'falsch verortet':>17}")
    zeile("-" * 60)
    for pfad in wetterdateien():
        befunde, z = pruefe_datei(pfad, aktiv)
        alle += befunde
        zeile(f"{pfad.replace(os.sep, '/'):<34}{z['zeilen']:>9}"
              f"{len(befunde):>17}")

    # --- Einordnung und Bericht ----------------------------------------
    if not alle:
        zeile("\nKeine falsch verorteten Zeilen gefunden.")
        return

    einordnen(alle, aktiv)

    zeile()
    zeile("Was mit den falsch verorteten Zeilen ist:")
    gruppen = {}
    for b in alle:
        gruppen.setdefault(b["einordnung"], []).append(b)
    for name in sorted(gruppen):
        betroffen = sorted({b["kennung"] for b in gruppen[name]})
        zeile(f"  {len(gruppen[name]):>6} Zeilen, "
              f"{len(betroffen):>4} Kennungen  -  {name}")

    weiteste = sorted(alle, key=lambda b: -float(b["abstand_km"]))[:5]
    zeile()
    zeile("Die groessten Abweichungen:")
    for b in weiteste:
        zeile(f"  {b['kennung']:<8}{b['abstand_km']:>8} km  "
              f"{b['datei']}  ->  {b['einordnung']}")

    felder = ["datei", "zeile", "kennung", "datum", "gespeichert_lat",
              "gespeichert_lon", "soll_lat", "soll_lon", "abstand_km",
              "passt_zu", "einordnung"]
    with open(BERICHT, "w", newline="", encoding="utf-8") as f:
        schreiber = csv.DictWriter(f, fieldnames=felder)
        schreiber.writeheader()
        schreiber.writerows(alle)

    zeile()
    zeile(f"{len(alle)} Zeilen im Einzelnen in {BERICHT}.")
    zeile("Nichts wurde geaendert.")


main()
