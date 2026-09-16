"""Offline-Pruefung der Taktung und beider HTTP-Aufrufstellen."""
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import io
import threading
import unittest
from unittest.mock import Mock, patch
import requests
import prognose
import sammeln
from wetter_abruf import AbrufTakt, retry_sekunden


class Uhr:
    def __init__(self):
        self.zeit = 0.0
        self.lock = threading.Lock()

    def jetzt(self):
        with self.lock:
            return self.zeit

    def schlafen(self, sekunden):
        with self.lock:
            self.zeit += sekunden


class AbrufTests(unittest.TestCase):
    def setUp(self):
        self.uhr = Uhr()
        self.takt = AbrufTakt(uhr=self.uhr.jetzt, schlafen=self.uhr.schlafen)

    def test_orte_modelle_und_keine_angesparten_spitzen(self):
        self.assertTrue(self.takt.warte(40))
        self.assertTrue(self.takt.warte(50, modelle=2))
        self.assertEqual(8, self.uhr.jetzt())
        self.assertTrue(self.takt.warte(40))
        self.assertEqual(28, self.uhr.jetzt())
        self.uhr.schlafen(100)
        self.takt.warte(40)
        self.takt.warte(40)
        self.assertEqual(136, self.uhr.jetzt())

    def test_parallel_kein_eigenes_budget_je_worker(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertTrue(all(pool.map(lambda _: self.takt.warte(50), range(12))))
        self.assertGreaterEqual(self.uhr.jetzt(), 110)

    def test_serversperre_gilt_fuer_alle_und_wird_nicht_verkuerzt(self):
        self.takt.warte(40)
        self.takt.gedrosselt('90')
        self.takt.gedrosselt('10')
        self.takt.warte(40)
        self.assertEqual(90, self.uhr.jetzt())
        self.takt.warte(40)
        self.assertEqual(98, self.uhr.jetzt())

    def test_neue_serversperre_erreicht_bereits_wartenden_worker(self):
        self.takt.warte(40)
        def schlaf(sekunden):
            self.uhr.schlafen(sekunden)
            if self.uhr.jetzt() == 1:
                self.takt.gedrosselt('60')
        self.takt.schlafen = schlaf
        self.takt.warte(40)
        self.assertEqual(61, self.uhr.jetzt())

    def test_lange_sperre_stoppt_ohne_erneuten_http_versuch(self):
        self.takt.gedrosselt('3600')
        self.assertFalse(self.takt.warte(40))
        self.assertFalse(self.takt.warte(2))
        self.assertEqual(0, self.uhr.jetzt())

    def test_retry_after_sekunden_datum_und_ungueltig(self):
        jetzt = datetime(2026, 9, 16, tzinfo=timezone.utc)
        self.assertEqual(120, retry_sekunden('Wed, 16 Sep 2026 00:02:00 GMT', jetzt))
        self.assertEqual(30, retry_sekunden('30'))
        for wert in (None, '', 'ungueltig', 'nan', 'inf'):
            self.assertEqual(60, retry_sekunden(wert))
        self.assertEqual(1, retry_sekunden('0'))

    def _http_test(self, modul, responses, anzahl=40):
        orte = [(str(i), 52., 10.) for i in range(anzahl)]
        zeiten = []
        antworten = iter(responses)
        def get(*args, **kwargs):
            zeiten.append(self.uhr.jetzt())
            antwort = next(antworten)
            if isinstance(antwort, Exception):
                raise antwort
            return antwort
        arg = (date(2026,9,16),) * (2 if modul is prognose else 1)
        with patch.object(modul, 'TAKT', self.takt), patch('requests.get', side_effect=get), \
                patch.object(modul.time, 'sleep', self.uhr.schlafen), \
                contextlib.redirect_stdout(io.StringIO()):
            ergebnis = modul.hole_buendel(orte, *arg)
        return ergebnis, zeiten

    def test_prognose_429_wartet_vor_wiederholung(self):
        drossel = Mock(status_code=429, headers={'Retry-After':'90'})
        ok = Mock(status_code=200)
        ok.json.return_value = [{'daily':{}}]*40
        ergebnis, zeiten = self._http_test(prognose, [drossel, ok])
        self.assertEqual(40,len(ergebnis))
        self.assertEqual([0,90],zeiten)

    def test_sammeln_beide_modelle_zaehlen_auch_bei_wiederholungen(self):
        ok = Mock(status_code=200)
        ok.json.return_value = [{'daily':{'precipitation_sum_icon_d2':[0],
                                         'temperature_2m_mean_icon_d2':[10]}}]*50
        ergebnis, zeiten = self._http_test(sammeln, [requests.ReadTimeout(),ok],50)
        self.assertEqual(50,len(ergebnis))
        self.assertEqual([0,20],zeiten)
        self.assertEqual(0, ergebnis[0]['regen_icon'])

    def test_beide_abrufer_stoppen_bei_langer_sperre(self):
        for modul in (prognose, sammeln):
            with self.subTest(modul=modul.__name__):
                self.setUp()
                antwort = Mock(status_code=429, headers={'Retry-After':'3600'})
                ergebnis, zeiten = self._http_test(modul,[antwort])
                self.assertIsNone(ergebnis)
                self.assertEqual([0],zeiten)

    def test_lange_sperre_meldet_beide_hauptlaeufe_als_fehler(self):
        orte = [('W1',52.,10.)]
        def ausfall(*args, **kwargs):
            self.takt.gedrosselt('3600')
            return None
        for modul in (prognose,sammeln):
            with self.subTest(modul=modul.__name__):
                self.setUp()
                with patch.object(modul,'TAKT',self.takt), \
                     patch.object(modul,'lade_punkte',return_value=orte), \
                     patch.object(modul,'buendel_moeglich',return_value=False), \
                     patch.object(modul,'hole_buendel',side_effect=ausfall), \
                     patch.object(prognose,'schreibe') as schreibe, \
                     patch.object(sammeln.historie,'vorhandene',return_value=set()), \
                     patch.object(sammeln.historie,'anhaengen') as anhaengen, \
                     contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as fehler:
                        modul.main()
                    self.assertEqual(1,fehler.exception.code)
                    schreibe.assert_not_called()
                    if modul is sammeln:
                        anhaengen.assert_called_once_with([])

    def test_wiederholungen_bleiben_begrenzt(self):
        for modul in (prognose,sammeln):
            with self.subTest(modul=modul.__name__):
                self.setUp()
                antwort = Mock(status_code=429,headers={})
                ergebnis, zeiten = self._http_test(modul,[antwort]*4)
                self.assertIsNone(ergebnis)
                self.assertEqual([0,60,120,180],zeiten)


if __name__ == '__main__':
    unittest.main()
