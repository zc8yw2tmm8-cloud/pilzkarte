"""
Holt die Vorhersage fuer 7 Tage. Wird jeden Tag komplett ueberschrieben -
Nur gepruefte Ergebnisse duerfen die bisherige Datei ersetzen.

Nur best_match: icon_d2 reicht nur zwei Tage und liefert keine Bodenwerte.
"""
import csv
import os
import sys
import time
import threading
import math
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

DATEI = "wetter_prognose.csv"
PUNKTE_DATEI = "waldpunkte.csv"
TAGE_VORAUS = 6

BUENDEL = 40
ARBEITER = 4
PAUSE = 0.1

# Wie viele der Punkte mindestens zurueckkommen muessen, damit die
# alte Datei ersetzt wird. Vorher reichte eine einzige Zeile: Kamen
# 200 von 1.632 Punkten, wurde trotzdem alles ueberschrieben, der
# Lauf meldete Erfolg, und die Seite wurde mit Luecken neu gebaut.
MINDEST_ANTEIL = 0.98

FELDER = [
    "precipitation_sum",
    "temperature_2m_mean",
    "soil_temperature_0_to_7cm_mean",
    "soil_moisture_0_to_7cm_mean",
    "soil_temperature_7_to_28cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "et0_fao_evapotranspiration",
]

SPALTEN = ["datum", "ort", "lat", "lon", "regen", "temperatur",
           "bt07", "bf07", "bt728", "bf728", "et0"]


