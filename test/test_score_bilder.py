import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
import weichzeichnen as w


class ScoreBilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.object(w, 'BILDORDNER', self.tmp.name)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        w._GEOMETRIE.clear()
        self.orte = [(52.0, 10.0), (52.0, 10.08), (52.0, 10.16)]

    def bild(self, scores, name='test.png'):
        pfad, grenzen = w.erzeuge([(*ort, s) for ort, s in zip(self.orte, scores)], name, dunkel=True)
        with Image.open(pfad) as im:
            return np.array(im), grenzen

    def test_grenzen_und_alpha_bleiben_gleich(self):
        voll, grenzen = self.bild([80, 80, 80])
        luecke, andere = self.bild([80, None, 80])
        self.assertEqual(grenzen, andere)
        self.assertEqual(voll.shape, luecke.shape)
        np.testing.assert_array_equal(voll[:, :, 3], luecke[:, :, 3])

    def test_luecke_grau_nullscore_farbig(self):
        luecke, _ = self.bild([80, None, 80])
        null, _ = self.bild([80, 0, 80])
        y, x = luecke.shape[0] // 2, luecke.shape[1] // 2
        self.assertGreater(luecke[y, x, 3], 0)
        np.testing.assert_array_equal(luecke[y, x, :3], w.KEINE_DATEN_RGB)
        self.assertFalse(np.array_equal(null[y, x, :3], w.KEINE_DATEN_RGB))

    def test_fehlend_senkt_bekannte_scores_nicht(self):
        luecke, _ = self.bild([80, None, 80])
        innen = luecke[:, :, 3] >= 180
        grau = np.all(luecke[:, :, :3] == w.KEINE_DATEN_RGB, axis=2)
        erwartet = w.farbtabelle(True)[int(80 / 100 * 255)]
        # Fern der grauen Grenze bleibt die Farbe des Werts 80 erhalten.
        self.assertTrue(np.any(innen & ~grau & np.all(luecke[:, :, :3] == erwartet, axis=2)))

    def test_alle_fehlend_und_nicht_endliche_werte(self):
        bild, _ = self.bild([None, float('nan'), float('inf')])
        sichtbar = bild[:, :, 3] > 10
        self.assertTrue(sichtbar.any())
        np.testing.assert_array_equal(bild[sichtbar, :3], np.full((sichtbar.sum(), 3), 145))

    def test_cache_beruecksichtigt_geaenderte_punktlage(self):
        self.bild([80, None, 80])
        self.orte[1] = (52.01, 10.08)
        cached, _ = self.bild([80, None, 80])
        w._GEOMETRIE.clear()
        frisch, _ = self.bild([80, None, 80])
        np.testing.assert_array_equal(cached, frisch)


if __name__ == '__main__':
    unittest.main()
