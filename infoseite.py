"""
Erzeugt info.html - die Erklaerseite zur Karte.

Der Inhalt wird direkt aus arten.py gelesen. Wenn du dort Schwellen
aenderst, steht beim naechsten Kartenlauf automatisch der neue Wert
auf der Seite. Keine doppelte Pflege.
"""
import arten as artenmodul
import farben

MONATSNAMEN = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

FELD_INFO = {
    "bilanz_14": ("Wasserbilanz 14 Tage", 1, "mm"),
    "bilanz_60": ("Wasserbilanz 60 Tage", 1, "mm"),
    "bf07": ("Bodenfeuchte 0-7 cm", 100, "%"),
    "bt07": ("Bodentemperatur 0-7 cm", 1, "&deg;C"),
    "regen_reife": ("Niederschlag Tag 4-14", 1, "mm"),
    "regentage": ("Regentage von 14", 1, ""),
    "temp": ("Lufttemperatur, Mittel 14 Tage", 1, "&deg;C"),
}


def bereich(von, bis, faktor, einheit):
    def z(w):
        w = w * faktor
        return str(int(w)) if abs(w - int(w)) < 0.05 else str(round(w, 1))

    if von is None and bis is None:
        return "alle Werte"
    if von is None:
        return f"bis {z(bis)} {einheit}"
    if bis is None:
        return f"ab {z(von)} {einheit}"
    return f"{z(von)} &ndash; {z(bis)} {einheit}"


def baender_tabelle(einstellung):
    zeilen = []
    for feld in artenmodul.MOEGLICHE_FELDER:
        baender = einstellung.get(feld)
        if not baender:
            continue
        titel, faktor, einheit = FELD_INFO.get(feld, (feld, 1, ""))
        hoechst = max(b[2] for b in baender)

        erste = True
        for von, bis, punkte in sorted(baender, key=lambda b: -b[2]):
            spalte1 = (f'<td rowspan="{len(baender)}" class="gruppe">'
                       f'{titel}<br><small>max. {hoechst} Punkte</small></td>'
                       if erste else "")
            zeilen.append(
                f"<tr>{spalte1}"
                f"<td>{bereich(von, bis, faktor, einheit)}</td>"
                f'<td class="p">{punkte}</td></tr>')
            erste = False

    return ("<table class='baender'><tr><th>Groesse</th><th>Bereich</th>"
            "<th>Punkte</th></tr>" + "".join(zeilen) + "</table>")


def saison_balken(saison, T):
    zellen = []
    for m in range(1, 13):
        w = saison.get(m, 0.0)
        hoehe = max(2, round(w * 46))
        farbe = (T["akzent"] if w >= 0.7
                 else "#8bc34a" if w >= 0.35 else T["linie"])
        zellen.append(
            f'<div class="mon"><div class="saeule" style="height:{hoehe}px;'
            f'background:{farbe}"></div>'
            f'<div class="mname">{MONATSNAMEN[m-1]}</div>'
            f'<div class="mwert">{w:.2f}</div></div>')
    return f'<div class="saison">{"".join(zellen)}</div>'


def baumart_tabelle(einstellung):
    """Gewichte je Baumart, absteigend."""
    gewichte = einstellung.get("baumarten")
    if not gewichte:
        return None
    teile = []
    for art, w in sorted(gewichte.items(), key=lambda x: -x[1]):
        name = artenmodul.BAUMART_NAMEN.get(art, art)
        stark = "" if w < 0.8 else " style='font-weight:600'"
        teile.append(f"<span class='chip'{stark}>{name} &times;{w}</span>")
    return " ".join(teile)


def wald_tabelle(waldtyp):
    namen = {"laub": "Laubwald", "nadel": "Nadelwald", "misch": "Mischwald",
             "bruch": "Bruch-/Feuchtwald", "unbekannt": "unbekannt"}
    teile = [f"<span class='chip'>{namen.get(k, k)} &times;{v}</span>"
             for k, v in sorted(waldtyp.items(), key=lambda x: -x[1])]
    return " ".join(teile)


