import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import web_wald
from web_wald import konturbild


class WaldDarstellungTest(unittest.TestCase):
    def test_konturen_ohne_blocknaehte(self):
        alpha = Image.new("L", (37, 29))
        alpha.paste(165, (4, 3, 31, 26))
        alpha.paste(0, (10, 8, 20, 18))
        alpha.putpixel((33, 4), 41)
        vorher = alpha.tobytes()
        klein = konturbild(alpha, block=7)
        gross = konturbild(alpha, block=512)
        self.assertEqual(klein.tobytes(), gross.tobytes())
        self.assertEqual(alpha.tobytes(), vorher)
        self.assertEqual(klein.getpixel((0, 0))[3], 0)
        self.assertEqual(klein.getpixel((25, 20))[3], 0)
        self.assertEqual(klein.getpixel((4, 5))[:3], (23, 30, 43))
        self.assertEqual(klein.getpixel((3, 5))[:3], (255, 255, 255))
        self.assertGreater(klein.getpixel((33, 4))[3], 0)

    def test_leere_maske(self):
        self.assertIsNone(konturbild(Image.new("L", (17, 13))).getbbox())

    def test_export_erhaelt_anteile_und_grenzen(self):
        with tempfile.TemporaryDirectory() as tmp:
            quelle, ziel = Path(tmp) / "quelle", Path(tmp) / "web"
            quelle.mkdir()
            ziel.mkdir()
            alpha = Image.new("L", (9, 9))
            alpha.paste(165, (2, 2, 7, 7))
            alpha.putpixel((1, 2), 41)
            bild = Image.new("RGBA", alpha.size, "green")
            bild.putalpha(alpha)
            bild.save(quelle / "wald_gesamt.png")
            (quelle / "wald_grenzen.txt").write_text("52.1,10.2,52.8,11.1")
            with patch.object(web_wald, "QUELLE", str(quelle)), patch.object(web_wald, "ZIEL", str(ziel)):
                web_wald.main()
                manifest = (ziel / "wald.json").read_bytes()
                m = json.loads(manifest)
                self.assertEqual(m["grenzen"], [[52.1, 10.2], [52.8, 11.1]])
                with Image.open(ziel / m["ebenen"][0]["datei"]) as export:
                    self.assertEqual(export.getchannel("A").tobytes(), alpha.tobytes())
                with patch.object(web_wald, "konturbild", side_effect=RuntimeError("Test")):
                    with self.assertRaises(RuntimeError):
                        web_wald.main()
                self.assertEqual((ziel / "wald.json").read_bytes(), manifest)


if __name__ == "__main__":
    unittest.main()
