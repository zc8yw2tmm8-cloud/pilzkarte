"""
Erzeugt die Pilzkarten - fuer alle Arten in einem Lauf.

Ergebnis:
  index.html          <- diese im Browser oeffnen
  karte_steinpilz.html, karte_marone.html, ...

In index.html schaltest du oben die Art um, in der Karte selbst
rechts oben den Tag und die Schutzgebiete.

Braucht: wetter_historie.csv, waldpunkte.csv
Optional: wetter_prognose.csv, waldtypen.csv, hoehen.csv,
          schutzgebiete.geojson
"""
import csv
import os
import json
import folium
from datetime import date, timedelta
from collections import defaultdict

from kennwerte import berechne, zahl, finde_ereignisse
import arten as artenmodul
import infoseite
import farben

try:
    import weichzeichnen
except ImportError:
    weichzeichnen = None

try:
    import waldebenen
except ImportError:
    waldebenen = None

# ===== Einstellungen =====
# Welche Arten erzeugt werden. None = alle aus arten.py
NUR_ARTEN = None
ZIELTAGE = [0, 1, 2, 3, 7]
RASTER_KM = 2.0

# True = weiche Verlaeufe (braucht numpy und pillow)
# False = harte 2-km-Quadrate
WEICHE_DARSTELLUNG = True

# Baumartenebenen zum Ein- und Ausblenden. Braucht die Kacheln,
# die baumarten.py heruntergeladen hat.
WALDEBENEN_ZEIGEN = True

# True = Nachtmodus. Beide Grundkarten sind immer waehlbar,
# diese Einstellung bestimmt Farbskala, Legende und Rahmenseite.
DUNKEL = True

# Belegte Funde als Ebene einblenden. Fenster in Tagen um den Stichtag,
# jahresuebergreifend: ein Oktoberfund von 2021 erscheint auf der
# Oktoberkarte 2026.
FUNDE_ZEIGEN = True
FUNDE_FENSTER = 21
# Funde mit groberer Ortsangabe als dies werden nicht gezeigt
FUNDE_MAX_UNSICHERHEIT = 3000

KARTE_MITTE = [52.45, 10.60]
KARTE_ZOOM = 9
# =========================

HISTORIE = "wetter_historie.csv"
PROGNOSE = "wetter_prognose.csv"
TYPEN_DATEI = "waldtypen.csv"
HOEHEN_DATEI = "hoehen.csv"
NAMEN_DATEI = "ortsnamen.csv"
BODEN_DATEI = "bodendaten.csv"
FUNDE_DATEI = "funde_arten.csv"
BAUMARTEN_DATEI = "baumarten.csv"
RELIEF_GRENZEN_DATEI = "relief_grenzen.txt"
SCHUTZ_DATEI = "schutzgebiete.geojson"
INDEX = "index.html"

TAG_NAMEN = {0: "Heute", 1: "Morgen", 2: "Uebermorgen"}

TYP_NAMEN = {
    "nadel": "Nadelwald", "laub": "Laubwald", "misch": "Mischwald",
    "bruch": "Bruch-/Feuchtwald", "unbekannt": "unbekannt",
}

FELD_NAMEN = {
    "bf07": "Bodenfeuchte", "bt07": "Bodentemperatur",
    "regen_reife": "Regen Tag 4-14", "regentage": "Regentage",
    "temp": "Lufttemperatur", "trockenheit": "Abzug Trockenheit",
    "duerre_60": "Abzug Duerre 60 Tage",
    "lange_trocken": "Abzug 14+ Tage trocken",
    "bilanz_14": "Wasserbilanz 14 Tage",
    "bilanz_60": "Wasserbilanz 60 Tage",
    "frost": "Abzug Frost",
}

THEMA = farben.thema(DUNKEL)


def tagname(tag):
    return TAG_NAMEN.get(tag, f"In {tag} Tagen")