def artenblock(art, einstellung, T):
    abzug = einstellung.get("abzug_faktor", 1.0)
    hinweis = ""
    if abzug != 1.0:
        hinweis = (f'<p class="hinweis">Holzbewohner: Abzuege fuer '
                   f'Bodentrockenheit wirken nur zu {int(abzug*100)} %, '
                   f'weil diese Art ihr Wasser aus dem Stamm zieht.</p>')

    return f"""
    <section class="art" id="{art}">
      <h3>{einstellung['name']}</h3>
      <p class="lat">{einstellung['gbif']}</p>
      {hinweis}
      <h4>Saisonfaktor</h4>
      {saison_balken(einstellung["saison"], T)}
      <h4>Baumarten-Faktor</h4>
      <p>{baumart_tabelle(einstellung) or wald_tabelle(einstellung["waldtyp"])}</p>
      <h4>Wetterpunkte</h4>
      {baender_tabelle(einstellung)}
    </section>
    """


def schreibe(dateiname="info.html", dunkel=False):
    T = farben.thema(dunkel)
    bloecke = "".join(artenblock(a, e, farben.thema(dunkel))
                      for a, e in artenmodul.ARTEN.items())
    sprung = " &middot; ".join(
        f'<a href="#{a}">{e["name"]}</a>'
        for a, e in artenmodul.ARTEN.items())
    staerke = artenmodul.SAISON_STAERKE

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wie die Pilzkarte rechnet</title>
<style>
  body {{ font: 15px/1.6 system-ui, sans-serif; color: {T['text']};
          background: {T['grund']};
          max-width: 860px; margin: 0 auto; padding: 24px 20px 80px; }}
  h1 {{ font-size: 24px; margin: 0 0 4px; }}
  h2 {{ font-size: 19px; margin: 34px 0 10px; padding-top: 14px;
        border-top: 2px solid {T['linie']}; }}
  h3 {{ font-size: 17px; margin: 26px 0 2px; }}
  h4 {{ font-size: 13px; margin: 16px 0 6px; color: {T['text_leise']};
        text-transform: uppercase; letter-spacing: .04em; }}
  p.lat {{ margin: 0 0 8px; color: {T['text_leise']};
           font-style: italic; }}
  .formel {{ background: {T['flaeche']};
             border-left: 4px solid {T['akzent']};
             padding: 12px 16px; margin: 14px 0; font-size: 16px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0 4px; }}
  th, td {{ text-align: left; padding: 5px 9px;
            border-bottom: 1px solid {T['linie']};
            font-size: 14px; }}
  th {{ background: {T['flaeche']}; font-size: 12px;
        text-transform: uppercase;
        letter-spacing: .04em; color: {T['text_leise']}; }}
  td.p {{ text-align: right; font-variant-numeric: tabular-nums;
          width: 70px; }}
  td.gruppe {{ background: {T['flaeche']}; width: 210px;
               vertical-align: top; }}
  td.gruppe small {{ color: {T['text_leise']}; }}
  .saison {{ display: flex; gap: 3px; align-items: flex-end; margin: 6px 0; }}
  .mon {{ flex: 1; text-align: center; }}
  .saeule {{ width: 100%; border-radius: 2px 2px 0 0; }}
  .mname {{ font-size: 11px; color: {T['text_leise']}; margin-top: 3px; }}
  .mwert {{ font-size: 10px; color: {T['text_leise']}; }}
  .chip {{ display: inline-block; background: {T['flaeche']};
           border-radius: 12px;
           padding: 2px 10px; margin: 2px 2px 2px 0; font-size: 13px; }}
  .hinweis {{ background: {T['flaeche']};
              border-left: 4px solid #f0b429;
              padding: 8px 14px; font-size: 14px; }}
  .warnung {{ background: {T['flaeche']};
              border-left: 4px solid {T['schutz_streng']};
              padding: 12px 16px; margin: 14px 0; }}
  section.art {{ border-bottom: 1px solid {T['linie']};
                 padding-bottom: 18px; }}
  nav {{ font-size: 14px; background: {T['flaeche']}; padding: 10px 14px;
         border-radius: 6px; }}
  a {{ color: {T['akzent']}; }}
  @media (max-width: 700px) {{
    body {{ padding: 14px 12px 70px; -webkit-text-size-adjust: 100%; }}
    table {{ font-size: 13px; }}
    th, td {{ padding: 4px 5px; }}
    td.gruppe {{ width: 130px; }}
    .saison {{ gap: 2px; }}
    .mname, .mwert {{ font-size: 9px; }}
    nav {{ line-height: 2.2; }}
  }}
  ul {{ padding-left: 22px; }}
  li {{ margin: 4px 0; }}