def lade_punkte():
    punkte = []
    with open(PUNKTE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            punkte.append((z["id"], float(z["lat"]), float(z["lon"])))
    return punkte


bremse = threading.Event()


def hole_buendel(orte, start, ende):
    """Mehrere Orte in einer Anfrage. None bei Misserfolg."""
    import requests

    url = "https://api.open-meteo.com/v1/forecast"
    parameter = {
        "latitude": ",".join(f"{o[1]}" for o in orte),
        "longitude": ",".join(f"{o[2]}" for o in orte),
        "start_date": str(start), "end_date": str(ende),
        "daily": ",".join(FELDER),
        "timezone": "Europe/Berlin",
    }

    for versuch in range(4):
        while bremse.is_set():
            time.sleep(1)
        try:
            antwort = requests.get(url, params=parameter, timeout=120)
        except Exception:
            time.sleep(2 * (versuch + 1))
            continue

        if antwort.status_code == 429:
            if not bremse.is_set():
                bremse.set()
                time.sleep(20)
                bremse.clear()
            time.sleep(4 * (versuch + 1))
            continue
        if antwort.status_code != 200:
            time.sleep(2 * (versuch + 1))
            continue

        try:
            daten = antwort.json()
        except Exception:
            time.sleep(2)
            continue

        if isinstance(daten, dict):
            daten = [daten]
        if not isinstance(daten, list) or len(daten) != len(orte):
            return None

        return [d.get("daily") if isinstance(d, dict) else None
                for d in daten]

    return None


def buendel_moeglich(orte, start, ende):
    if len(orte) < 2:
        return False
    e = hole_buendel(orte[:2], start, ende)
    return e is not None and len(e) == 2


def fehlt_etwas(zeilen, orte, start, ende):
    """Prueft Ort/Tag-Eindeutigkeit, Werte und die Abdeckung vor dem Ersetzen.

    Aufwand linear in der Zeilenzahl; keine Suche pro Ort durch alle Zeilen.
    """
    if not orte or start > ende:
        return ["Keine Orte oder ungueltiger Prognosezeitraum"]
    bekannt = {o[0]: (o[1], o[2]) for o in orte}
    if len(bekannt) != len(orte):
        return ["Doppelte Ortskennungen im Eingaberaster"]
    if any(not name or not all(math.isfinite(v) for v in xy)
           or abs(xy[0]) > 90 or abs(xy[1]) > 180
           for name, xy in bekannt.items()):
        return ["Ungueltige Ortskennung oder Koordinaten im Eingaberaster"]

    tage = [(start + timedelta(days=i)).isoformat()
            for i in range((ende - start).days + 1)]
    je_tag = {t: set() for t in tage}
    gesehen = set()
    fehler = {}

    def mangel(text):
        fehler[text] = fehler.get(text, 0) + 1

    for z in zeilen:
        ort, tag = z.get("ort"), z.get("datum")
        if ort not in bekannt or tag not in je_tag:
            mangel("Zeilen mit unbekanntem Ort oder unerwartetem Datum")
            continue
        schluessel = (ort, tag)
        if schluessel in gesehen:
            mangel("Doppelte Ort-Tag-Zeilen")
        gesehen.add(schluessel)
        try:
            werte = [z[k] for k in SPALTEN[2:]]
            if any(isinstance(v, bool) or not math.isfinite(float(v))
                   for v in werte):
                raise ValueError
            if (float(z["lat"]), float(z["lon"])) != bekannt[ort]:
                mangel("Zeilen mit vom Eingaberaster abweichenden Koordinaten")
                continue
        except (KeyError, ValueError, TypeError, OverflowError):
            mangel("Zeilen mit fehlenden oder nicht endlichen Messwerten/Koordinaten")
            continue
        je_tag[tag].add(ort)

    maengel = [f"{text}: {zahl}" for text, zahl in fehler.items()]
    mindestens = math.ceil(len(orte) * MINDEST_ANTEIL)
    # Derselbe Ort muss den gesamten Zeitraum abdecken. Wechselnde Luecken
    # duerfen nicht an jedem Tag erneut die Ausfalltoleranz ausschoepfen.
    vollstaendig = set.intersection(*je_tag.values())
    if len(vollstaendig) < mindestens:
        maengel.append(f"Nur {len(vollstaendig)} von {len(orte)} Orten an allen "
                       f"{len(tage)} Tagen vollstaendig (mindestens {mindestens})")
    for tag in tage:
        if len(je_tag[tag]) < mindestens:
            maengel.append(f"{tag}: nur {len(je_tag[tag])} von {len(orte)} Orten")
    return maengel


def tageszeilen(ort, daten):
    """Antwortform pruefen, bevor Spalten per Index zusammengefuehrt werden."""
    if not isinstance(daten, dict) or not isinstance(daten.get("time"), list):
        raise ValueError("daily.time fehlt oder ist keine Liste")
    tage = daten["time"]
    if not tage or any(not isinstance(t, str) for t in tage):
        raise ValueError("Leere oder ungueltige Tagesliste")
    if any(not isinstance(daten.get(f), list) or len(daten[f]) != len(tage)
           for f in FELDER):
        raise ValueError("Messwertspalten fehlen oder haben verschiedene Laengen")
    name, lat, lon = ort
    return [dict(zip(SPALTEN, [tag, name, lat, lon]
                     + [daten[f][i] for f in FELDER]))
            for i, tag in enumerate(tage)]


def schreibe(zeilen):
    """Erst danebenschreiben, dann umbenennen.

    Direkt in die Zieldatei zu schreiben heisst: Ein Abbruch mitten
    im Schreiben hinterlaesst eine halbe CSV, die niemandem auffaellt.
    os.replace ist auf einem Laufwerk unteilbar - entweder die alte
    Datei steht noch ganz da oder die neue.
    """
    vorlaeufig = DATEI + ".neu"
    with open(vorlaeufig, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SPALTEN)
        writer.writeheader()
        writer.writerows(zeilen)
    os.replace(vorlaeufig, DATEI)


def main():
    start = date.today()
    ende = start + timedelta(days=TAGE_VORAUS)
    orte = lade_punkte()
    # Rasterfehler vor dem ersten Netzwerkabruf erkennen.
    rasterfehler = fehlt_etwas([], orte, start, ende)
    if not orte or any("Eingaberaster" in m for m in rasterfehler):
        print("Ungueltiges Eingaberaster - alte Datei bleibt stehen.", flush=True)
        sys.exit(1)

    print(f"Prognose {start} bis {ende} fuer {len(orte)} Punkte", flush=True)

    gebuendelt = buendel_moeglich(orte, start, ende)
    print(f"Mehrere Orte je Anfrage: "
          f"{'ja, ' + str(BUENDEL) + ' auf einmal' if gebuendelt else 'nein'}",
          flush=True)

    pakete = ([orte[i:i + BUENDEL] for i in range(0, len(orte), BUENDEL)]
              if gebuendelt else [[o] for o in orte])

    zeilen = []
    fehler = 0
    sperre = threading.Lock()
    beginn = time.time()
    erledigt = [0]

    def arbeite(paket):
        return paket, hole_buendel(paket, start, ende)

    with ThreadPoolExecutor(max_workers=ARBEITER) as pool:
        for paket, ergebnis in pool.map(arbeite, pakete):
            time.sleep(PAUSE)
            with sperre:
                erledigt[0] += 1
                if ergebnis is None:
                    fehler += len(paket)
                else:
                    for (name, lat, lon), d in zip(paket, ergebnis):
                        if not d:
                            fehler += 1
                            continue
                        try:
                            zeilen.extend(tageszeilen((name, lat, lon), d))
                        except ValueError:
                            fehler += 1


                if erledigt[0] % 20 == 0 or erledigt[0] == len(pakete):
                    dauer = time.time() - beginn
                    rest = (len(pakete) - erledigt[0]) / max(
                        erledigt[0] / max(dauer, 0.1), 0.01)
                    print(f"  {erledigt[0]} von {len(pakete)} Anfragen, "
                          f"{len(zeilen)} Werte, {fehler} Fehler, "
                          f"noch ~{rest/60:.0f} min", flush=True)

    if not zeilen:
        print("Keine Prognosewerte erhalten - alte Datei bleibt stehen.",
              flush=True)
        sys.exit(1)

    maengel = fehlt_etwas(zeilen, orte, start, ende)
    if maengel:
        print("\nVorhersage unvollstaendig - alte Datei bleibt stehen:",
              flush=True)
        for m in maengel:
            print(f"  {m}", flush=True)
        print("\nBesser eine Vorhersage von gestern als eine mit\n"
              "Loechern: Fehlende Zellen werden auf der Karte wie\n"
              "schlechte Bedingungen gezeichnet.", flush=True)
        sys.exit(1)

    schreibe(zeilen)

    tage_je_ort = {}
    for z in zeilen:
        tage_je_ort.setdefault(z["ort"], set()).add(z["datum"])
    komplette = sum(len(t) == TAGE_VORAUS + 1 for t in tage_je_ort.values())
    print(f"Abdeckung: {komplette}/{len(orte)} Orte mit allen Tagen; "
          f"{len(orte) - komplette} Orte unvollstaendig oder fehlend.", flush=True)

    print(f"\n{len(zeilen)} Prognosewerte in {time.time()-beginn:.0f} s.",
          flush=True)
    if fehler:
        print(f"{fehler} Punkte ohne Daten.", flush=True)


if __name__ == "__main__":
    main()
