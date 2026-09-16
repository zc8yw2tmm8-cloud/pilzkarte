"""Offline-Pruefungen der begrenzten Runner-Diagnose."""
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import prognose
from wetter_paketvergleich import Vergleich, pakete


class VergleichTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.v = Vergleich(Path(self.tmp.name), date(2026, 9, 16))
        self.punkte = [('ort', 52.0, 10.0)]
        self.daily = {'time': [str(self.v.start + timedelta(days=i)) for i in range(7)]}
        self.daily.update({f: [0.0]*7 for f in prognose.FELDER})

    def test_beide_groessen_decken_dieselben_orte_ab(self):
        punkte = list(range(160))
        for groesse, anzahl in [(10, 16), (40, 4)]:
            batches = pakete(punkte, groesse)
            self.assertEqual(anzahl, len(batches))
            self.assertEqual(punkte, [p for batch in batches for p in batch])

    @patch('wetter_paketvergleich.requests.get')
    def test_vollstaendige_nullwerte_und_paarvergleich(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'daily': self.daily}
        with patch.object(self.v.takt, 'warte', return_value=True):
            for groesse in (10, 40):
                e = self.v.anfrage(1, groesse, 0, self.punkte)
                self.assertEqual(1, e['vollstaendig'])
                self.assertIsNone(e['fehler'])
        self.assertEqual({'runde': 1, 'ort_tage': 7, 'abweichend': 0},
                         self.v.zusammenfassung()['wertevergleich'][0])
        self.assertEqual(120, get.call_args.kwargs['timeout'])

    @patch('wetter_paketvergleich.requests.get')
    def test_429_stoppt_folgeanfragen(self, get):
        get.return_value = Mock(status_code=429, text='limit', headers={'Retry-After': '60'})
        self.v.anfrage(1, 10, 0, self.punkte)
        e = self.v.anfrage(1, 10, 1, self.punkte)
        self.assertFalse(e['angefragt'])
        get.assert_called_once()
        self.assertEqual(1, self.v.zusammenfassung()['varianten'][10]['http429'])

    @patch('wetter_paketvergleich.requests.get')
    def test_zeitbudget_verhindert_neue_anfrage(self, get):
        self.v.deadline = 0
        e = self.v.anfrage(1, 10, 0, self.punkte)
        self.assertFalse(e['angefragt'])
        self.assertIsNotNone(self.v.abbruch)
        get.assert_not_called()

    @patch('wetter_paketvergleich.requests.get')
    def test_unvollstaendige_antwort_ist_kein_erfolg(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'daily': {**self.daily, prognose.FELDER[0]: [None]*7}}
        e = self.v.anfrage(1, 40, 0, self.punkte)
        self.assertEqual(0, e['vollstaendig'])
        self.assertIsNotNone(e['fehler'])
        self.assertEqual(0, self.v.zusammenfassung()['wertevergleich'][0]['ort_tage'])


if __name__ == '__main__':
    unittest.main()