</style>
</head>
<body>

<h1>Wie die Pilzkarte rechnet</h1>
<p class="lat">Automatisch aus arten.py erzeugt &ndash; die Zahlen unten sind
genau die, mit denen die Karte gerade arbeitet.</p>

<h2>Was die Karte zeigt</h2>
<p>Jede Zelle ist 2 &times; 2 km gross und liegt im Wald. Die Farbe sagt,
wie gut die <b>Bedingungen</b> fuer eine Pilzart gerade sind &ndash; nicht,
ob dort tatsaechlich Pilze stehen. Sie beantwortet die Frage
&bdquo;wohin lohnt die Anfahrt&ldquo;, nicht &bdquo;wo genau im Wald&ldquo;.</p>

<div class="formel">
  <b>Endscore = Wetterpunkte &times; Saisonfaktor &times; Waldtypfaktor</b><br>
  <small>Wetterpunkte 0&ndash;100 &middot; beide Faktoren zwischen 0 und 1</small>
</div>

<p>Die Saison wird mit der Staerke <b>{staerke}</b> gewichtet: Ein Monatswert
von 0 senkt den Score also nicht auf null, sondern auf
{round((1-staerke)*100)} % &ndash; ein Restwert bleibt, weil auch ausserhalb
der Hauptzeit einzelne Funde vorkommen.</p>

<h2>Woher die Daten kommen</h2>
<ul>
  <li><b>Wetter:</b> Open-Meteo. Vergangenheit aus dem ERA5-Archiv
      (ca. 11 km Raster), der taegliche Zulauf aus dem DWD-Modell icon_d2
      (2 km) fuer Regen und Lufttemperatur. Bodenwerte und Verdunstung
      kommen immer aus dem Standardmodell, weil icon_d2 sie nicht liefert.</li>
  <li><b>Baumarten:</b> Thuenen-Atlas, Karte der dominanten Baumarten,
      10 m Aufloesung, elf Klassen.</li>
  <li><b>Waldflaechen:</b> OpenStreetMap ueber die Overpass-API. Ueber die
      Waldpolygone wurde ein 2-km-Raster gelegt; eine Zelle zaehlt als Wald,
      wenn ihr Mittelpunkt oder eine ihrer vier Ecken im Wald liegt.</li>
  <li><b>Schutzgebiete:</b> OpenStreetMap. Rot = Naturschutzgebiet,
      Sammeln verboten. Blau = Landschaftsschutz, meist erlaubt.</li>
  <li><b>Hoehenlage:</b> Open-Meteo Elevation API.</li>
  <li><b>Fundmeldungen zur Kalibrierung:</b> GBIF, ueberwiegend
      Citizen-Science-Beobachtungen der letzten Jahre.</li>
</ul>

<h2>Die Kenngroessen</h2>
<p>Alle beziehen sich auf einen Stichtag &ndash; heute oder einen der
Prognosetage.</p>
<table>
  <tr><th>Groesse</th><th>Berechnung</th></tr>
  <tr><td>Bodenfeuchte</td><td>Mittel der letzten 5 Tage, Volumenanteil
      in der Schicht 0&ndash;7 cm</td></tr>
  <tr><td>Bodentemperatur</td><td>Mittel der letzten 5 Tage, 0&ndash;7 cm</td></tr>
  <tr><td>Niederschlag Tag 4&ndash;14</td><td>Summe des Regens, der 4 bis 14
      Tage vor dem Stichtag fiel</td></tr>
  <tr><td>Niederschlag Tag 0&ndash;3</td><td>Summe der letzten vier Tage</td></tr>
  <tr><td>Regentage</td><td>Anzahl Tage mit mindestens 1 mm, von 14</td></tr>
  <tr><td>Tage seit Regen</td><td>Abstand zum letzten Tag mit mindestens
      3 mm</td></tr>
  <tr><td>Wasserbilanz</td><td>Regen minus Verdunstung, ueber 14 und 60
      Tage. Erklaert, warum 20 mm im heissen August weniger wert sind als
      im kuehlen Oktober. <b>Der staerkste Einzelwert</b> in der
      Kalibrierung.</td></tr>
  <tr><td>Frosttage</td><td>Tage mit Lufttemperatur unter 0 &deg;C in den
      letzten 14, dazu die tiefste Bodentemperatur</td></tr>
