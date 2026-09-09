import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
import waldebenen as w
import web_wald


class WaldFlaechen(unittest.TestCase):
    def test_viertel_halb_voll(self):
        maske = np.array([[1, 0, 1, 1, 1, 1], [0, 0, 0, 0, 1, 1]], dtype=bool)
        np.testing.assert_array_equal(w.flaechenanteile(maske), [[64, 128, 255]])

    def test_schmaler_streifen_bleibt_sichtbar(self):
        maske = np.zeros((8, 8), dtype=bool)
        maske[:, 1] = True
        self.assertFalse(maske[::4, ::4].any())
        verkleinert = w.flaechenanteile(maske)
        self.assertTrue(np.all(verkleinert[:, 0] == 128))
        self.assertAlmostEqual(verkleinert.mean() / 255, maske.mean(), places=3)

    def test_arten_werden_nicht_gemischt(self):
        klassen = np.array([[2, 9], [2, 9]])
        self.assertEqual(128, w.flaechenanteile(klassen == 2)[0, 0])
        self.assertEqual(128, w.flaechenanteile(klassen == 9)[0, 0])
        self.assertEqual(255, w.flaechenanteile(klassen > 0)[0, 0])

    def test_kachelposition_und_naht(self):
        with tempfile.TemporaryDirectory() as tmp:
            for iy in range(2):
                for ix in range(2):
                    Image.fromarray(np.full((3, 3), 1 + iy * 2 + ix, np.uint8)).save(Path(tmp) / f'k_{iy}_{ix}.tif')
            with patch.multiple(w, KACHELORDNER=tmp, KACHELN_X=2, KACHELN_Y=2):
                bild = w.lade_gesamtbild()
            np.testing.assert_array_equal(bild[:3, :3], 3)
            np.testing.assert_array_equal(bild[:3, 3:], 4)
            np.testing.assert_array_equal(bild[3:, :3], 1)
            np.testing.assert_array_equal(bild[3:, 3:], 2)
            self.assertEqual((3, 3), w.flaechenanteile(bild > 0).shape)

    def test_webexport_erhaelt_groesse_und_alpha(self):
        with tempfile.TemporaryDirectory() as tmp:
            quelle = Path(tmp) / 'quelle'
            quelle.mkdir()
            bild = np.zeros((4, 2300, 4), dtype=np.uint8)
            bild[:, :, :3] = [60, 110, 60]
            bild[:, ::2, 3] = 83
            Image.fromarray(bild).save(quelle / 'wald_gesamt.png')
            (quelle / 'wald_grenzen.txt').write_text('52,10,53,11')
            ziel = Path(tmp) / 'web'
            with patch.multiple(web_wald, QUELLE=str(quelle), ZIEL=str(ziel)):
                web_wald.main()
            with Image.open(ziel / 'wald/wald_gesamt.png') as im:
                self.assertEqual((2300, 4), im.size)
                np.testing.assert_array_equal(np.array(im)[:, :, 3], bild[:, :, 3])


if __name__ == '__main__':
    unittest.main()
