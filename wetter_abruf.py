"""Gemeinsamer Starttakt fuer die parallelen Open-Meteo-Abrufe eines Prozesses."""
import math
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def retry_sekunden(wert, jetzt=None):
    """Retry-After als Sekunden oder HTTP-Datum; ungueltig -> 60 Sekunden."""
    try:
        sekunden = float(wert)
    except (TypeError, ValueError):
        try:
            datum = parsedate_to_datetime(wert)
            if datum.tzinfo is None:
                datum = datum.replace(tzinfo=timezone.utc)
            sekunden = (datum - (jetzt or datetime.now(timezone.utc))).total_seconds()
        except (TypeError, ValueError, OverflowError, AttributeError):
            return 60.0
    return max(1.0, sekunden) if math.isfinite(sekunden) else 60.0


class AbrufTakt:
    """300 Orts-/Modelleinheiten pro Minute, ohne angespartes Burst-Guthaben.

    Konservative Taktung, keine exakte Nachbildung der Anbieterabrechnung.
    Stunden-/Tageslimits und fremde Nutzer derselben IP bleiben moeglich.
    Lange Serversperren beenden weitere Abrufe statt den Workflow auszusitzen.
    """
    def __init__(self, pro_minute=300, max_pause=300, uhr=None, schlafen=None):
        if not math.isfinite(pro_minute) or pro_minute <= 0:
            raise ValueError('pro_minute muss positiv und endlich sein')
        self.pro_minute = pro_minute
        self.max_pause = max_pause
        self.uhr = uhr or time.monotonic
        self.schlafen = schlafen or time.sleep
        self.sperre = threading.Lock()
        self.naechster_start = 0.0
        self.gestoppt = False

    def warte(self, orte, modelle=1):
        kosten = orte * modelle
        if not math.isfinite(kosten) or kosten <= 0:
            raise ValueError('Abrufkosten muessen positiv und endlich sein')
        while True:
            with self.sperre:
                if self.gestoppt:
                    return False
                jetzt = self.uhr()
                rest = self.naechster_start - jetzt
                if rest <= 0:
                    self.naechster_start = jetzt + kosten * 60 / self.pro_minute
                    return True
            # Sperre freigeben: andere Threads koennen eine Serversperre melden.
            self.schlafen(min(rest, 1.0))

    def gedrosselt(self, retry_after=None):
        sekunden = retry_sekunden(retry_after)
        with self.sperre:
            if sekunden > self.max_pause:
                self.gestoppt = True
                return f'Server verlangt {sekunden:.0f} s Pause; weitere Abrufe in diesem Prozess beendet'
            self.naechster_start = max(self.naechster_start, self.uhr() + sekunden)
        return f'gemeinsame Pause mindestens {sekunden:.0f} s'


TAKT = AbrufTakt()
