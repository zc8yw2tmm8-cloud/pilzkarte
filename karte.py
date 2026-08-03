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
import time
import json
import folium
from datetime import date, timedelta
from collections import defaultdict

from kennwerte import berechne, zahl, finde_ereignisse
import historie
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
ZIELTAGE = [0, 1, 2, 3, 4, 5, 6]
RASTER_KM = 2.0

# True = weiche Verlaeufe (braucht numpy und pillow)
# False = harte 2-km-Quadrate
WEICHE_DARSTELLUNG = True

# Ausfuehrliche Popups nur auf der Heute-Ebene. Die Prognosetage
# behalten den Tooltip mit dem Score. Spart etwa 80 Prozent des
# erzeugten HTML und macht Datei wie Browser deutlich schneller.
POPUP_NUR_HEUTE = True

# Ebenen ohne ausfuehrliche Popups als EIN Kartenobjekt statt 1046
# einzelnen Rechtecken. folium rendert jedes Objekt einzeln durch eine
# Vorlage - das ist der groesste Zeitfresser beim Schreiben der Dateien.
GEOJSON_EBENEN = True

# Auch die Heute-Ebene mit ihren ausfuehrlichen Popups zusammenfassen.
# Bringt den groessten Zeitgewinn, ist aber der unsicherste Umbau:
# Das Popup-HTML steckt dann in einer GeoJSON-Eigenschaft. Falls die
# Popups leer bleiben oder Rohtext zeigen, hier auf False setzen.
GEOJSON_HEUTE = True

# Zeigt an, wo die Laufzeit hingeht. Zum Suchen von Bremsen.
ZEITMESSUNG = True

# Bilder verlinken statt einbetten.
# folium liest eine Bilddatei ein und schreibt sie base64-kodiert in die
# HTML, sobald es sie als lokale Datei erkennt. Bei elf Waldebenen und
# zwei Reliefbildern sind das rund 25 MB - in JEDER der sieben Karten.
# Ein angehaengtes Rautezeichen laesst folium die Angabe als Adresse
# behandeln; der Browser ignoriert es und laedt die Datei.
# Preis: der Ordner bilder/ muss neben den HTML-Dateien liegen.
BILDER_EINBETTEN = False

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

PROGNOSE = "wetter_prognose.csv"
TYPEN_DATEI = "waldtypen.csv"
HOEHEN_DATEI = "hoehen.csv"
NAMEN_DATEI = "ortsnamen.csv"
BODEN_DATEI = "bodendaten.csv"
FUNDE_DATEI = "funde_arten.csv"
BAUMARTEN_DATEI = "baumarten.csv"
RELIEF_GRENZEN_DATEI = "relief_grenzen.csv"
RELIEF_ALT = "relief_grenzen.txt"
RELIEF_WEIT = "relief_weit_grenzen.txt"
SCHUTZ_DATEI = "schutzgebiete.geojson"
INDEX = "index.html"

TAG_NAMEN = {0: "Heute", 1: "Morgen", 2: "Uebermorgen"}

TYP_NAMEN = {
    "nadel": "Nadelwald", "laub": "Laubwald", "misch": "Mischwald",
    "bruch": "Bruch-/Feuchtwald", "unbekannt": "unbekannt",
}

FELD_NAMEN = {
    "bf07": "Bodenfeuchte", "bt07": "Bodentemperatur",
    "regen_reife": "Niederschlag Tag 4\u201314", "regentage": "Regentage",
    "temp": "Lufttemperatur", "trockenheit": "Abzug: Boden ausgetrocknet",
    "duerre_60": "Abzug: D\u00fcrre \u00fcber 60 Tage",
    "lange_trocken": "Abzug: 14+ Tage ohne Regen",
    "bilanz_14": "Wasserbilanz 14 Tage",
    "bilanz_60": "Wasserbilanz 60 Tage",
    "frost": "Abzug: Frost",
}

THEMA = farben.thema(DUNKEL)

BILDZEIT = [0.0]


# 1x1 durchsichtiges PNG als Datenadresse. folium erkennt "data:" als
# Adresse und liest keine Datei ein.
PLATZHALTER = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
               "CAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU"
               "5ErkJggg==")


def bild_ebene(pfad, grenzen, zindex):
    """
    Bildebene, die auf die Datei verweist statt sie einzubetten.

    folium liest eine angegebene Bilddatei ein und schreibt sie
    base64-kodiert in die HTML. Bei dreizehn Ebenen in sieben Karten
    sind das rund 25 MB je Datei. Deshalb bekommt folium hier ein
    Platzhalterbild, und die Adresse wird danach auf den echten Pfad
    gesetzt - der Browser laedt die Datei dann selbst.
    """
    quelle = pfad if BILDER_EINBETTEN else PLATZHALTER
    ebene = folium.raster_layers.ImageOverlay(
        image=quelle, bounds=grenzen, opacity=1.0,
        interactive=False, cross_origin=False, zindex=zindex,
    )
    if not BILDER_EINBETTEN:
        ebene.url = pfad
    return ebene


