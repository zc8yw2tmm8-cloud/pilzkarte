"""Manuelle, begrenzte Diagnose; erzeugt ausschliesslich Diagnoseartefakte."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import threading
import time
from zoneinfo import ZoneInfo

import requests
import prognose
from wetter_abruf import AbrufTakt


def pakete(punkte, groesse):
    return [punkte[i:i+groesse] for i in range(0,len(punkte),groesse)]


class Vergleich:
    def __init__(self, out, start, budget=300):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.start = start
        self.ende = start + timedelta(days=prognose.TAGE_VORAUS)
        self.beginn = time.monotonic()
        self.deadline = self.beginn + budget
        self.takt = AbrufTakt()
        self.lock = threading.Lock()
        self.abbruch = None
        self.eintraege = []
        self.werte = {}

    def stoppe(self, grund):
        with self.lock:
            if self.abbruch is None:
                self.abbruch = grund
        with self.takt.sperre:
            self.takt.gestoppt = True

    def anfrage(self, runde, groesse, nummer, punkte):
        e = dict(runde=runde,paketgroesse=groesse,paket=nummer,
                 orte=[p[0] for p in punkte],angefragt=False,status=None,
                 fehler=None,vollstaendig=0,dauer_s=0)
        if time.monotonic() + 130 > self.deadline:
            self.stoppe('Zeitbudget: keine weitere Anfrage mit 120-s-Timeout')
        if not self.takt.warte(len(punkte)):
            e['fehler'] = 'Nicht gestartet: Abbruch'
            return self.speichere(e)
        if time.monotonic() + 130 > self.deadline:
            self.stoppe('Zeitbudget nach Taktpause')
            e['fehler'] = 'Nicht gestartet: Zeitbudget'
            return self.speichere(e)
        params = dict(latitude=','.join(str(p[1]) for p in punkte),
                      longitude=','.join(str(p[2]) for p in punkte),
                      start_date=str(self.start),end_date=str(self.ende),
                      daily=','.join(prognose.FELDER),timezone='Europe/Berlin')
        e['angefragt'] = True
        e['utc'] = datetime.now(timezone.utc).isoformat()
        anfang = time.monotonic()
        try:
            response = requests.get('https://api.open-meteo.com/v1/forecast',
                                    params=params,timeout=120)
            e['status'] = response.status_code
            if response.status_code != 200:
                e['fehler'] = response.text[:300]
                if response.status_code == 429:
                    e['retry_after'] = response.headers.get('Retry-After')
                    self.stoppe('HTTP 429: keine weiteren Anfragen')
            else:
                daten = response.json()
                raw = json.dumps(daten,ensure_ascii=False).encode('utf-8')
                (self.out/f'antwort_{runde}_{groesse}_{nummer}.json').write_bytes(raw)
                e['sha256'] = hashlib.sha256(raw).hexdigest()
                if isinstance(daten,dict):
                    daten = [daten]
                if not isinstance(daten,list):
                    raise ValueError('Antwort ist keine Ortsliste')
                daily = [d.get('daily') if isinstance(d,dict) else None for d in daten]
                zeilen, fehlend = prognose.paket_auswerten(punkte,daily,self.start,self.ende)
                e['vollstaendig'] = len(punkte)-len(fehlend)
                if fehlend:
                    e['fehler'] = 'Unvollstaendige Orte: '+','.join(p[0] for p in fehlend)
                with self.lock:
                    self.werte.setdefault((runde,groesse),{}).update(
                        {(z['ort'],z['datum']):z for z in zeilen})
        except (requests.RequestException,ValueError,TypeError) as exc:
            e['fehler'] = type(exc).__name__
        e['dauer_s'] = round(time.monotonic()-anfang,3)
        return self.speichere(e)

    def speichere(self, eintrag):
        with self.lock:
            self.eintraege.append(eintrag)
            with (self.out/'anfragen.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(eintrag,ensure_ascii=False)+'\n')
            print(json.dumps(eintrag,ensure_ascii=False),flush=True)
        return eintrag

    def zusammenfassung(self):
        varianten = {}
        for groesse in (10,40):
            rows = [e for e in self.eintraege if e['paketgroesse']==groesse and e['angefragt']]
            dauer = [e['dauer_s'] for e in rows]
            varianten[groesse] = dict(anfragen=len(rows),
                vollstaendige_ortsantworten=sum(e['vollstaendig'] for e in rows),
                fehler=sum(e['fehler'] is not None for e in rows),
                http429=sum(e['status']==429 for e in rows),
                timeouts=sum(e['fehler'] in ('ReadTimeout','ConnectTimeout') for e in rows),
                median_s=statistics.median(dauer) if dauer else None,
                maximum_s=max(dauer) if dauer else None)
        paare = []
        for runde in (1,2):
            a,b = self.werte.get((runde,10),{}), self.werte.get((runde,40),{})
            gemeinsam = a.keys() & b.keys()
            paare.append(dict(runde=runde,ort_tage=len(gemeinsam),
                              abweichend=sum(a[k]!=b[k] for k in gemeinsam)))
        return dict(abbruch=self.abbruch,varianten=varianten,wertevergleich=paare,
                    dauer_s=round(time.monotonic()-self.beginn,2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ausgabe',type=Path,default=Path('diagnose_ergebnis'))
    args = parser.parse_args()
    start = datetime.now(ZoneInfo('Europe/Berlin')).date()
    v = Vergleich(args.ausgabe,start)
    alle = prognose.lade_punkte()
    punkte = [p for offset in (0,400,800,1200) for p in alle[offset:offset+40]]
    if len(punkte)!=160 or len({p[0] for p in punkte})!=160:
        raise ValueError('Auswahl umfasst nicht 160 verschiedene Orte')
    # Pro Variante ganze 160 Orte im Pool, damit auch 40er-Pakete vier Arbeiter nutzen.
    for runde,reihenfolge in enumerate(((40,10),(10,40)),start=1):
        for groesse in reihenfolge:
            if v.abbruch: break
            jobs = list(enumerate(pakete(punkte,groesse)))
            with ThreadPoolExecutor(max_workers=prognose.ARBEITER) as pool:
                list(pool.map(lambda job:v.anfrage(runde,groesse,job[0],job[1]),jobs))
        if v.abbruch: break
    bericht = v.zusammenfassung()
    bericht.update(start=str(start),ende=str(v.ende),felder=prognose.FELDER,
                   punkte=[p[0] for p in punkte],arbeiter=prognose.ARBEITER,timeout_s=120,
                   zeitbudget_s=300,wiederholungen=0,requests_version=requests.__version__,
                   python=platform.python_version(),system=platform.system(),
                   github_run_id=os.environ.get('GITHUB_RUN_ID'),
                   github_sha=os.environ.get('GITHUB_SHA'),
                   einschraenkung='Stichprobe; Caches, Serverlast, IP und Modellupdates nicht kontrolliert. Keine Produktionsdaten geschrieben. Unvollstaendige Varianten nicht als Erfolg werten.')
    (args.ausgabe/'bericht.json').write_text(json.dumps(bericht,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ERGEBNIS '+json.dumps(bericht,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
