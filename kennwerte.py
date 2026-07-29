"""
Gemeinsames Modul: berechnet aus einer Tagesreihe die Groessen,
die Score und Kalibrierung benutzen.

Wird von funde_wetter2.py, kalibrieren.py und karte.py importiert -
so ist garantiert, dass alle drei genau dasselbe rechnen.
"""
from datetime import date


def zahl(text):
    """CSV-Text in Zahl. Leer wird None."""
    if text is None or text == "":
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def mittel(werte):
    werte = [w for w in werte if w is not None]
    if not werte:
        return None
    return sum(werte) / len(werte)


def berechne(reihe, stichtag):
    """
    reihe: Liste von dicts mit 'tag' (date) und den Messwerten
           regen, temp, bt07, bf07, bt728, bf728, et0
    stichtag: date, auf den sich alles bezieht

    Rueckgabe: dict mit den Kennwerten oder None, wenn zu wenig Daten.
    """
    reihe = sorted((r for r in reihe if r["tag"] <= stichtag),
                   key=lambda r: r["tag"])
    if not reihe:
        return None

    def alter(r):
        return (stichtag - r["tag"]).days

    fenster14 = [r for r in reihe if alter(r) <= 14]
    fenster60 = [r for r in reihe if alter(r) <= 60]
    letzte5 = [r for r in reihe if alter(r) <= 5]

    # Reicht die Historie ueberhaupt fuer ein 60-Tage-Fenster?
    # Es genuegt nicht, die Tage zu zaehlen - die Wasserbilanz braucht
    # Verdunstungswerte, und aeltere Zeilen haben die oft nicht.
    tage_lang = len(fenster60)
    tage_mit_et0 = sum(1 for r in fenster60
                       if r["regen"] is not None and r["et0"] is not None)
    lang_genug = tage_lang >= 45
    bilanz_lang_genug = tage_mit_et0 >= 45

    if len(fenster14) < 8:
        return None

    regen14 = [r["regen"] for r in fenster14 if r["regen"] is not None]
    if len(regen14) < 8:
        return None

    regen_reife = sum(r["regen"] for r in fenster14
                      if r["regen"] is not None and 4 <= alter(r) <= 14)
    regen_frisch = sum(r["regen"] for r in fenster14
                       if r["regen"] is not None and alter(r) <= 3)
    regentage = sum(1 for r in fenster14
                    if r["regen"] is not None and r["regen"] >= 1.0)

    tage_seit_regen = 99
    for r in fenster14:
        if r["regen"] is not None and r["regen"] >= 3.0:
            tage_seit_regen = alter(r)

    # Wasserbilanz: Regen minus Verdunstung. Das ist die Groesse,
    # die 20 mm im kuehlen Oktober von 20 mm im heissen August trennt.
    def bilanz(fenster):
        paare = [(r["regen"], r["et0"]) for r in fenster
                 if r["regen"] is not None and r["et0"] is not None]
        if not paare:
            return None
        return sum(reg - et for reg, et in paare)

    # Frost: beendet die Saison ziemlich abrupt
    temps14 = [r["temp"] for r in fenster14 if r["temp"] is not None]
    bt14 = [r["bt07"] for r in fenster14 if r["bt07"] is not None]
    frosttage = sum(1 for t in temps14 if t < 0.0)
    min_temp = min(temps14) if temps14 else None
    min_boden = min(bt14) if bt14 else None

    return {
        "regen_reife": round(regen_reife, 1),
        "frosttage": frosttage,
        "min_temp": None if min_temp is None else round(min_temp, 1),
        "min_boden": None if min_boden is None else round(min_boden, 1),
        "regen_frisch": round(regen_frisch, 1),
        "regentage": regentage,
        "tage_seit_regen": tage_seit_regen,
        "regen_60": (round(sum(r["regen"] for r in fenster60
                               if r["regen"] is not None), 1)
                     if lang_genug else None),
        "bilanz_14": None if bilanz(fenster14) is None
                     else round(bilanz(fenster14), 1),
        "bilanz_60": (None if not bilanz_lang_genug or bilanz(fenster60) is None
                      else round(bilanz(fenster60), 1)),
        "temp": None if mittel([r["temp"] for r in fenster14]) is None
                else round(mittel([r["temp"] for r in fenster14]), 1),
        "bt07": None if mittel([r["bt07"] for r in letzte5]) is None
                else round(mittel([r["bt07"] for r in letzte5]), 1),
        "bf07": None if mittel([r["bf07"] for r in letzte5]) is None
                else round(mittel([r["bf07"] for r in letzte5]), 3),
        "bt728": None if mittel([r["bt728"] for r in letzte5]) is None
                 else round(mittel([r["bt728"] for r in letzte5]), 1),
        "bf728": None if mittel([r["bf728"] for r in letzte5]) is None
                 else round(mittel([r["bf728"] for r in letzte5]), 3),
        "tage_vorhanden": len(fenster14),
        "tage_lang": tage_lang,
        "tage_et0": tage_mit_et0,
    }


# Ein Regenereignis: mindestens so viel Niederschlag innerhalb von
# hoechstens so vielen aufeinanderfolgenden Tagen.
EREIGNIS_MM = 15.0
EREIGNIS_TAGE = 3


def finde_ereignisse(reihe, mindest_mm=EREIGNIS_MM, fenster=EREIGNIS_TAGE):
    """
    Sucht Regenereignisse in einer Tagesreihe - Vergangenheit wie
    Vorhersage. Ein Ereignis ist der Ausloeser fuer einen Schub.

    Rueckgabe: Liste von {"tag": date, "mm": float}, chronologisch.
    Ueberlappende Ereignisse werden zusammengefasst.
    """
    tage = sorted((r for r in reihe if r.get("regen") is not None),
                  key=lambda r: r["tag"])
    if not tage:
        return []

    ereignisse = []
    i = 0
    while i < len(tage):
        summe = 0.0
        letzter = i
        for j in range(i, min(i + fenster, len(tage))):
            # Luecken in der Reihe beenden das Fenster
            if (tage[j]["tag"] - tage[i]["tag"]).days > fenster - 1:
                break
            summe += tage[j]["regen"]
            letzter = j
            if summe >= mindest_mm:
                break

        if summe >= mindest_mm:
            # Der letzte Tag des Ereignisses zaehlt als Ausloeser
            neu = {"tag": tage[letzter]["tag"], "mm": round(summe, 1)}
            # Ein laenger anhaltender Regen soll ein Ereignis bleiben,
            # nicht mehrere dicht aufeinanderfolgende
            if ereignisse and (neu["tag"] - ereignisse[-1]["tag"]).days <= 4:
                ereignisse[-1]["tag"] = neu["tag"]
                ereignisse[-1]["mm"] = round(
                    ereignisse[-1]["mm"] + neu["mm"], 1)
            else:
                ereignisse.append(neu)
            i = letzter + 1
        else:
            i += 1

    return ereignisse


KENNWERT_SPALTEN = [
    "regen_reife", "regen_frisch", "regentage", "tage_seit_regen",
    "regen_60", "bilanz_14", "bilanz_60",
    "temp", "bt07", "bf07", "bt728", "bf728",
    "frosttage", "min_temp", "min_boden", "tage_vorhanden",
    "tage_lang", "tage_et0",
]
