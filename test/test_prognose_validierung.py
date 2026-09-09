"""Offline: python -B -m unittest discover -s test -p test_prognose_validierung.py"""
import contextlib
import csv
import io
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prognose as p


class PrognosePruefung(unittest.TestCase):
    def setUp(self):
        self.start = date(2026, 9, 9)
        self.ende = self.start + timedelta(days=6)
        self.orte = [(str(i), 52.0, 10.0) for i in range(100)]
        self.daily = {"time": [(self.start + timedelta(days=i)).isoformat()
                               for i in range(7)]}
        self.daily.update({f: [0.0] * 7 for f in p.FELDER})
        self.zeilen = [z for o in self.orte for z in p.tageszeilen(o, self.daily)]

    def pruefe(self, zeilen, orte=None):
        return p.fehlt_etwas(zeilen, self.orte if orte is None else orte,
                            self.start, self.ende)

    def test_vollstaendig_und_nullwerte(self):
        self.assertEqual([], self.pruefe(self.zeilen))

    def test_toleranz_und_aufrunden(self):
        with patch.object(p, "MINDEST_ANTEIL", 0.98):
            self.assertEqual([], self.pruefe(self.zeilen[14:]))
            self.assertTrue(self.pruefe(self.zeilen[21:]))
            self.assertTrue(self.pruefe([], self.orte[:1]))

    def test_wechselnde_luecken(self):
        # Pro Tag nur 1 % Ausfall, aber sieben unterschiedliche Orte betroffen.
        zeilen = [z for z in self.zeilen if z['ort'] !=
                  str((date.fromisoformat(z['datum']) - self.start).days)]
        self.assertTrue(self.pruefe(zeilen))

    def test_doppelte_kennungen_und_zeilen(self):
        self.assertTrue(self.pruefe(self.zeilen + self.zeilen[:1]))
        self.assertTrue(self.pruefe(self.zeilen, self.orte + self.orte[:1]))

    def test_unbekannte_orte_tage_koordinaten_und_messwerte(self):
        for feld, wert in [('ort', 'fremd'), ('datum', '2020-01-01'),
                           ('lat', 51), ('temperatur', None), ('bf07', ''),
                           ('et0', float('nan')), ('regen', float('inf')),
                           ('bt728', True)]:
            with self.subTest(feld=feld, wert=wert):
                zeilen = [dict(z) for z in self.zeilen]
                zeilen[0][feld] = wert
                self.assertTrue(self.pruefe(zeilen))

    def test_antwortform(self):
        for d in [None, {}, {'time': []}, {**self.daily, p.FELDER[0]: [1]}]:
            with self.assertRaises(ValueError):
                p.tageszeilen(self.orte[0], d)

    def test_fehlschlag_erhaelt_datei_erfolg_ersetzt(self):
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / 'prognose.csv'
            ziel.write_bytes(b'alte Datei\n')
            with patch.object(p, 'DATEI', str(ziel)), \
                 patch.object(p, 'lade_punkte', return_value=self.orte[:1]), \
                 patch.object(p, 'buendel_moeglich', return_value=False), \
                 patch.object(p, 'PAUSE', 0), \
                 contextlib.redirect_stdout(io.StringIO()):
                with patch.object(p, 'hole_buendel', return_value=None):
                    with self.assertRaises(SystemExit) as fehler:
                        p.main()
                    self.assertEqual(1, fehler.exception.code)
                    self.assertEqual(b'alte Datei\n', ziel.read_bytes())
                heute = date.today()
                daily = {**self.daily, 'time': [(heute + timedelta(days=i)).isoformat()
                                               for i in range(7)]}
                with patch.object(p, 'hole_buendel', return_value=[daily]):
                    p.main()
                with ziel.open(encoding='utf-8') as f:
                    self.assertEqual(7, len(list(csv.DictReader(f))))
                self.assertFalse(Path(str(ziel) + '.neu').exists())


if __name__ == '__main__':
    unittest.main()
