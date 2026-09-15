import unittest

import schutzgebiete as sg


def quadrat(x, y, a):
    return [(x, y), (x + a, y), (x + a, y + a), (x, y + a), (x, y)]


class RingeBauenTest(unittest.TestCase):
    def test_drei_stuecke_eines_umgedreht(self):
        wege = [
            [(0, 0), (1, 0), (1, 1)],
            [(0, 1), (0, 0)],
            # umgedreht: laeuft von (0,1) nach (1,1) statt umgekehrt
            [(0, 1), (0.5, 1.2), (1, 1)],
        ]
        ringe, reste = sg.ringe_bauen(wege)
        self.assertEqual(reste, 0)
        self.assertEqual(len(ringe), 1)
        ring = ringe[0]
        self.assertEqual(ring[0], ring[-1])
        self.assertEqual(len(ring), 6)
        self.assertEqual(set(ring), {(0, 0), (1, 0), (1, 1), (0.5, 1.2),
                                     (0, 1)})

    def test_offener_rest_wird_verworfen_nicht_geschlossen(self):
        wege = [quadrat(0, 0, 1), [(5, 5), (6, 5), (6, 6)]]
        ringe, reste = sg.ringe_bauen(wege)
        self.assertEqual(len(ringe), 1)
        self.assertEqual(reste, 1)


class PolygoneOrdnenTest(unittest.TestCase):
    def test_loch_kommt_zum_richtigen_aussenring(self):
        gross = quadrat(0, 0, 10)
        loch = quadrat(2, 2, 2)
        daneben = quadrat(20, 0, 3)
        polygone = sg.polygone_ordnen([loch, daneben, gross])
        self.assertEqual(len(polygone), 2)
        mit_loch = [p for p in polygone if len(p) == 2]
        self.assertEqual(len(mit_loch), 1)
        self.assertEqual(set(mit_loch[0][0]), set(gross))
        self.assertEqual(set(mit_loch[0][1]), set(loch))

    def test_richtung_aussen_gegen_loch_mit_uhrzeiger(self):
        gross = quadrat(0, 0, 10)[::-1]   # im Uhrzeigersinn angeliefert
        loch = quadrat(2, 2, 2)           # gegen den Uhrzeigersinn
        (poly,) = sg.polygone_ordnen([gross, loch])
        self.assertGreater(sg.flaeche(poly[0]), 0)
        self.assertLess(sg.flaeche(poly[1]), 0)

    def test_insel_im_loch_ist_wieder_aussen(self):
        ringe = [quadrat(0, 0, 10), quadrat(2, 2, 6), quadrat(4, 4, 2)]
        polygone = sg.polygone_ordnen(ringe)
        self.assertEqual(sorted(len(p) for p in polygone), [1, 2])


class VereinfachenTest(unittest.TestCase):
    def test_ring_bleibt_geschlossen_und_verliert_zwischenpunkte(self):
        # Quadrat von gut 700 m mit vielen Punkten auf den Kanten
        a = 0.01
        ring = []
        for i in range(10):
            ring.append((10.5 + a * i / 10, 52.4))
        for i in range(10):
            ring.append((10.5 + a, 52.4 + a * i / 10))
        for i in range(10):
            ring.append((10.5 + a - a * i / 10, 52.4 + a))
        for i in range(10):
            ring.append((10.5, 52.4 + a - a * i / 10))
        ring.append(ring[0])

        ergebnis = sg.vereinfachen(ring)
        self.assertEqual(ergebnis[0], ergebnis[-1])
        self.assertEqual(len(ergebnis), 5)

    def test_zu_kleiner_ring_faellt_weg(self):
        winzig = quadrat(10.5, 52.4, 0.000001)
        self.assertIsNone(sg.vereinfachen(winzig))


class InnenpunktTest(unittest.TestCase):
    def test_punkt_im_loch_zaehlt_nicht(self):
        polygone = sg.polygone_ordnen([quadrat(0, 0, 10), quadrat(2, 2, 2)])
        self.assertTrue(sg.im_multipolygon((1, 1), polygone))
        self.assertFalse(sg.im_multipolygon((3, 3), polygone))

    def test_innenpunkt_einer_sichel(self):
        # U-Form: der Schwerpunkt liegt in der Aussparung
        u = [(0, 0), (6, 0), (6, 6), (4, 6), (4, 2), (2, 2), (2, 6),
             (0, 6), (0, 0)]
        polygone = sg.polygone_ordnen([u])
        self.assertTrue(sg.im_multipolygon(sg.innenpunkt(polygone),
                                           polygone))


class EinstufungTest(unittest.TestCase):
    def test_naturpark_nicht_nsg_und_kernzone_ja(self):
        self.assertFalse(sg.sammelverbot_osm(
            {"protect_class": "5", "protection_title": "Naturpark"}))
        self.assertTrue(sg.sammelverbot_osm(
            {"protect_class": "4", "protection_title": "Naturschutzgebiet"}))
        self.assertTrue(sg.sammelverbot_osm(
            {"protect_class": "1", "protection_title": "Kernzone"}))
        self.assertFalse(sg.sammelverbot_osm(
            {"protect_class": "5",
             "protection_title": "Landschaftsschutzgebiet"}))

    def test_nur_https_links(self):
        self.assertEqual(sg.nur_https("http://example.org"), "")
        self.assertEqual(sg.nur_https("javascript:alert(1)"), "")
        self.assertEqual(sg.nur_https(" https://a.de/x "), "https://a.de/x")


if __name__ == "__main__":
    unittest.main()
