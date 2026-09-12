import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import web_wald


class WaldDarstellungTest(unittest.TestCase):
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
                self.assertNotIn("kontur", m["ebenen"][0])
                # Scheitert der Export mittendrin, bleibt der alte Stand
                with patch.object(web_wald.hashlib, "sha256", side_effect=RuntimeError("Test")):
                    with self.assertRaises(RuntimeError):
                        web_wald.main()
                self.assertEqual((ziel / "wald.json").read_bytes(), manifest)


if __name__ == "__main__":
    unittest.main()