def tagname(tag):
    return TAG_NAMEN.get(tag, f"In {tag} Tagen")


def lade_reihen():
    punkte = {}
    reihen = defaultdict(dict)

    # Nur die Monate lesen, die ins Zeitfenster fallen
    grenze = (date.today() - timedelta(days=100)).isoformat()
    for z in historie.lese(grenze):
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
                    "ortsname": (z.get("ort") or "").strip(),
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
    """Zahl mit Komma statt Punkt - deutsche Schreibweise."""
    if wert is None:
        return "&ndash;"
    w = round(wert * faktor, stellen)
    if stellen == 0:
        text = str(int(round(w)))
    else:
        text = f"{w:.{stellen}f}".replace(".", ",")
    return f"{text}{einheit}"


def komma(wert, stellen=2):
    """Zahl mit Komma, mindestens eine Nachkommastelle."""
    text = f"{wert:.{stellen}f}".rstrip("0")
    if text.endswith("."):
        text += "0"
    return text.replace(".", ",")


def alle_arten_verlauf(cache, bezugstage, punkte, waldtypen, boden,
                       bestand):
    """
    Score aller Arten je Zelle und Stichtag.

    Kostet fast nichts, weil die Kennwerte schon gerechnet sind, und
    liefert drei Dinge auf einmal: den Artenvergleich im Popup, die
    Bestenliste und den Trend ueber die naechsten Tage.

    Rueckgabe: {ort: {art: [wert je Stichtag]}}
    """
    ergebnis = {}
    for ort in punkte:
        wt = waldtypen.get(ort, {"typ": "unbekannt"})
        bd, bst = boden.get(ort), bestand.get(ort)
        je_art = {a: [] for a in artenmodul.ARTEN}

        for tag in bezugstage:
            kenn = cache.get((tag, ort))
            for art in artenmodul.ARTEN:
                je_art[art].append(
                    None if kenn is None else artenmodul.score(
                        kenn, art, tag, wt["typ"], bd, bst)[0])

        if any(w is not None for liste in je_art.values() for w in liste):
            ergebnis[ort] = je_art
    return ergebnis


WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def trend_text(werte, bezugstage, heute_wert):
    """
    Kurzer Hinweis, ob es besser oder schlechter wird.

    Beantwortet die eigentliche Frage: jetzt losfahren oder warten?
    """
    kuenftig = [(t, w) for t, w in zip(bezugstage, werte)
                if w is not None and t > bezugstage[0]]
    if not kuenftig or heute_wert is None:
        return ""

    besttag, bestwert = max(kuenftig, key=lambda x: x[1])
    schlecht = min(w for _, w in kuenftig)

    if bestwert >= heute_wert + 8:
        pfeil, farbe_ = "&#9650;", "#2e9e4f"
        wann = (f"{WOCHENTAGE[besttag.weekday()]} "
                f"{besttag.strftime('%d.%m.')}")
        satz = f"steigt auf <b>{bestwert}</b> am {wann}"
    elif schlecht <= heute_wert - 8:
        pfeil, farbe_ = "&#9660;", "#c0392b"
        satz = f"f&auml;llt in den n&auml;chsten Tagen auf {schlecht}"
    else:
        pfeil, farbe_ = "&#9654;", "#888888"
        satz = "bleibt in den n&auml;chsten Tagen etwa gleich"

    return (f'<div class="trend"><span style="color:{farbe_}">{pfeil}</span> '
            f'{satz}</div>')


def rechne_ereignisse(reihen):
    """Regenereignisse je Zelle - ueber die ganze Reihe, auch Vorhersage."""
    return {ort: finde_ereignisse(reihe) for ort, reihe in reihen.items()}


