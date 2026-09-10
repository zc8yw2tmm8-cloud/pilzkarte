import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from wald_geo import pruefe_kachel, anteilsfenster, geografische_grenzen

class Geografie(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)

    def tif(self, name, data, transform, crs="EPSG:3857"):
        path = self.p / name
        with rasterio.open(path, "w", driver="GTiff", width=data.shape[1],
                           height=data.shape[0], count=1, dtype="uint8",
                           crs=crs, transform=transform, nodata=0) as dst:
            dst.write(data.astype("uint8"), 1)
        return path

    def raster(self, files, transform, width, height, block=2):
        a = np.zeros((height*2, width*2), dtype="uint8")
        for win, data in anteilsfenster(files, transform, width, height, block):
            x,y,w,h=map(int,(win.col_off,win.row_off,win.width,win.height))
            a[y*2:(y+h)*2,x*2:(x+w)*2] = data
        return a

    def test_overlap_zero_and_order(self):
        t=from_origin(0,80,10,10)
        a=self.tif("a.tif",np.zeros((8,8)),t)
        b=self.tif("b.tif",np.full((8,8),9),t)
        out=self.raster([b,a],from_origin(0,80,20,20),4,4)
        np.testing.assert_array_equal(out,0)

    def test_offset_and_orientation(self):
        a=self.tif("a.tif",np.full((8,4),2),from_origin(0,80,10,10))
        b=self.tif("b.tif",np.full((8,4),9),from_origin(40,80,10,10))
        out=self.raster([a,b],from_origin(0,80,20,20),4,4)
        np.testing.assert_array_equal(out[:,:4],2)
        np.testing.assert_array_equal(out[:,4:],9)

    def test_north_south_and_different_resolution(self):
        a=self.tif("a.tif",np.full((2,4),2),from_origin(0,80,20,20))
        b=self.tif("b.tif",np.full((4,8),9),from_origin(0,40,10,10))
        out=self.raster([a,b],from_origin(0,80,20,20),4,4)
        np.testing.assert_array_equal(out[:4],2)
        np.testing.assert_array_equal(out[4:],9)

    def test_block_independence(self):
        data=np.arange(64,dtype="uint8").reshape(8,8)%10
        a=self.tif("a.tif",data,from_origin(0,80,10,10))
        t=from_origin(0,80,20,20)
        np.testing.assert_array_equal(self.raster([a],t,4,4,1),self.raster([a],t,4,4,4))

    def test_missing_georeference_and_coverage_rejected(self):
        a=self.tif("a.tif",np.zeros((4,4)),from_origin(0,80,10,10),None)
        with self.assertRaises(ValueError):pruefe_kachel(a)
        b=self.tif("b.tif",np.zeros((4,4)),from_origin(0,80,10,10))
        with self.assertRaises(ValueError):self.raster([b],from_origin(0,80,20,20),4,4)

    def test_fraction_and_no_class_average(self):
        data=np.array([[2,9],[0,0]],dtype="uint8")
        a=self.tif("a.tif",data,from_origin(0,20,10,10))
        out=self.raster([a],from_origin(0,20,20,20),1,1)
        self.assertEqual(.5,(out>0).mean())
        self.assertEqual(.25,(out==2).mean())
        self.assertEqual(.25,(out==9).mean())

if __name__ == "__main__":unittest.main()