def lade_reihen():
    punkte = {}
    reihen = defaultdict(dict)

    with open(HISTORIE, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            ort = z["ort"]
            punkte[ort] = (float(z["lat"]), float(z["lon"]))

            regen = zahl(z.get("regen_icon"))
            if regen is None:
                regen = zahl(z.get("regen_era5"))
            if regen is None:
                continue

            tag = date.fromisoformat(z["datum"])
            reihen[ort][tag] = {
                "tag": tag, "regen": regen,
                "temp": zahl(z.get("temperatur")),
                "bt07": zahl(z.get("bt07")), "bf07": zahl(z.get("bf07")),
                "bt728": zahl(z.get("bt728")), "bf728": zahl(z.get("bf728")),
                "et0": zahl(z.get("et0")),
                "prognose": False,
            }

    ergaenzt = 0
    if os.path.exists(PROGNOSE):
        with open(PROGNOSE, "r", encoding="utf-8") as f:
            for z in csv.DictReader(f):
                ort = z["ort"]
                tag = date.fromisoformat(z["datum"])
                if ort not in punkte:
                    punkte[ort] = (float(z["lat"]), float(z["lon"]))
                if tag in reihen[ort]:
                    continue

                regen = zahl(z.get("regen"))
                if regen is None:
                    continue

                reihen[ort][tag] = {
                    "tag": tag, "regen": regen,
                    "temp": zahl(z.get("temperatur")),
                    "bt07": zahl(z.get("bt07")), "bf07": zahl(z.get("bf07")),
                    "bt728": zahl(z.get("bt728")),
                    "bf728": zahl(z.get("bf728")),
                    "et0": zahl(z.get("et0")),
                    "prognose": True,
                }
                ergaenzt += 1

    fertig = {ort: sorted(tage.values(), key=lambda r: r["tag"])
              for ort, tage in reihen.items()}
    return punkte, fertig, ergaenzt


def lade_waldtypen():
    typen = {}
    if not os.path.exists(TYPEN_DATEI):
        return typen
    with open(TYPEN_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            pid = (z.get("punkt_id") or "").strip()
            typ = (z.get("typ") or "").strip().lower()
            if pid and typ:
                typen[pid] = {"typ": typ,
                              "notiz": (z.get("notiz") or "").strip()}
    return typen


def lade_hoehen():
    hoehen = {}
    if not os.path.exists(HOEHEN_DATEI):
        return hoehen
    with open(HOEHEN_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            h = zahl(z.get("hoehe"))
            if h is not None:
                hoehen[z["id"]] = h
    return hoehen


def lade_namen():
    """Lesbare Bezeichnungen aus ortsnamen.py."""
    namen = {}
    if not os.path.exists(NAMEN_DATEI):
        return namen
    with open(NAMEN_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            titel = (z.get("titel") or "").strip()
            if titel:
                namen[z["id"]] = {
                    "titel": titel,
                    "abstand": (z.get("abstand_km") or "").strip(),
                    "wald": (z.get("wald") or "").strip(),
                }
    return namen


def lade_boden():
    """Bodeneigenschaften je Punkt aus bodendaten.csv."""
    boden = {}
    if not os.path.exists(BODEN_DATEI):
        return boden
    with open(BODEN_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            eintrag = {feld: zahl(z.get(feld))
                       for feld in ("ph", "sand", "clay", "cec", "humus")}
            if eintrag.get("ph") is not None or eintrag.get("sand") is not None:
                boden[z["id"]] = eintrag
    return boden


def uebersetze_art(name):
    """Legendenname oder Klassenzahl in einen lesbaren Namen."""
    schluessel = artenmodul.BAUMART_SCHLUESSEL.get(name)
    if schluessel is None and name.lstrip("-").isdigit():
        schluessel = artenmodul.BAUMART_WERTE.get(int(name))
    if schluessel:
        return artenmodul.BAUMART_NAMEN.get(schluessel, schluessel)
    return name


def uebersetze_klasse(name):
    """Klassenname oder Zahlencode in einen lesbaren Namen."""
    if not name:
        return ""
    schluessel = artenmodul.BAUMART_SCHLUESSEL.get(name)
    if schluessel is None and name.lstrip("-").isdigit():
        schluessel = artenmodul.BAUMART_WERTE.get(int(name))
    if schluessel is None:
        return name
    return artenmodul.BAUMART_NAMEN.get(schluessel, schluessel)


def lade_bestand():
    """Baumartenanteile je Zelle aus baumarten.csv."""
    bestand = {}
    if not os.path.exists(BAUMARTEN_DATEI):
        return bestand

    with open(BAUMARTEN_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            anteile = {}
            for teil in (z.get("verteilung") or "").split(";"):
                if ":" not in teil:
                    continue
                name, wert = teil.rsplit(":", 1)
                name = name.strip()

                # Namen aus der Legende, oder rohe Klassenzahlen aus
                # Dateien, die vor dem Auslesen der Legende entstanden
                schluessel = artenmodul.BAUMART_SCHLUESSEL.get(name)
                if schluessel is None and name.lstrip("-").isdigit():
                    schluessel = artenmodul.BAUMART_WERTE.get(int(name))

                w = zahl(wert)
                if schluessel and w:
                    anteile[schluessel] = anteile.get(schluessel, 0) + w

            bestand[z["id"]] = {
                "anteile": anteile,
                "waldanteil": zahl(z.get("waldanteil")),
                "haupt": uebersetze_art((z.get("haupt") or "").strip()),
                "haupt_anteil": zahl(z.get("haupt_anteil")),
            }
    return bestand


def lade_funde():
    """Belegte Fundmeldungen aus GBIF, gruppiert nach Art."""
    funde = defaultdict(list)
    if not os.path.exists(FUNDE_DATEI):
        return funde

    with open(FUNDE_DATEI, "r", encoding="utf-8") as f:
        for z in csv.DictReader(f):
            u = zahl(z.get("unsicherheit_m"))
            if u is not None and u > FUNDE_MAX_UNSICHERHEIT:
                continue
            try:
                tag = date.fromisoformat(z["datum"])
                lat = float(z["lat"])
                lon = float(z["lon"])
            except (ValueError, KeyError, TypeError):
                continue

            funde[z["art"]].append({
                "tag": tag, "lat": lat, "lon": lon,
                "ort": (z.get("ort") or "").strip(),
                "unsicherheit": u,
            })
    return funde


def tage_im_jahr_abstand(a, b):
    """Abstand zweier Daten im Jahreslauf, jahresuebergreifend."""
    ta = a.timetuple().tm_yday
    tb = b.timetuple().tm_yday
    d = abs(ta - tb)
    return min(d, 366 - d)


def fund_ebene(art, bezugstag, funde):
    """Belegte Funde im Zeitfenster um den Stichtag, als Cluster."""
    treffer = [f for f in funde.get(art, [])
               if tage_im_jahr_abstand(f["tag"], bezugstag) <= FUNDE_FENSTER]
    if not treffer:
        return None, 0

    name = (f"Belegte Funde &plusmn;{FUNDE_FENSTER} Tage "
            f"({len(treffer)})")
    gruppe = folium.FeatureGroup(name=name, show=False)

    try:
        from folium.plugins import MarkerCluster
        ziel = MarkerCluster(name=name).add_to(gruppe)
    except Exception:
        ziel = gruppe

    heute = date.today()
    for f in sorted(treffer, key=lambda x: -x["tag"].year):
        alter = heute.year - f["tag"].year
        # Juengere Funde kraeftiger
        deckkraft = 0.9 if alter <= 2 else 0.65 if alter <= 5 else 0.45

        genauigkeit = ("" if f["unsicherheit"] is None
                       else f"<br>Ortsangabe &plusmn;{round(f['unsicherheit'])} m")
        ortszeile = f"<br>{f['ort']}" if f["ort"] else ""

        text = (f"<b>{artenmodul.ARTEN[art]['name']}</b><br>"
                f"Gefunden am {f['tag'].strftime('%d.%m.%Y')}"
                f"{ortszeile}{genauigkeit}")

        folium.CircleMarker(
            location=[f["lat"], f["lon"]],
            radius=5,
            popup=folium.Popup(text, max_width=240),
            tooltip=f["tag"].strftime("%d.%m.%Y"),
            color="#1a1a1a", weight=1, opacity=deckkraft,
            fill=True, fill_color="#7b1fa2", fill_opacity=deckkraft,
        ).add_to(ziel)

    return gruppe, len(treffer)


def farbe(punkte):
    return farben.hex_farbe(punkte, DUNKEL)


def zeige(wert, faktor=1, einheit="", stellen=1):
    if wert is None:
        return "n/a"
    w = round(wert * faktor, stellen)
    if stellen == 0 or abs(w - int(w)) < 0.001:
        w = int(w)
    return f"{w}{einheit}"


def rechne_ereignisse(reihen):
    """Regenereignisse je Zelle - ueber die ganze Reihe, auch Vorhersage."""
    return {ort: finde_ereignisse(reihe) for ort, reihe in reihen.items()}


def schub_hinweis(art, ereignisse, bezugstag):
    """
    Satz zum letzten Regenereignis und dem erwarteten Schub.
    Gibt (text, tage_bis_schub) zurueck. tage_bis_schub ist None,
    wenn kein Fenster bestimmbar ist.
    """
    if not ereignisse:
        return "", None

    vergangen = [e for e in ereignisse if e["tag"] <= bezugstag]
    if not vergangen:
        return "", None

    letztes = vergangen[-1]
    alter = (bezugstag - letztes["tag"]).days
    fenster = artenmodul.schubfenster(art, letztes["tag"])

    text = (f"Letztes Regenereignis: {letztes['mm']} mm "
            f"vor {alter} Tagen")

    if fenster is None:
        return text, None

    von, bis = fenster
    tage_bis = (von - bezugstag).days

    if bezugstag < von:
        text += (f"<br>Schub erwartet ab {von.strftime('%d.%m.')} "
                 f"&ndash; in {tage_bis} Tagen")
    elif bezugstag <= bis:
        text += (f"<br><b>Schubfenster laeuft</b> "
                 f"({von.strftime('%d.%m.')} bis {bis.strftime('%d.%m.')})")
    else:
        vorbei = (bezugstag - bis).days
        text += (f"<br>Schubfenster seit {vorbei} Tagen vorbei")

    return text, tage_bis


def rechne_kennwerte(reihen, bezugstage):
    """
    Einmal pro Punkt und Tag - unabhaengig von der Pilzart.
    Spart bei sechs Arten den sechsfachen Rechenaufwand.
    """
    cache = {}
    for tag in bezugstage:
        for ort, reihe in reihen.items():
            k = berechne(reihe, tag)
            if k is None:
                continue
            k["prognose_tage"] = sum(
                1 for r in reihe if r.get("prognose") and r["tag"] <= tag)
            cache[(tag, ort)] = k
    return cache


def baue_ebene(art, bezugstag, name, punkte, cache, waldtypen, hoehen,
               namen, boden, bestand, ereignisse, sichtbar):
    gruppe = folium.FeatureGroup(name=name, show=sichtbar)

    d_lat = RASTER_KM / 111.0 / 2 * 1.02
    d_lon = RASTER_KM / (111.0 * 0.61) / 2 * 1.02

    artname = artenmodul.ARTEN[art]["name"]
    scores = []
    werte = []
    weich = WEICHE_DARSTELLUNG and weichzeichnen is not None

    for ort in punkte:
        k = cache.get((bezugstag, ort))
        if k is None:
            continue

        wt = waldtypen.get(ort, {"typ": "unbekannt", "notiz": ""})
        bd = boden.get(ort)
        bst = bestand.get(ort)
        end, wetter, saison, wald, bfaktor, einzeln = artenmodul.score(
            k, art, bezugstag, wt["typ"], bd, bst)

        lat, lon = punkte[ort]
        scores.append(end)

        if bst and bst["anteile"]:
            oben = sorted(bst["anteile"].items(), key=lambda x: -x[1])[:4]
            typ_text = ", ".join(
                f"{artenmodul.BAUMART_NAMEN.get(a, a)} {round(w * 100)} %"
                for a, w in oben)
            if bst["waldanteil"] is not None:
                typ_text += (f"<br>Waldanteil der Zelle: "
                             f"{round(bst['waldanteil'] * 100)} %")
        else:
            typ_text = TYP_NAMEN.get(wt["typ"], wt["typ"])
            if wt["notiz"]:
                typ_text += f" ({wt['notiz']})"

        teile = "".join(
            f"{FELD_NAMEN.get(f, f)} "
            f"<b>{'+' if p > 0 else ''}{p}</b><br>"
            for f, p in einzeln.items() if p != 0)

        hinweis = (f"<br><i>{k['prognose_tage']} Tage aus Vorhersage</i>"
                   if k["prognose_tage"] else "")

        schub, _ = schub_hinweis(art, ereignisse.get(ort, []), bezugstag)
        schub_block = (f"<hr style='margin:4px 0'>{schub}" if schub else "")

        if k.get("bilanz_60") is None:
            bilanz60_text = (
                f"<span style='color:#c62828'>zu wenig Daten "
                f"({k.get('tage_et0', 0)} Tage mit Verdunstung "
                f"von {k.get('tage_lang', 0)})</span>")
        else:
            bilanz60_text = zeige(k["bilanz_60"], 1, " mm")

        hoehe = hoehen.get(ort)
        eintrag = namen.get(ort)

        if eintrag:
            titel = eintrag["titel"]
            if eintrag["abstand"] and not eintrag["wald"]:
                titel += f" &middot; {eintrag['abstand']} km"
        else:
            titel = ort

        if bd:
            teile_boden = []
            if bd.get("ph") is not None:
                teile_boden.append(f"pH {bd['ph']}")
            if bd.get("sand") is not None:
                teile_boden.append(f"Sand {round(bd['sand'])} %")
            if bd.get("clay") is not None:
                teile_boden.append(f"Ton {round(bd['clay'])} %")
            boden_text = "<br>Boden: " + ", ".join(teile_boden)
        else:
            boden_text = ""

        lage = []
        if hoehe is not None:
            lage.append(zeige(hoehe, 1, " m", 0))
        lage.append(f"{lat:.3f}, {lon:.3f}")
        lage.append(ort)

        text = f"""
        <b>{titel}</b><br>
        <span style="color:#888;font-size:11px">{name} &middot;
        {" &middot; ".join(lage)}</span><br>
        {artname}: <b>{end}/100</b><br>
        <span style="color:#666">Wetter {wetter} &times; Saison {saison}
        &times; Bestand {wald} &times; Boden {bfaktor}</span><br>
        Bestand: {typ_text}{boden_text}
        <hr style="margin:4px 0">
        Bodenfeuchte 0-7: {zeige(k['bf07'], 100, ' %')}<br>
        Bodenfeuchte 7-28: {zeige(k['bf728'], 100, ' %')}<br>
        Bodentemperatur: {zeige(k['bt07'], 1, ' &deg;C')}<br>
        Lufttemperatur &Oslash;: {zeige(k['temp'], 1, ' &deg;C')}<br>
        Regen Tag 4-14: {zeige(k['regen_reife'], 1, ' mm')}<br>
        Regen Tag 0-3: {zeige(k['regen_frisch'], 1, ' mm')}<br>
        Regentage: {k['regentage']}<br>
        Wasserbilanz 14 T: {zeige(k['bilanz_14'], 1, ' mm')}<br>
        Wasserbilanz 60 T: {bilanz60_text}<br>
        Frosttage / Min. Boden: {k['frosttage']} /
        {zeige(k['min_boden'], 1, ' &deg;C')}
        {schub_block}<br>
        <hr style="margin:4px 0">
        <div style="font-size:11px">
          <b style="color:#888">PUNKTE</b><br>{teile}
          <b>Summe Wetter: {wetter}</b>
        </div>{hinweis}
        """

        werte.append((lat, lon, end))

        folium.Rectangle(
            bounds=[[lat - d_lat, lon - d_lon], [lat + d_lat, lon + d_lon]],
            popup=folium.Popup(text, max_width=280),
            tooltip=f"{titel}: {end}",
            color=None, weight=0, fill=True,
            fill_color=farbe(end),
            # bei weicher Darstellung nur unsichtbare Klickflaeche
            fill_opacity=0.0 if weich else 0.8,
        ).add_to(gruppe)

    if not scores:
        return None, 0, 0

    # Weiches Bild UNTER die Klickflaechen legen
    if weich:
        stil = "d" if DUNKEL else "h"
        dateiname = (f"{art}_t{(bezugstag - date.today()).days}"
                     f"_{stil}.png")
        pfad, grenzen = weichzeichnen.erzeuge(werte, dateiname,
                                              dunkel=DUNKEL)
        if pfad:
            folium.raster_layers.ImageOverlay(
                image=pfad, bounds=grenzen, opacity=1.0,
                interactive=False, cross_origin=False, zindex=1,
            ).add_to(gruppe)

    return gruppe, len(scores), sum(scores) / len(scores)


def reliefebenen(karte):
    """Feinkarte aus dem 1-m-Hoehenmodell, falls relief.py gelaufen ist."""
    if not os.path.exists(RELIEF_GRENZEN_DATEI):
        return 0

    try:
        with open(RELIEF_GRENZEN_DATEI, "r", encoding="utf-8") as f:
            sued, west, nord, ost = [float(t) for t in
                                     f.read().strip().split(",")]
    except Exception:
        return 0

    grenzen = [[sued, west], [nord, ost]]
    anzahl = 0

    for datei, titel in [
        ("bilder/relief_feuchte.png", "Feuchte Senken (1 m Hoehenmodell)"),
        ("bilder/relief_schummerung.png", "Gelaendeschummerung (1 m)"),
    ]:
        if not os.path.exists(datei):
            continue
        gruppe = folium.FeatureGroup(name=titel, show=False)
        folium.raster_layers.ImageOverlay(
            image=datei, bounds=grenzen, opacity=1.0,
            interactive=False, cross_origin=False, zindex=3,
        ).add_to(gruppe)
        gruppe.add_to(karte)
        anzahl += 1

    return anzahl


def waldflaechen(karte, vorrat):
    """Baumartenebenen als durchsichtige Bilder. Einmal erzeugt,
    danach von allen Artenkarten gemeinsam benutzt."""
    if not WALDEBENEN_ZEIGEN or waldebenen is None:
        return 0

    if "ebenen" not in vorrat:
        vorrat["ebenen"], vorrat["grenzen"] = waldebenen.erzeuge()

    ebenen, grenzen = vorrat["ebenen"], vorrat["grenzen"]
    if not ebenen or grenzen is None:
        return 0

    for name, pfad, _ in ebenen:
        gruppe = folium.FeatureGroup(name=f"Wald: {name}", show=False)
        folium.raster_layers.ImageOverlay(
            image=pfad, bounds=grenzen, opacity=1.0,
            interactive=False, cross_origin=False, zindex=2,
        ).add_to(gruppe)
        gruppe.add_to(karte)

    return len(ebenen)


def schutzgebiete(karte):
    if not os.path.exists(SCHUTZ_DATEI):
        return
    with open(SCHUTZ_DATEI, "r", encoding="utf-8") as f:
        sg = json.load(f)

    for stufe, farbwert, titel, an in [
        ("streng", THEMA["schutz_streng"],
         "Naturschutzgebiete (Sammeln verboten)", True),
        ("mild", THEMA["schutz_mild"],
         "Landschaftsschutz / Natura 2000", False),
    ]:
        teil = {"type": "FeatureCollection",
                "features": [x for x in sg["features"]
                             if x["properties"]["stufe"] == stufe]}
        if not teil["features"]:
            continue

        gruppe = folium.FeatureGroup(name=titel, show=an)
        folium.GeoJson(
            teil,
            style_function=lambda x, c=farbwert: {
                "fillColor": c, "color": c, "weight": 2,
                "fillOpacity": 0.15, "dashArray": "5,5"},
            tooltip=folium.GeoJsonTooltip(fields=["name"],
                                          aliases=["Schutzgebiet:"]),
        ).add_to(gruppe)
        gruppe.add_to(karte)


def legende(karte, art, schnitt_heute):
    stufen = [(95, "sehr gut"), (80, "gut"), (60, "moeglich"),
              (40, "schwach"), (15, "kaum")]
    zeilen = "".join(
        f'<div><span style="display:inline-block;width:14px;height:14px;'
        f'background:{farbe(w)};margin-right:6px;vertical-align:middle;'
        f'border-radius:2px"></span>{w}+ {t}</div>' for w, t in stufen)

    html = f"""
    <div style="position:fixed;bottom:22px;left:12px;z-index:1000;
                background:{THEMA['kasten']};color:{THEMA['text']};
                padding:10px 12px;border-radius:8px;
                box-shadow:0 1px 6px rgba(0,0,0,.45);
                font:12px sans-serif;line-height:1.5">
      <b>{artenmodul.ARTEN[art]['name']}</b><br>
      <span style="color:{THEMA['text_leise']}">Schnitt heute:
      {round(schnitt_heute)}</span>
      <hr style="margin:6px 0;border:0;border-top:1px solid {THEMA['linie']}">
      {zeilen}
    </div>
    <style>
      .leaflet-control-layers {{
        background: {THEMA['kasten']} !important;
        color: {THEMA['text']} !important;
        border: 1px solid {THEMA['linie']} !important;
      }}
      .leaflet-control-layers-separator {{
        border-top: 1px solid {THEMA['linie']} !important;
      }}
      .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
        background: {THEMA['flaeche']} !important;
        color: {THEMA['text']} !important;
      }}
      .leaflet-tooltip {{
        background: {THEMA['flaeche']} !important;
        color: {THEMA['text']} !important;
        border-color: {THEMA['linie']} !important;
      }}
      .leaflet-bar a {{
        background: {THEMA['flaeche']} !important;
        color: {THEMA['text']} !important;
      }}
    </style>
    """
    karte.get_root().html.add_child(folium.Element(html))


def baue_karte(art, punkte, cache, waldtypen, hoehen, namen, boden,
               bestand, ereignisse, funde, vorrat):
    erst = farben.thema(DUNKEL)
    zweit = farben.thema(not DUNKEL)

    karte = folium.Map(location=KARTE_MITTE, zoom_start=KARTE_ZOOM,
                       tiles=None)
    folium.TileLayer(tiles=erst["tiles"], attr=erst["attr"],
                     name=erst["name_hell"], overlay=False,
                     control=True).add_to(karte)
    folium.TileLayer(tiles=zweit["tiles"], attr=zweit["attr"],
                     name=zweit["name_hell"], overlay=False,
                     control=True).add_to(karte)

    schnitt_heute = 0

    for i, tag in enumerate(ZIELTAGE):
        bezugstag = date.today() + timedelta(days=tag)
        gruppe, anzahl, schnitt = baue_ebene(
            art, bezugstag, tagname(tag), punkte, cache,
            waldtypen, hoehen, namen, boden, bestand, ereignisse,
            i == 0)
        if gruppe is None:
            continue
        gruppe.add_to(karte)
        if i == 0:
            schnitt_heute = schnitt

    anzahl_funde = 0
    if FUNDE_ZEIGEN:
        gruppe, anzahl_funde = fund_ebene(art, date.today(), funde)
        if gruppe is not None:
            gruppe.add_to(karte)

    waldflaechen(karte, vorrat)
    vorrat["relief"] = reliefebenen(karte)
    schutzgebiete(karte)
    folium.LayerControl(collapsed=True).add_to(karte)
    legende(karte, art, schnitt_heute)

    dateiname = f"karte_{art}.html"
    karte.save(dateiname)
    return dateiname, schnitt_heute, anzahl_funde


def schreibe_index(eintraege):
    """Rahmenseite mit Artenumschaltern."""
    T = THEMA
    knoepfe = "".join(
        f'<button class="art" data-datei="{datei}" data-i="{i}">'
        f'{name}<span>{round(schnitt)}</span></button>'
        for i, (name, datei, schnitt) in enumerate(eintraege))

    knoepfe += ('<button class="art info" data-datei="info.html">'
                '? Wie wird gerechnet</button>')

    erste = eintraege[0][1] if eintraege else ""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Pilzkarte</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font: 15px/1.4 system-ui, sans-serif;
          display: flex; flex-direction: column; height: 100vh;
          background: {T['grund']}; color: {T['text']}; }}
  header {{ padding: 10px 14px; background: {T['flaeche']};
            border-bottom: 1px solid {T['linie']};
            box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
  h1 {{ margin: 0 0 8px; font-size: 16px; font-weight: 600; }}
  .leiste {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  button.art {{ border: 1px solid {T['linie']};
                background: {T['grund']}; color: {T['text']};
                padding: 7px 12px; border-radius: 20px; cursor: pointer;
                font-size: 14px; display: flex; align-items: baseline;
                gap: 6px; }}
  button.art:hover {{ border-color: {T['akzent']}; }}
  button.art.aktiv {{ background: {T['akzent']};
                      border-color: {T['akzent']};
                      color: {T['flaeche']}; }}
  button.art.info {{ margin-left: auto;
                     background: {T['flaeche']};
                     border-style: dashed; }}
  button.art.info.aktiv {{ background: #455a64; border-color: #455a64; }}
  button.art span {{ font-size: 11px; opacity: .7; }}
  iframe {{ flex: 1; width: 100%; border: 0; }}
</style>
</head>
<body>
<header>
  <h1>Pilzkarte &ndash; Region Wolfsburg / Braunschweig / Suedheide</h1>
  <div class="leiste">{knoepfe}</div>
</header>
<iframe id="rahmen" src="{erste}"></iframe>
<script>
  var knoepfe = document.querySelectorAll('button.art');
  var rahmen = document.getElementById('rahmen');
  knoepfe.forEach(function (b) {{
    b.addEventListener('click', function () {{
      knoepfe.forEach(function (x) {{ x.classList.remove('aktiv'); }});
      b.classList.add('aktiv');
      rahmen.src = b.dataset.datei;
    }});
  }});
  if (knoepfe.length) {{ knoepfe[0].classList.add('aktiv'); }}
</script>
</body>
</html>
"""
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)


def schubkalender(ereignisse):
    """Uebersicht: wann waere je Art mit einem Schub zu rechnen?"""
    heute = date.today()
    alle = [e for liste in ereignisse.values() for e in liste]
    if not alle:
        return

    letzte = sorted({e["tag"] for e in alle})[-4:]
    if not letzte:
        return

    print("\nSchubkalender (Hinweis, geht NICHT in den Score ein)")
    print(f"  {'Art':<18}{'Ausloeser':>11}{'Schub von':>11}"
          f"{'bis':>11}   Stand")

    for art, einstellung in artenmodul.ARTEN.items():
        if not einstellung.get("verzug"):
            print(f"  {einstellung['name']:<18}{'-':>11}{'-':>11}"
                  f"{'-':>11}   nicht regengesteuert")
            continue

        bestes = None
        for tag in reversed(letzte):
            fenster = artenmodul.schubfenster(art, tag)
            if fenster is None:
                continue
            von, bis = fenster
            if bis >= heute:
                bestes = (tag, von, bis)
                break

        if bestes is None:
            print(f"  {einstellung['name']:<18}{'-':>11}{'-':>11}"
                  f"{'-':>11}   kein aktuelles Fenster")
            continue

        tag, von, bis = bestes
        if heute < von:
            stand = f"in {(von - heute).days} Tagen"
        elif heute <= bis:
            stand = "laeuft gerade"
        else:
            stand = "vorbei"

        print(f"  {einstellung['name']:<18}"
              f"{tag.strftime('%d.%m.'):>11}"
              f"{von.strftime('%d.%m.'):>11}"
              f"{bis.strftime('%d.%m.'):>11}   {stand}")


def main():
    liste = NUR_ARTEN or list(artenmodul.ARTEN)
    unbekannt = [a for a in liste if a not in artenmodul.ARTEN]
    if unbekannt:
        print("Unbekannte Art:", ", ".join(unbekannt))
        return

    punkte, reihen, ergaenzt = lade_reihen()
    if not reihen:
        print("Keine Wetterdaten. Erst nachfuellen.py laufen lassen.")
        return

    waldtypen = lade_waldtypen()
    hoehen = lade_hoehen()
    namen = lade_namen()
    boden = lade_boden()
    bestand = lade_bestand()
    funde = lade_funde() if FUNDE_ZEIGEN else {}

    print(f"{len(reihen)} Punkte, {ergaenzt} Prognosewerte")

    # Reicht die Historie fuer die 60-Tage-Fenster?
    alle_tage = [r["tag"] for reihe in reihen.values() for r in reihe]
    if alle_tage:
        spanne = (max(alle_tage) - min(alle_tage)).days
        print(f"Historie umfasst {spanne} Tage "
              f"({min(alle_tage)} bis {max(alle_tage)})")
        mit_et0 = sum(1 for reihe in reihen.values() for r in reihe
                      if r.get("et0") is not None)
        gesamt_zeilen = sum(len(r) for r in reihen.values())
        if gesamt_zeilen:
            print(f"Verdunstungswerte bei "
                  f"{round(mit_et0 / gesamt_zeilen * 100)} % der Zeilen")

        if spanne < 60 or mit_et0 < gesamt_zeilen * 0.7:
            print("  ACHTUNG: Die 60-Tage-Wasserbilanz kann nicht sauber")
            print("  berechnet werden - zu kurze Historie oder fehlende")
            print("  Verdunstungswerte in aelteren Zeilen. Beim Pfifferling")
            print("  ist das die wichtigste Groesse.")
            print("  Abhilfe: wetter_historie.csv loeschen, dann")
            print("  nachfuellen.py und sammeln.py neu laufen lassen.")
    print(f"Waldtyp bekannt bei {len(waldtypen)} Punkten")
    print(f"Ortsname bekannt bei {len(namen)} Punkten")
    print(f"Bodendaten bei {len(boden)} Punkten")
    if bestand:
        mit_wald = sum(1 for b in bestand.values()
                       if (b["waldanteil"] or 0) >= 0.5)
        mit_arten = sum(1 for b in bestand.values() if b["anteile"])
        print(f"Baumarten bei {len(bestand)} Punkten "
              f"({mit_wald} mit ueber 50 % Waldanteil)")
        if mit_arten == 0:
            print("  ACHTUNG: keine Anteile lesbar. Die Spalte verteilung")
            print("  in baumarten.csv passt zu keiner bekannten Schreibweise.")
        elif mit_arten < len(bestand) * 0.9:
            print(f"  Nur bei {mit_arten} Punkten sind Anteile lesbar.")
    if funde:
        gesamt = sum(len(v) for v in funde.values())
        print(f"Belegte Funde: {gesamt} in {len(funde)} Arten")
    if WEICHE_DARSTELLUNG and weichzeichnen is None:
        print("\nWeiche Darstellung gewuenscht, aber numpy/pillow fehlen.")
        print("  pip install numpy pillow")
        print("Zeichne bis dahin harte Quadrate.")
    elif WEICHE_DARSTELLUNG:
        print("Darstellung: weiche Verlaeufe (Ordner bilder/)")

    print("\nSuche Regenereignisse ...")
    ereignisse = rechne_ereignisse(reihen)
    anzahl = sum(len(e) for e in ereignisse.values())
    print(f"  {round(anzahl / max(1, len(ereignisse)), 1)} Ereignisse "
          f"je Zelle in den letzten Monaten")

    bezugstage = [date.today() + timedelta(days=t) for t in ZIELTAGE]
    if WALDEBENEN_ZEIGEN and waldebenen is None:
        print("Waldebenen gewuenscht, aber waldebenen.py fehlt.")
    elif WALDEBENEN_ZEIGEN and not os.path.isdir("kacheln"):
        print("Waldebenen: keine Kacheln vorhanden "
              "(erst baumarten.py laufen lassen)")

    print("\nRechne Kennwerte (einmal fuer alle Arten) ...")
    cache = rechne_kennwerte(reihen, bezugstage)
    print(f"  {len(cache)} Punkt-Tage\n")

    schubkalender(ereignisse)

    vorrat = {}
    eintraege = []
    for art in liste:
        datei, schnitt, nfunde = baue_karte(art, punkte, cache, waldtypen,
                                            hoehen, namen, boden, bestand,
                                            ereignisse, funde, vorrat)
        name = artenmodul.ARTEN[art]["name"]
        saison = artenmodul.ARTEN[art]["saison"].get(date.today().month, 0)
        zusatz = f"   {nfunde} Belegfunde" if nfunde else ""
        print(f"  {name:18s} Schnitt heute {round(schnitt):3d}   "
              f"Saison {saison}{zusatz}   -> {datei}")
        eintraege.append((name, datei, schnitt))

    if vorrat.get("ebenen"):
        print(f"\n  {len(vorrat['ebenen'])} Waldebenen erzeugt")
    if vorrat.get("relief"):
        print(f"  {vorrat['relief']} Reliefebenen eingebunden")

    # bester Kandidat nach vorne
    eintraege.sort(key=lambda e: -e[2])

    infodatei = infoseite.schreibe(dunkel=DUNKEL)
    print(f"\n  Erklaerseite -> {infodatei}")

    schreibe_index(eintraege)

    print(f"\nFertig. {INDEX} im Browser oeffnen.")
    if eintraege:
        print(f"Beste Art heute: {eintraege[0][0]} "
              f"(Schnitt {round(eintraege[0][2])})")


main()