def schub_hinweis(art, ereignisse, bezugstag):
    """
    Satz zum letzten Regenereignis und zum abgeleiteten Schubfenster.

    Das Fenster ist reine Arithmetik: letztes Ereignis plus die
    Verzugszeit aus der Fachliteratur. Es ist KEINE Wahrscheinlichkeit
    und geht nicht in den Score ein - die Bedingungen bewertet der
    Score getrennt. Liegt das Ereignis lange zurueck, wird das Fenster
    weggelassen, weil es dann nichts mehr aussagt.
    """
    if not ereignisse:
        return "", None

    vergangen = [e for e in ereignisse if e["tag"] <= bezugstag]
    if not vergangen:
        return "", None

    letztes = vergangen[-1]
    alter = (bezugstag - letztes["tag"]).days
    menge = f"{letztes['mm']:.1f}".replace(".", ",")

    def tage(n):
        return "einem Tag" if n == 1 else f"{n} Tagen"

    text = (f"Letztes Regenereignis: {menge} mm vor {tage(alter)}")

    fenster = artenmodul.schubfenster(art, letztes["tag"])
    if fenster is None:
        return text, None

    von, bis = fenster
    tage_bis = (von - bezugstag).days
    vorbei = (bezugstag - bis).days

    if vorbei > 14:
        # Zu lange her - ein Fenster daraus abzuleiten waere Zahlenspiel
        return text, None

    zeitraum = f"{von.strftime('%d.%m.')} bis {bis.strftime('%d.%m.')}"
    if bezugstag < von:
        stand = f"beginnt in {tage(tage_bis)}"
    elif vorbei <= 0:
        stand = "<b>l&auml;uft gerade</b>"
    else:
        stand = f"seit {tage(vorbei)} vorbei"

    text += (f'<br>Schubfenster {zeitraum}, {stand}'
             f'<div class="klein">Aus dem Regenereignis abgeleitet '
             f'(Literaturwert), nicht Teil des Scores.</div>')

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
               namen, boden, bestand, ereignisse, reihe_von, verlauf,
               bezugstage, sichtbar):
    gruppe = folium.FeatureGroup(name=name, show=sichtbar)

    d_lat = RASTER_KM / 111.0 / 2 * 1.02
    d_lon = RASTER_KM / (111.0 * 0.61) / 2 * 1.02

    artname = artenmodul.ARTEN[art]["name"]
    scores = []
    werte = []
    mit_popup = sichtbar or not POPUP_NUR_HEUTE
    sammlung = []
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

        if not mit_popup:
            werte.append((lat, lon, end))
            titel_kurz = namen.get(ort, {}).get("titel", ort)

            if GEOJSON_EBENEN:
                # Nur sammeln - unten wird daraus ein einziges Objekt
                sammlung.append({
                    "type": "Feature",
                    "properties": {"t": f"{titel_kurz}: {end}",
                                   "f": farbe(end)},
                    "geometry": {"type": "Polygon", "coordinates": [[
                        [lon - d_lon, lat - d_lat],
                        [lon + d_lon, lat - d_lat],
                        [lon + d_lon, lat + d_lat],
                        [lon - d_lon, lat + d_lat],
                        [lon - d_lon, lat - d_lat]]]},
                })
            else:
                folium.Rectangle(
                    bounds=[[lat - d_lat, lon - d_lon],
                            [lat + d_lat, lon + d_lon]],
                    tooltip=f"{titel_kurz}: {end}",
                    color=None, weight=0, fill=True,
                    fill_color=farbe(end),
                    fill_opacity=0.0 if weich else 0.8,
                ).add_to(gruppe)
            continue

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

        punkte_zeilen = "".join(
            f"<tr><td>{FELD_NAMEN.get(f, f)}</td>"
            f"<td>{'+' if p > 0 else ''}{p}</td></tr>"
            for f, p in einzeln.items() if p != 0)

        je_art = verlauf.get(ort, {})

        if sichtbar and je_art:
            trend = trend_text(je_art.get(art, []), bezugstage, end)
            andere = sorted(
                ((a, w[0]) for a, w in je_art.items() if w[0] is not None),
                key=lambda x: -x[1])
            zeilen_v = "".join(
                f'<tr{" class=\"aktiv\"" if a == art else ""}>'
                f'<td>{artenmodul.ARTEN[a]["name"]}</td>'
                f'<td style="color:{farbe(w)};font-weight:600">{w}</td></tr>'
                for a, w in andere)
            vergleich_block = (
                f'<details><summary>Andere Arten hier</summary>'
                f'<table class="w">{zeilen_v}</table></details>')
        else:
            trend = ""
            vergleich_block = ""

        schub, _ = schub_hinweis(art, ereignisse.get(ort, []), bezugstag)
        schub_block = (f'<div class="kopf">REGEN</div>'
                       f"<div>{schub}</div>" if schub else "")

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
            if eintrag["wald"]:
                titel = eintrag["wald"]
                if eintrag.get("ortsname"):
                    titel += f" bei {eintrag['ortsname']}"
            elif eintrag.get("ortsname") and eintrag["abstand"]:
                # Ohne Waldnamen: Entfernung zur naechsten Ortschaft,
                # damit klar ist, worauf sich die Angabe bezieht
                abstand = str(eintrag["abstand"]).replace(".", ",")
                titel = f"Wald {abstand} km von {eintrag['ortsname']}"
            else:
                titel = eintrag["titel"]
        else:
            titel = ort

        if bd:
            teile = []
            if bd.get("ph") is not None:
                teile.append(f"pH {zeige(bd['ph'], 1, '', 1)}")
            if bd.get("sand") is not None:
                teile.append(f"Sand {zeige(bd['sand'], 1, ' %', 0)}")
            if bd.get("clay") is not None:
                teile.append(f"Ton {zeige(bd['clay'], 1, ' %', 0)}")
            boden_text = (f"<div>Boden: {' &middot; '.join(teile)}</div>"
                          if teile else "")
        else:
            boden_text = ""

        kopfzeile = [name]
        if hoehe is not None:
            kopfzeile.append(zeige(hoehe, 1, " m", 0))
        kopfzeile.append(f"{lat:.4f}, {lon:.4f}".replace(".", ","))
        kopfzeile.append(ort)

        letzte_messung = None
        for r in reihe_von.get(ort, []):
            if not r.get("prognose") and r["tag"] <= bezugstag:
                if letzte_messung is None or r["tag"] > letzte_messung:
                    letzte_messung = r["tag"]

        if k["prognose_tage"] and letzte_messung is not None:
            stand_hinweis = (f"&middot; gemessen bis "
                             f"{letzte_messung.strftime('%d.%m.')}")
        else:
            stand_hinweis = ""

        # Fussnote: wie viele Tage des Zeitfensters aus der Vorhersage
        # stammen statt aus gemessenen Daten
        if k["prognose_tage"]:
            n = k["prognose_tage"]
            hinweis = (f'<div class="fuss">Von den 14 ausgewerteten Tagen '
                       f'{"stammt 1 Tag" if n == 1 else f"stammen {n} Tage"} '
                       f'aus der Wettervorhersage, der Rest aus gemessenen '
                       f'Daten.</div>')
        else:
            hinweis = ""

        text = f"""
        <div class="pk">
          <div class="titel">{titel}</div>
          <div class="lage">{" &middot; ".join(kopfzeile)}</div>

          <div class="score">{artname} <b>{end}</b><span
            class="max">/100</span></div>
          {trend}
          <div class="formel">Wetter {wetter} &times; Saison
            {komma(saison)} &times; Bestand {komma(wald)} &times; Boden
            {komma(bfaktor)}</div>

          <div class="kopf">STANDORT</div>
          <div>{typ_text}</div>
          {boden_text}

          <div class="kopf">WICHTIGSTE WERTE
            <span class="klein">Stand {bezugstag.strftime('%d.%m.%Y')}
            {stand_hinweis}</span></div>
          <table class="w">
            <tr><td>Bodenfeuchte</td>
                <td>{zeige(k['bf07'], 100, ' %')}</td></tr>
            <tr><td>Bodentemperatur</td>
                <td>{zeige(k['bt07'], 1, ' &deg;C')}</td></tr>
            <tr><td>Wasserbilanz 14 Tage</td>
                <td>{zeige(k['bilanz_14'], 1, ' mm')}</td></tr>
            <tr><td>Niederschlag Tag 4&ndash;14</td>
                <td>{zeige(k['regen_reife'], 1, ' mm')}</td></tr>
          </table>
          {schub_block}

          {vergleich_block}

          <details>
            <summary>Alle Wetterwerte</summary>
            <div class="klein">Bodenwerte als Mittel der letzten 5 Tage,
              Niederschlag und Bilanz ueber die genannten Zeitraeume,
              jeweils bis {bezugstag.strftime('%d.%m.')}</div>
            <table class="w">
              <tr><td>Bodenfeuchte 0&ndash;7 cm</td>
                  <td>{zeige(k['bf07'], 100, ' %')}</td></tr>
              <tr><td>Bodenfeuchte 7&ndash;28 cm</td>
                  <td>{zeige(k['bf728'], 100, ' %')}</td></tr>
              <tr><td>Bodentemperatur</td>
                  <td>{zeige(k['bt07'], 1, ' &deg;C')}</td></tr>
              <tr><td>Lufttemperatur, Mittel 14 Tage</td>
                  <td>{zeige(k['temp'], 1, ' &deg;C')}</td></tr>
              <tr><td>Niederschlag Tag 4&ndash;14</td>
                  <td>{zeige(k['regen_reife'], 1, ' mm')}</td></tr>
              <tr><td>Niederschlag Tag 0&ndash;3</td>
                  <td>{zeige(k['regen_frisch'], 1, ' mm')}</td></tr>
              <tr><td>Regentage von 14</td>
                  <td>{k['regentage']}</td></tr>
              <tr><td>Wasserbilanz 14 Tage</td>
                  <td>{zeige(k['bilanz_14'], 1, ' mm')}</td></tr>
              <tr><td>Wasserbilanz 60 Tage</td>
                  <td>{bilanz60_text}</td></tr>
              <tr><td>Frosttage / k&auml;ltester Boden</td>
                  <td>{k['frosttage']} /
                      {zeige(k['min_boden'], 1, ' &deg;C')}</td></tr>
            </table>
          </details>

          <details>
            <summary>Punkte im Einzelnen</summary>
            <table class="w">{punkte_zeilen}
              <tr class="summe"><td>Summe Wetter</td>
                  <td>{wetter} / 100</td></tr>
            </table>
            {hinweis}
          </details>
        </div>
        """

        werte.append((lat, lon, end))

        if GEOJSON_EBENEN and GEOJSON_HEUTE:
            sammlung.append({
                "type": "Feature",
                "properties": {"t": f"{titel}: {end}", "f": farbe(end),
                               "h": " ".join(text.split())},
                "geometry": {"type": "Polygon", "coordinates": [[
                    [lon - d_lon, lat - d_lat],
                    [lon + d_lon, lat - d_lat],
                    [lon + d_lon, lat + d_lat],
                    [lon - d_lon, lat + d_lat],
                    [lon - d_lon, lat - d_lat]]]},
            })
        else:
            folium.Rectangle(
                bounds=[[lat - d_lat, lon - d_lon],
                        [lat + d_lat, lon + d_lon]],
                popup=folium.Popup(text, max_width=280),
                tooltip=f"{titel}: {end}",
                color=None, weight=0, fill=True,
                fill_color=farbe(end),
                fill_opacity=0.0 if weich else 0.8,
            ).add_to(gruppe)

    if sammlung:
        deckkraft = 0.0 if weich else 0.8
        hat_popup = "h" in sammlung[0]["properties"]

        folium.GeoJson(
            {"type": "FeatureCollection", "features": sammlung},
            style_function=lambda x, d=deckkraft: {
                "fillColor": x["properties"]["f"],
                "color": x["properties"]["f"],
                "weight": 0, "opacity": 0, "fill": True,
                "fillOpacity": d},
            tooltip=folium.GeoJsonTooltip(fields=["t"], labels=False,
                                          sticky=False),
            popup=(folium.GeoJsonPopup(fields=["h"], labels=False,
                                       max_width=300)
                   if hat_popup else None),
            smooth_factor=0,
        ).add_to(gruppe)

    if not scores:
        return None, 0, 0

    # Weiches Bild UNTER die Klickflaechen legen
    if weich:
        stil = "d" if DUNKEL else "h"
        dateiname = (f"{art}_t{(bezugstag - date.today()).days}"
                     f"_{stil}.png")
        _tb = time.time()
        pfad, grenzen = weichzeichnen.erzeuge(werte, dateiname,
                                              dunkel=DUNKEL)
        if ZEITMESSUNG:
            BILDZEIT[0] += time.time() - _tb
        if pfad:
            bild_ebene(pfad, grenzen, 1).add_to(gruppe)

    return gruppe, len(scores), sum(scores) / len(scores)