</table>

<h2>Abzuege</h2>
<table>
  <tr><th>Bedingung</th><th>Abzug</th><th>Grundlage</th></tr>
  <tr><td>Bodenfeuchte unter 17 % und kein frischer Regen</td>
      <td class="p">-15</td><td>ausgetrockneter Boden</td></tr>
  <tr><td>Ueber 14 Tage ohne Regen von mindestens 3 mm</td>
      <td class="p">-12</td><td>gemessen: Auswahlverhaeltnis 0,14</td></tr>
  <tr><td>Wasserbilanz der letzten 60 Tage unter -120 mm</td>
      <td class="p">-10</td><td>Trockensommer wirkt nach</td></tr>
  <tr><td>Ein bis zwei Frosttage in den letzten 14</td>
      <td class="p">-15 bis -20</td>
      <td>gemessen: Auswahlverhaeltnis faellt auf 0,0 bis 0,7</td></tr>
  <tr><td>Drei Frosttage oder Bodentemperatur unter -1 &deg;C</td>
      <td class="p">-35 bis -45</td>
      <td>gemessen: 0,0 bis 0,3</td></tr>
</table>

<p>Der Frostabzug ist an Fundmeldungen aus Oktober bis Dezember
gemessen. Wichtig dabei: Das Signal bleibt bestehen, wenn man
<i>nur den November</i> betrachtet - es ist also nicht bloss der
Saisonverlauf, sondern Frost selbst.</p>

<div class="hinweis">Eine Annahme wurde dabei widerlegt: Marone und
Birkenpilz galten als frosthart. Gemessen reagieren sie so empfindlich
wie die anderen - die Marone faellt im November schon bei ein bis zwei
Frosttagen auf 0,00. Wirklich unbeeindruckt ist nur der
Schwefelporling (1,74 bei leichtem Frost), was zu einem Holzbewohner
passt: Sein Fruchtkoerper steht geschuetzter und haelt wochenlang.</div>

<h2>Wie die Schwellen zustande kamen</h2>
<p>Fundmeldungen allein sagen wenig. Dass Steinpilze bei 31 % Bodenfeuchte
gefunden werden, ist nur dann interessant, wenn der Boden nicht ohnehin
meistens so feucht ist. Deshalb werden die Fundbedingungen gegen eine
<b>Hintergrundstichprobe</b> gehalten: mehrere zehntausend normale Tage an
zufaelligen Waldpunkten seit 2019.</p>

<div class="formel">
  Auswahlverhaeltnis =
  Anteil der Funde in einem Wertebereich &divide;
  Anteil der normalen Tage im selben Bereich
</div>

<p>1,0 bedeutet: kein Signal. 2,0 bedeutet: doppelt so haeufig wie zufaellig
zu erwarten. Verglichen wird nur innerhalb derselben Monate &ndash; sonst
misst man den Herbst und nicht den Pilz.</p>

<p>Grundlage sind 2819 Fundmeldungen aus GBIF gegen rund 47.000
Vergleichstage an 35 zufaelligen Waldpunkten seit 2019. Alle
Wetterbaender und Saisonfaktoren unten sind daraus abgeleitet.</p>

<p>Die <b>Bodenfaktoren</b> (pH und Tonanteil) sind ebenfalls gemessen:
468 Fundorte gegen 977 Waldpunkte im selben Gebiet. Der Tonanteil ist
dabei das staerkste Bodensignal - beim Schwefelporling reicht das
Auswahlverhaeltnis von 0,04 bei unter 12 % Ton bis 2,89 bei ueber 20 %.
Ton haelt Wasser, das ist der Mechanismus dahinter.</p>

