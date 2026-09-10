import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
import waldebenen as w
import web_wald


class WaldFlaechen(unittest.TestCase):
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