def reliefebenen(karte):
    """Feinkarten aus dem 1-m-Hoehenmodell, ein Paar je Gebiet."""
    gebiete = []

    if os.path.exists(RELIEF_GRENZEN_DATEI):
        with open(RELIEF_GRENZEN_DATEI, "r", encoding="utf-8") as f:
            for z in csv.DictReader(f):
                try:
                    gebiete.append((
                        z["gebiet"], z.get("titel") or z["gebiet"],
                        [[float(z["sued"]), float(z["west"])],
                         [float(z["nord"]), float(z["ost"])]]))
                except (ValueError, KeyError):
                    continue
    elif os.path.exists(RELIEF_ALT):
        # Fassung mit nur einem Gebiet
        try:
            with open(RELIEF_ALT, "r", encoding="utf-8") as f:
                s, w, n, o = [float(t) for t in f.read().strip().split(",")]
            gebiete.append(("", "Gelaende", [[s, w], [n, o]]))
        except Exception:
            pass

    # Gebietsweite Uebersicht aus relief_weit.py
    if os.path.exists(RELIEF_WEIT):
        try:
            with open(RELIEF_WEIT, "r", encoding="utf-8") as f:
                s, w, n, o = [float(t) for t in f.read().strip().split(",")]
            gebiete.append(("weit", "ganzes Gebiet, 20 m",
                            [[s, w], [n, o]]))
        except Exception:
            pass

    if not gebiete:
        return 0

    anzahl = 0
    fehlend = 0

    for schluessel, titel, grenzen in gebiete:
        teil = f"_{schluessel}" if schluessel else ""
        for art, beschriftung in [
            ("feuchte", f"Feuchte Senken: {titel}"),
            ("schummerung", f"Gelaendeschummerung: {titel}"),
        ]:
            datei = f"bilder/relief{teil}_{art}.png"
            if not os.path.exists(datei):
                fehlend += 1
                continue
            gruppe = folium.FeatureGroup(name=beschriftung, show=False)
            bild_ebene(datei, grenzen, 3).add_to(gruppe)
            gruppe.add_to(karte)
            anzahl += 1

    if fehlend and not anzahl:
        print("  Reliefbilder fehlen - relief.py nochmal laufen lassen.")

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
        bild_ebene(pfad, grenzen, 2).add_to(gruppe)
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
      .leaflet-popup-content {{ margin: 10px 12px; }}
      .pk {{ font: 12px/1.45 system-ui, sans-serif;
             min-width: 250px; max-width: 300px;
             max-height: 58vh; overflow-y: auto;
             overscroll-behavior: contain;
             padding-right: 4px; }}
      .pk details {{ margin-top: 8px; }}
      .pk summary {{ cursor: pointer; font-size: 10.5px;
                     font-weight: 700; letter-spacing: .06em;
                     color: {THEMA['akzent']};
                     border-top: 1px solid {THEMA['linie']};
                     padding-top: 6px; text-transform: uppercase;
                     list-style: none; }}
      .pk summary::-webkit-details-marker {{ display: none; }}
      .pk summary::before {{ content: "\25b8 "; }}
      .pk details[open] summary::before {{ content: "\25be "; }}
      .pk .titel {{ font-size: 14px; font-weight: 600;
                    margin-bottom: 1px; }}
      .pk .lage {{ color: {THEMA['text_leise']}; font-size: 10.5px;
                   margin-bottom: 8px; }}
      .pk .score {{ font-size: 13px; }}
      .pk .score b {{ font-size: 19px; color: {THEMA['akzent']};
                      margin-left: 4px; }}
      .pk .score .max {{ font-size: 11px;
                         color: {THEMA['text_leise']}; }}
      .pk .trend {{ margin: 3px 0 2px; font-size: 12px; }}
      .pk .formel {{ color: {THEMA['text_leise']}; font-size: 10.5px;
                     margin-bottom: 2px; }}
      .pk .kopf {{ margin: 9px 0 3px; font-size: 9.5px; font-weight: 700;
                   letter-spacing: .08em; color: {THEMA['text_leise']};
                   border-top: 1px solid {THEMA['linie']};
                   padding-top: 5px; }}
      .pk table.w {{ width: 100%; border-collapse: collapse; }}
      .pk table.w td {{ padding: 1px 0; border: 0; font-size: 12px; }}
      .pk table.w td:last-child {{ text-align: right;
                                   font-variant-numeric: tabular-nums;
                                   white-space: nowrap;
                                   padding-left: 12px; }}
      .pk tr.aktiv td {{ font-weight: 700; }}
      .pk tr.summe td {{ border-top: 1px solid {THEMA['linie']};
                         font-weight: 600; padding-top: 3px; }}
      .pk .klein {{ font-size: 10px; font-weight: 400;
                    letter-spacing: 0; text-transform: none;
                    color: {THEMA['text_leise']}; }}
      .pk .fuss {{ margin-top: 7px; font-size: 10.5px;
                   color: {THEMA['text_leise']}; font-style: italic; }}
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
               bestand, ereignisse, reihen, funde, verlauf, bezugstage,
               vorrat):
    zeit = {"ebenen": 0.0, "bilder": 0.0, "wald": 0.0, "relief": 0.0,
            "funde": 0.0, "schutz": 0.0, "speichern": 0.0}
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
        _t = time.time()
        gruppe, anzahl, schnitt = baue_ebene(
            art, bezugstag, tagname(tag), punkte, cache,
            waldtypen, hoehen, namen, boden, bestand, ereignisse,
            reihen, verlauf, bezugstage, i == 0)
        zeit["ebenen"] += time.time() - _t
        if gruppe is None:
            continue
        gruppe.add_to(karte)
        if i == 0:
            schnitt_heute = schnitt

    _t = time.time()
    anzahl_funde = 0
    if FUNDE_ZEIGEN:
        gruppe, anzahl_funde = fund_ebene(art, date.today(), funde)
        if gruppe is not None:
            gruppe.add_to(karte)
    zeit["funde"] = time.time() - _t

    _t = time.time()
    waldflaechen(karte, vorrat)
    zeit["wald"] = time.time() - _t

    _t = time.time()
    vorrat["relief"] = reliefebenen(karte)
    zeit["relief"] = time.time() - _t

    _t = time.time()
    schutzgebiete(karte)
    zeit["schutz"] = time.time() - _t
    folium.LayerControl(collapsed=True).add_to(karte)
    legende(karte, art, schnitt_heute)

    dateiname = f"karte_{art}.html"
    _t = time.time()
    karte.save(dateiname)
    zeit["speichern"] = time.time() - _t

    if ZEITMESSUNG:
        gross = os.path.getsize(dateiname) / 1024 / 1024
        teile = "  ".join(f"{n} {round(w, 1)}" for n, w in zeit.items()
                          if w >= 0.05)
        print(f"      [{round(gross, 1)} MB]  {teile}")

    return dateiname, schnitt_heute, anzahl_funde