<div class="hinweis">Vorbehalt: Tonreiche Boeden liegen in dieser
Region im Sueden, wo auch mehr Menschen melden. Ein Teil des Effekts
koennte Beobachterdichte sein. Dagegen spricht, dass der Birkenpilz
genau umgekehrt reagiert - bei reiner Sammlerdichte muessten alle
Arten in dieselbe Richtung zeigen.</div>

<p>Noch <b>geschaetzt</b> sind die Baumartenfaktoren, die
Frostempfindlichkeit je Art sowie die Bodenwerte von Pfifferling und
Sommersteinpilz - fuer diese beiden lagen nur je zehn Fundorte im
Vergleichsgebiet.</p>

<h2>Baumarten</h2>
<p>Fuer jede Rasterzelle sind die Anteile der Baumarten bekannt -
aus der Karte der dominanten Baumarten des Thuenen-Instituts
(Blickensdoerfer u.a. 2024, Sentinel-1 und -2 kombiniert mit der
Bundeswaldinventur, 10 m Aufloesung, Stand 2017/2018). Je Zelle
wurden rund 37.000 Bildpunkte ausgezaehlt.</p>

<p>Der Faktor ist ein <b>gewichteter Mittelwert</b>, keine Kategorie.
Eine Zelle mit 60 % Eiche, 30 % Kiefer und 10 % Birke ergibt beim
Schwefelporling 0,6&times;1,0 + 0,3&times;0,1 + 0,1&times;0,3 = 0,66.
Damit zaehlt auch eine Beimischung: Ein Kiefernforst mit 20 % Birke
ist fuer den Birkenpilz brauchbar, obwohl die Hauptbaumart Kiefer ist.</p>

<p>Der <b>Waldanteil</b> der Zelle wirkt nur noch schwach - und das
hat einen Grund, der nicht auf der Hand liegt.</p>

<p>Der Waldanteil sagt, wie wahrscheinlich eine <i>zufaellige</i>
Stelle in der Zelle Wald ist. Das beantwortet die Frage, wie viele
Pilze in der ganzen Zelle stehen. Ein Sammler fragt aber etwas
anderes: <i>Wenn ich in dem Waldstueck dort suche - wie stehen meine
Chancen?</i> Dafuer ist gleichgueltig, ob drumherum Acker liegt.
Niemand sucht auf dem Acker.</p>

<p>Eine starke Daempfung wuerde also kleine Waelder bestrafen, ohne
dass es dem Sammler etwas sagt. Was bleibt, ist zweierlei: Ein
kleines Waldstueck bietet weniger Flaeche zum Absuchen. Und
unterhalb von etwa vier Prozent Waldanteil werden Baumarten- und
Bodenangaben unsicher, weil sie aus sehr wenigen Bildpunkten
stammen.</p>

<div class="hinweis">Grundsaetzliche Grenze: Die Karte zeigt nur
Zellen, in denen OpenStreetMap Wald verzeichnet. Wiesen, Parks,
Streuobstwiesen, Hecken und Alleen fehlen ganz - obwohl gerade dort
Parasol und Schwefelporling haeufig stehen.</div>

<p>Die Gewichte stammen aus der Pilzliteratur und wurden an
Fundmeldungen geprueft. Dabei zeigte sich ein Fallstrick: Ein erster
Vergleich der Baumarten an Fundorten mit denen in der Region ergab,
dass <i>alle</i> Arten Laubwald bevorzugen und Kiefer meiden - auch
die Marone, die ein Nadelwaldpilz ist. Der Grund war nicht Biologie,
sondern <b>wo Menschen unterwegs sind</b>:</p>

<table>
  <tr><th>Baumart</th><th>Anteil an der Waldflaeche</th>
      <th>Anteil an den Pilzmeldeorten</th></tr>
  <tr><td>Kiefer</td><td>45,3 %</td><td>11,7 %</td></tr>
  <tr><td>Eiche</td><td>21,4 %</td><td>43,6 %</td></tr>
  <tr><td>Buche</td><td>9,5 %</td><td>26,5 %</td></tr>
</table>

