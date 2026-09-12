import unittest
import numpy as np

import relief
import relief_geo as geo


class ReliefGeoTest(unittest.TestCase):
    PUNKTE = [(52.2, 10.8), (52.7, 10.55), (52.05, 10.1), (52.85, 11.15)]

    def test_hin_und_zurueck(self):
        lat = np.array([p[0] for p in self.PUNKTE])
        lon = np.array([p[1] for p in self.PUNKTE])
        e, n = geo.wgs84_zu_utm(lat, lon)
        lat2, lon2 = geo.utm_zu_wgs84(e, n)
        self.assertLess(np.abs(lat2 - lat).max() * 111000, 0.01)
        self.assertLess(np.abs(lon2 - lon).max() * 70000, 0.01)

    def test_passt_zu_relief(self):
        for lat, lon in self.PUNKTE:
            e, n = geo.wgs84_zu_utm(lat, lon)
            lat_r, lon_r = relief.utm_zu_wgs84(float(e), float(n))
            self.assertAlmostEqual(lat_r, lat, delta=1e-7)
            self.assertAlmostEqual(lon_r, lon, delta=1e-7)

    def test_raster_umschliesst_utm_rechteck(self):
        rahmen = (600000.0, 5780000.0, 616000.0, 5797000.0)
        sued, west, nord, ost, hoehe = geo.umschliessendes_raster(rahmen, 1000)
        ecken = [(rahmen[0], rahmen[1]), (rahmen[0], rahmen[3]),
                 (rahmen[2], rahmen[1]), (rahmen[2], rahmen[3])]
        for e, n in ecken:
            lat, lon = geo.utm_zu_wgs84(e, n)
            self.assertTrue(sued <= lat <= nord and west <= lon <= ost)
        # Bildpunkte etwa quadratisch: 16 x 17 km
        self.assertAlmostEqual(hoehe / 1000, 17 / 16, delta=0.08)

    def test_waldmaske_schlaegt_im_mercator_bild_nach(self):
        alpha = np.zeros((4, 4), dtype=np.uint8)
        alpha[0, 3] = 165        # Nordost-Ecke ist Wald
        maske = geo.Waldmaske(alpha, 52.0, 10.0, 53.0, 11.0)
        self.assertTrue(maske.wald(np.array([52.95]), np.array([10.9]))[0])
        self.assertFalse(maske.wald(np.array([52.05]), np.array([10.1]))[0])
        self.assertFalse(maske.wald(np.array([54.0]), np.array([10.9]))[0])
        form = (5, 6)
        rahmen = (600000.0, 5800000.0, 606000.0, 5805000.0)
        self.assertEqual(maske.fuer_utm_gitter(form, rahmen, 1000.0,
                                               streifen=2).shape, form)


if __name__ == "__main__":
    unittest.main()