def schreibe_bestenliste(scores_heute, namen, bestand, boden, punkte,
                         verlauf=None, bezugstage=None,
                         dateiname="beste.html"):
    """
    Rangliste der besten Zellen je Art.

    Gruene Flaechen auf einer Karte zu suchen ist muehsam - eine Liste
    mit Namen beantwortet die eigentliche Frage schneller.
    """
    T = THEMA
    bloecke = []

    for art, einstellung in artenmodul.ARTEN.items():
        # Nicht jede Zelle hat fuer jede Art einen Wert - etwa wenn
        # die Kennwerte fehlen. Fehlende einfach ueberspringen.
        liste = sorted(((ort, w[art]) for ort, w in scores_heute.items()
                        if w.get(art) is not None),
                       key=lambda x: -x[1])[:12]
        if not liste or liste[0][1] < 1:
            continue

        zeilen = []
        for rang, (ort, wert) in enumerate(liste, start=1):
            eintrag = namen.get(ort, {})
            titel = eintrag.get("titel") or ort
            lat, lon = punkte[ort]
            bst = bestand.get(ort) or {}
            anteile = bst.get("anteile") or {}
            oben = sorted(anteile.items(), key=lambda x: -x[1])[:2]
            bestandstext = ", ".join(
                f"{artenmodul.BAUMART_NAMEN.get(a, a)} {round(w*100)} %"
                for a, w in oben)

            pfeil = ""
            if verlauf and bezugstage and ort in verlauf:
                liste = verlauf[ort].get(art, [])
                kuenftig = [w for w in liste[1:] if w is not None]
                if kuenftig:
                    if max(kuenftig) >= wert + 8:
                        pfeil = ('<span style="color:#2e9e4f" '
                                 'title="wird besser">&#9650;</span>')
                    elif min(kuenftig) <= wert - 8:
                        pfeil = ('<span style="color:#c0392b" '
                                 'title="wird schlechter">&#9660;</span>')

            zeilen.append(
                f'<tr><td class="rang">{rang}</td>'
                f'<td><b>{titel}</b><div class="klein">{bestandstext}</div></td>'
                f'<td class="wert" style="color:{farbe(wert)}">{wert}'
                f'<div class="pfeil">{pfeil}</div></td>'
                f'<td><a href="https://www.openstreetmap.org/'
                f'?mlat={lat:.5f}&amp;mlon={lon:.5f}#map=14/{lat:.5f}/{lon:.5f}"'
                f' target="_blank" title="In OpenStreetMap oeffnen">Karte</a>'
                f'<div class="klein">{lat:.4f}, {lon:.4f}</div></td></tr>')

        saison = round(artenmodul.saison_rohwert(einstellung, date.today()), 2)
        bloecke.append(
            f'<section><h2>{einstellung["name"]}'
            f'<span class="saison">Saison {saison}</span></h2>'
            f'<table>{"".join(zeilen)}</table></section>')

    html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Beste Gebiete</title>