<p>Rechnet man gegen die Meldeorte statt gegen die Flaeche, bleibt ein
schwaecheres, aber sinnvolles Bild: Steinpilz bei Fichte und Buche,
Schwefelporling bei Eiche, Erle und Weide, Marone bei Nadelholz.</p>

<div class="hinweis">Die Zahl der auswertbaren Fundorte je Art liegt
nur zwischen 43 und 86. Die Gewichte sind daher behutsam angepasst,
nicht direkt uebernommen. Und das Referenzjahr der Baumartenkarte ist
2017/2018: Wo dort Fichte steht, kann heute Kahlflaeche sein.</div>

<h2>Belegte Funde</h2>
<p>Als eigene Ebene lassen sich gemeldete Funde derselben Art einblenden -
lila Punkte, zusammengefasst zu Gruppen. Gezeigt wird ein Fenster von
&plusmn;21 Tagen <b>im Jahreslauf</b>: Ein Oktoberfund von 2021 erscheint
also auf der Oktoberkarte. Juengere Funde sind kraeftiger dargestellt.
Meldungen mit einer Ortsangabe grober als 3 km werden weggelassen.</p>

<p>Das ist keine Vorhersage, sondern eine Gegenprobe: Wo schon einmal
etwas stand, stimmt oft mehr als das Wetter allein hergibt - Baumarten,
Alter des Bestandes, Bodenverhaeltnisse im Kleinen.</p>

<div class="hinweis">Beim Schwefelporling ist diese Ebene wertvoller als
der Score. Er waechst an einzelnen Baeumen und kommt dort jahrelang
wieder. Ein alter Fundpunkt ist deshalb ein besserer Hinweis als jede
Wetterrechnung - was die Kalibrierung bestaetigt: Bei 840 Funden liegen
alle Wetter-Auswahlverhaeltnisse zwischen 0,74 und 1,33, also praktisch
ohne Signal.</div>

<p>Einschraenkung: Diese Punkte zeigen, wo Menschen unterwegs waren und
gemeldet haben. Waldstuecke ohne Meldungen sind nicht schlechter, nur
unbeachtet.</p>

<h2>Was die Karte <i>nicht</i> kann</h2>
<div class="warnung">
  <b>Sie erkennt keine Pilze und sagt nichts ueber Essbarkeit.</b>
  Bestimme jeden Fund selbst sicher, im Zweifel ueber eine Pilzberatung.
  Kein Pilz gehoert in die Pfanne, bei dem auch nur ein Restzweifel bleibt.
</div>
<ul>
  <li><b>Baumarten von 2017/2018.</b> Seither hat das Fichtensterben
      ganze Bestaende veraendert. In dieser Region spielt das kaum eine
      Rolle - Fichte kommt hier fast nicht vor -, im Mittelgebirge sehr
      wohl.</li>
  <li><b>Nur Anwesenheitsdaten.</b> Es ist bekannt, wann jemand etwas fand
      &ndash; nicht, wann jemand vergeblich suchte. Die Schwellen lassen
      sich deshalb nur einseitig pruefen.</li>
  <li><b>Beobachterverzerrung.</b> Im Oktober sind mehr Sammler unterwegs
      als im Juli. Der Saisonfaktor rechnet das heraus, indem er die
      Meldungen einer Art durch alle Pilzmeldungen desselben Monats teilt.</li>
  <li><b>Grobes Raster.</b> 2 km sagen etwas ueber ein Waldstueck, nichts
      ueber die einzelne Senke. Beim Schwefelporling, der an einzelnen
      Baeumen waechst, ist das besonders unscharf.</li>
  <li><b>Schutzgebiete ohne Gewaehr.</b> OpenStreetMap ist gut gepflegt,
      aber nicht amtlich. Verbindlich ist das jeweilige Landesverzeichnis.
      Und auch ausserhalb gilt: nur fuer den Eigenbedarf, einzelne Arten
      stehen bundesweit unter Schutz.</li>
</ul>

<h2>Die Arten im Einzelnen</h2>
<nav>{sprung}</nav>
{bloecke}

</body>
</html>
"""
    with open(dateiname, "w", encoding="utf-8") as f:
        f.write(html)
    return dateiname
