"""
Schreibt alle Kartendaten als JSON fuer die Website.

Statt sieben HTML-Dateien mit je 13 MB entsteht eine Datei von etwa
einem Megabyte. Die Farben rechnet der Browser aus den Zahlen -
dadurch ist das Umschalten zwischen Arten und Tagen sofortig statt
eines Neuladens.

Aufbau der Datei:
  {
    "stand": "2026-08-01",
    "tage": [{"versatz": 0, "datum": "...", "name": "Heute"}, ...],
    "arten": {"steinpilz": {"name": "Steinpilz", "saison": [...]}, ...},
    "zellen": [
      {"id": "W0001", "lat": .., "lon": .., "titel": "...",
       "hoehe": 87, "bestand": "Kiefer 78 %, Birke 14 %",
       "boden": {...}, "kennwerte": {...},
       "scores": {"steinpilz": [4, 6, 9, 12, 8], ...}}
    ]
  }

Ergebnis: web/daten.json
"""
import os
import json
import math
from datetime import date, timedelta

import karte as k
import arten as artenmodul
from kennwerte import berechne

ORDNER = "web"
DATEI = "daten.json"


def gitter_angaben():
    """
    Ursprung und Schrittweite des Waldrasters.

    Muss zu waldraster.py und waldraster_ergaenzen.py passen -
    dieselben Zahlen, damit die Kacheln genau auf den Feldern liegen.
    """
    sued, west = 52.05, 10.10
    nord = 52.85
    schritt_lat = k.RASTER_KM / 111.0
    mitte = (sued + nord) / 2
    schritt_lon = k.RASTER_KM / (111.0 * math.cos(math.radians(mitte)))
    # NICHT runden. Der Browser rechnet sonst mit einem minimal
    # anderen Schritt als die Skripte, und Punkte nahe einer
    # Feldgrenze landen in verschiedenen Feldern - auf der Karte
    # sieht man dann Loecher und doppelte Kacheln.
    return {"sued": sued, "west": west,
            "schritt_lat": schritt_lat,
            "schritt_lon": schritt_lon}


def runde(wert, stellen=2):
    return None if wert is None else round(wert, stellen)


# Lesbare Namen der Wettergroessen fuer die Bremse-Meldung
GROESSEN_NAMEN = {
    "bf07": "Bodenfeuchte", "bt07": "Bodentemperatur",
    "bilanz_14": "Wasserbilanz der letzten 14 Tage",
    "bilanz_60": "Wasserbilanz der letzten 60 Tage",
    "regen_reife": "Regen vor 4 bis 14 Tagen",
    "regen_frisch": "Regen der letzten 3 Tage",
    "regentage": "Zahl der Regentage",
    "temp": "Lufttemperatur",
}


def schwaechste_groesse(art, einzeln):
    """
    Welche Wettergroesse kostet die meisten Punkte?

    "Gebremst durch Wetter" allein hilft niemandem weiter. Hier wird
    nachgesehen, welche einzelne Groesse am weitesten von ihrem
    Bestwert entfernt ist - dann steht im Popup "Bodenfeuchte zu
    niedrig" statt einer Aufzaehlung von Moeglichkeiten.
    """
    e = artenmodul.ARTEN.get(art)
    if not e:
        return None

    schlimmste, groesster_verlust = None, 0
    for feld in artenmodul.MOEGLICHE_FELDER:
        if not e.get(feld) or feld.startswith("abzug"):
            continue
        hoechst = max(b[2] for b in e[feld])
        verlust = hoechst - einzeln.get(feld, 0)
        if verlust > groesster_verlust:
            groesster_verlust, schlimmste = verlust, feld

    if schlimmste is None or groesster_verlust < 4:
        return None
    return GROESSEN_NAMEN.get(schlimmste, schlimmste)


def letzter_regen(reihe, stichtag, mindest_mm=1.0):
    """
    Der letzte Tag mit nennenswertem Regen und wie viel es war.

    Unter 1 mm ist Nieselregen - der erreicht den Waldboden unter
    dem Kronendach oft gar nicht.
    """
    beste = None
    for r in reihe:
        if r.get("tag") is None or r["tag"] > stichtag:
            continue
        regen = r.get("regen")
        if regen is None or regen < mindest_mm:
            continue
        if beste is None or r["tag"] > beste["tag"]:
            beste = r

    if beste is None:
        return None

    return {"datum": beste["tag"].strftime("%d.%m.%Y"),
            "mm": round(beste["regen"], 1),
            "vor": (stichtag - beste["tag"]).days}