<style>
  body {{ font: 14px/1.5 system-ui, sans-serif; margin: 0;
          padding: 16px 18px 60px; background: {T['grund']};
          color: {T['text']}; }}
  h1 {{ font-size: 18px; margin: 0 0 4px; }}
  .stand {{ color: {T['text_leise']}; font-size: 12px;
            margin-bottom: 18px; }}
  section {{ margin-bottom: 26px; }}
  h2 {{ font-size: 15px; margin: 0 0 6px;
        border-bottom: 1px solid {T['linie']}; padding-bottom: 4px; }}
  .saison {{ float: right; font-weight: 400; font-size: 12px;
             color: {T['text_leise']}; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 5px 6px; border-bottom: 1px solid {T['linie']};
        vertical-align: top; }}
  td.rang {{ width: 26px; color: {T['text_leise']};
             font-variant-numeric: tabular-nums; }}
  td.wert {{ text-align: right; font-size: 17px; font-weight: 700;
             width: 48px; font-variant-numeric: tabular-nums; }}
  .klein {{ font-size: 11px; color: {T['text_leise']}; }}
  .pfeil {{ font-size: 11px; line-height: 1; }}
  a {{ color: {T['akzent']}; }}
  @media (max-width: 700px) {{
    body {{ padding: 12px 10px 70px; font-size: 15px;
            -webkit-text-size-adjust: 100%; }}
    td {{ padding: 9px 4px; }}
    td.wert {{ font-size: 19px; }}
    a {{ display: inline-block; padding: 6px 0; }}
  }}
</style></head><body>
<h1>Beste Gebiete heute</h1>
<div class="stand">Stand {date.today().strftime('%d.%m.%Y')} &middot;
je Art die zw&ouml;lf h&ouml;chsten Zellen &middot;
Zahlen unter etwa 40 bedeuten geringe Aussichten</div>
{"".join(bloecke)}
</body></html>
"""
    with open(dateiname, "w", encoding="utf-8") as f:
        f.write(html)
    return dateiname


def schreibe_index(eintraege):
    """Rahmenseite mit Artenumschaltern."""
    T = THEMA
    knoepfe = "".join(
        f'<button class="art" data-datei="{datei}" data-i="{i}">'
        f'{name}<span class="wert"><b>{round(schnitt)}</b>/100</span>'
        f'</button>'
        for i, (name, datei, schnitt) in enumerate(eintraege))

    knoepfe += ('<button class="art liste" data-datei="beste.html">'
                '&#9733; Beste Gebiete</button>')
    knoepfe += ('<button class="art info" data-datei="info.html">'
                '? Wie wird gerechnet</button>')

    erste = eintraege[0][1] if eintraege else ""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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

  /* Auf dem Telefon: eine Zeile zum Wischen statt vieler Reihen.
     Sonst frisst die Leiste die halbe Bildschirmhoehe. */
  @media (max-width: 700px) {{
    body {{ -webkit-text-size-adjust: 100%; }}
    header {{ padding: 8px 10px; }}
    h1 {{ font-size: 14px; margin-bottom: 6px; }}
    .leiste {{ flex-wrap: nowrap; overflow-x: auto;
               scrollbar-width: none;
               -webkit-overflow-scrolling: touch;
               padding-bottom: 2px; }}
    .leiste::-webkit-scrollbar {{ display: none; }}
    button.art {{ flex: 0 0 auto; padding: 9px 12px; font-size: 13px;
                  min-height: 40px; }}
    button.art.liste, button.art.info {{ margin-left: 0; }}
  }}
  button.art {{ border: 1px solid {T['linie']};
                background: {T['grund']}; color: {T['text']};
                padding: 7px 12px; border-radius: 20px; cursor: pointer;
                font-size: 14px; display: flex; align-items: baseline;
                gap: 6px; }}
  button.art:hover {{ border-color: {T['akzent']}; }}
  button.art.aktiv {{ background: {T['akzent']};
                      border-color: {T['akzent']};
                      color: {T['flaeche']}; }}
  button.art.liste {{ margin-left: auto; background: {T['flaeche']}; }}
  button.art.info {{
                     background: {T['flaeche']};
                     border-style: dashed; }}
  button.art.info.aktiv {{ background: #455a64; border-color: #455a64; }}
  button.art .wert {{ font-size: 10px; opacity: .65;
                      margin-left: 2px; }}
  button.art .wert b {{ font-size: 14px; font-weight: 700;
                        opacity: 1; }}
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
            stand = "l&auml;uft gerade"
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
    if POPUP_NUR_HEUTE:
        print("Ausfuehrliche Popups nur auf der Heute-Ebene")

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

    verlauf = alle_arten_verlauf(cache, bezugstage, punkte, waldtypen,
                                 boden, bestand)
    scores_heute = {ort: {a: w[0] for a, w in je.items() if w[0] is not None}
                    for ort, je in verlauf.items()}

    vorrat = {}
    eintraege = []
    for art in liste:
        datei, schnitt, nfunde = baue_karte(art, punkte, cache, waldtypen,
                                            hoehen, namen, boden, bestand,
                                            ereignisse, reihen, funde,
                                            verlauf, bezugstage, vorrat)
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

    listendatei = schreibe_bestenliste(scores_heute, namen, bestand,
                                       boden, punkte, verlauf,
                                       bezugstage)
    print(f"  Bestenliste  -> {listendatei}")

    infodatei = infoseite.schreibe(dunkel=DUNKEL)
    print(f"\n  Erklaerseite -> {infodatei}")

    schreibe_index(eintraege)

    if ZEITMESSUNG:
        print(f"\nBilderzeugung insgesamt: {round(BILDZEIT[0], 1)} s")

    print(f"\nFertig. {INDEX} im Browser oeffnen.")
    if eintraege:
        print(f"Beste Art heute: {eintraege[0][0]} "
              f"(Schnitt {round(eintraege[0][2])})")


# Nur ausfuehren, wenn direkt gestartet - dieses Modul
# wird von anderen Skripten importiert, und dann darf
# nichts von selbst losrechnen.
if __name__ == "__main__":
    main()