def regenereignis(ereignisse, stichtag):
    """
    Das letzte Regenereignis - mindestens 15 mm in drei Tagen.

    Das ist der Ausloeser fuer einen Schub, nicht jeder Nieselregen.
    """
    vergangen = [e for e in ereignisse if e["tag"] <= stichtag]
    if not vergangen:
        return None
    letztes = vergangen[-1]
    return {"datum": letztes["tag"].strftime("%d.%m.%Y"),
            "mm": letztes["mm"],
            "vor": (stichtag - letztes["tag"]).days}


def main():
    print("Lese Daten ...")
    punkte, reihen, ergaenzt = k.lade_reihen()
    if not reihen:
        print("Keine Wetterdaten.")
        return

    waldtypen = k.lade_waldtypen()
    hoehen = k.lade_hoehen()
    namen = k.lade_namen()
    boden = k.lade_boden()
    bestand = k.lade_bestand()
    funde = k.lade_funde()
    ereignisse = k.rechne_ereignisse(reihen)

    bezugstage = [date.today() + timedelta(days=t) for t in k.ZIELTAGE]
    cache = k.rechne_kennwerte(reihen, bezugstage)

    print(f"{len(reihen)} Zellen, {len(bezugstage)} Stichtage")

    zellen = []
    for ort, (lat, lon) in punkte.items():
        kenn_heute = cache.get((bezugstage[0], ort))
        if kenn_heute is None:
            continue

        wt = waldtypen.get(ort, {"typ": "unbekannt"})
        bd = boden.get(ort)
        bst = bestand.get(ort)

        # Scores fuer alle Arten und Stichtage
        scores = {}
        teile = {}
        for art in artenmodul.ARTEN:
            werte = []
            for i, tag in enumerate(bezugstage):
                kenn = cache.get((tag, ort))
                if kenn is None:
                    werte.append(None)
                    continue
                end, wetter, saison, wald, boden_f, einzeln = \
                    artenmodul.score(kenn, art, tag, wt["typ"], bd, bst)
                werte.append(end)
                if i == 0:
                    gebremst = artenmodul.bremse(wetter, saison, wald,
                                                 boden_f)
                    # Beim Wetter genauer werden: welche Groesse?
                    if gebremst and gebremst[0] == "Wetter":
                        genau = schwaechste_groesse(art, einzeln)
                        if genau:
                            gebremst = (gebremst[0], genau,
                                        gebremst[2])
                    teile[art] = {
                        "wetter": wetter, "saison": saison,
                        "bestand": wald, "boden": boden_f,
                        # Nullwerte weglassen - sie machen einen
                        # grossen Teil der Datei aus und sagen nichts
                        "einzeln": {f: p for f, p in einzeln.items()
                                    if p},
                        # Was den Wert am staerksten drueckt - ohne
                        # das ist eine niedrige Zahl nicht zu deuten
                        "bremse": (None if gebremst is None else
                                   {"was": gebremst[0],
                                    "warum": gebremst[1],
                                    "wert": gebremst[2]}),
                    }
            scores[art] = werte

        eintrag = namen.get(ort, {})
        if eintrag.get("wald"):
            titel = eintrag["wald"]
            if eintrag.get("ortsname"):
                titel += f" bei {eintrag['ortsname']}"
        elif eintrag.get("ortsname") and eintrag.get("abstand"):
            titel = (f"Wald {str(eintrag['abstand']).replace('.', ',')} km "
                     f"von {eintrag['ortsname']}")
        else:
            titel = eintrag.get("titel") or ort

        bestandstext = ""
        waldanteil = None
        if bst and bst.get("anteile"):
            oben = sorted(bst["anteile"].items(), key=lambda x: -x[1])[:4]
            bestandstext = ", ".join(
                f"{artenmodul.BAUMART_NAMEN.get(a, a)} {round(w * 100)} %"
                for a, w in oben)
            waldanteil = bst.get("waldanteil")

        # Wann hat es zuletzt geregnet, und wie viel?
        regen_zuletzt = letzter_regen(reihen[ort], bezugstage[0])
        regen_ereignis = regenereignis(ereignisse.get(ort, []),
                                       bezugstage[0])

        zellen.append({
            "id": ort,
            # Sieben Stellen sind auf 11 cm genau. Fuenf waeren zu
            # grob: Bei 1 m Genauigkeit kippten zwoelf Punkte ueber
            # eine Feldgrenze ins Nachbarfeld.
            "lat": round(lat, 7),
            "lon": round(lon, 7),
            "titel": titel,
            "hoehe": None if hoehen.get(ort) is None
                     else round(hoehen[ort]),
            "bestand": bestandstext,
            "waldanteil": runde(waldanteil, 2),
            "boden": None if not bd else {
                "ph": runde(bd.get("ph"), 1),
                "sand": runde(bd.get("sand"), 0),
                "ton": runde(bd.get("clay"), 0),
            },
            "kenn": {
                "bf07": runde(kenn_heute.get("bf07"), 3),
                "bt07": runde(kenn_heute.get("bt07"), 1),
                "temp": runde(kenn_heute.get("temp"), 1),
                "regen_reife": runde(kenn_heute.get("regen_reife"), 1),
                "regen_frisch": runde(kenn_heute.get("regen_frisch"), 1),
                "regentage": kenn_heute.get("regentage"),
                "bilanz_14": runde(kenn_heute.get("bilanz_14"), 1),
                "bilanz_60": runde(kenn_heute.get("bilanz_60"), 1),
                "frosttage": kenn_heute.get("frosttage"),
                "prognose_tage": kenn_heute.get("prognose_tage"),
            },
            "regen_zuletzt": regen_zuletzt,
            "regen_ereignis": regen_ereignis,
            "scores": scores,
            "teile": teile,
        })

    # Belegte Funde mit Tag im Jahr - die Auswahl nach Zeitfenster
    # trifft der Browser, damit sie sich mit dem Stichtag mitbewegt.
    fundpunkte = {}
    for art, liste in funde.items():
        # Neueste zuerst, damit bei der Begrenzung die aktuellen bleiben
        sortiert = sorted(liste, key=lambda x: -x["tag"].toordinal())
        fundpunkte[art] = [
            {"lat": round(f["lat"], 5), "lon": round(f["lon"], 5),
             "d": f["tag"].strftime("%d.%m.%Y"),
             "t": f["tag"].timetuple().tm_yday}
            for f in sortiert[:1200]]

    # Alter der Daten mitgeben, damit die Website warnen kann
    letzter_gemessen = k.juengste_messung(reihen)

    daten = {
        "stand": date.today().isoformat(),
        "gemessen_bis": (letzter_gemessen.isoformat()
                         if letzter_gemessen else None),
        "gebiet": {
            "sued": min(z["lat"] for z in zellen),
            "west": min(z["lon"] for z in zellen),
            "nord": max(z["lat"] for z in zellen),
            "ost": max(z["lon"] for z in zellen),
        },
        "raster_km": k.RASTER_KM,
        # Gitterursprung und Schrittweite. Damit kann die Karte die
        # Kacheln am Gitter ausrichten statt am Punkt - sonst sitzt
        # eine Kachel am Feldrand und ragt in die Nachbarzelle.
        "gitter": gitter_angaben(),
        "tage": [{"versatz": t,
                  "datum": (date.today() + timedelta(days=t)).isoformat(),
                  "name": k.tagname(t)} for t in k.ZIELTAGE],
        "arten": {
            a: {
                "name": e["name"],
                "saison": round(artenmodul.saison_rohwert(
                    e, bezugstage[0]), 2),
                # Fuer die Erklaerseite: die vollstaendige Saisonkurve
                # und die Punktbaender, damit sie ein echtes Beispiel
                # nachrechnen und zeigen kann
                "saison_jahr": [e["saison"].get(m, 0.0)
                                for m in range(1, 13)],
                "baender": {
                    feld: e[feld] for feld in artenmodul.MOEGLICHE_FELDER
                    if e.get(feld)
                },
                "hoechstpunkte": {
                    feld: max(b[2] for b in e[feld])
                    for feld in artenmodul.MOEGLICHE_FELDER if e.get(feld)
                },
            }
            for a, e in artenmodul.ARTEN.items()
        },
        "zellen": zellen,
        "funde": fundpunkte,
        "fund_fenster": 30,
    }

    os.makedirs(ORDNER, exist_ok=True)
    pfad = os.path.join(ORDNER, DATEI)
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, separators=(",", ":"))

    gross = os.path.getsize(pfad) / 1024 / 1024
    print(f"\n{len(zellen)} Zellen in {pfad} ({gross:.2f} MB)")
    print(f"{sum(len(v) for v in fundpunkte.values())} Belegfunde")

    beste = sorted(zellen, key=lambda z: -(z["scores"]["steinpilz"][0] or 0))
    if beste:
        print(f"\nBester Steinpilzwert heute: "
              f"{beste[0]['scores']['steinpilz'][0]} "
              f"({beste[0]['titel']})")


main()
