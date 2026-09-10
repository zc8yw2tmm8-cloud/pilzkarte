import ast
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
import rasterio
from rasterio.transform import from_origin
from PIL import Image
from wald_geo import pruefe_kachel

class Cache(unittest.TestCase):
    def test_cache_identity_and_invalid_download(self):
        tree=ast.parse(Path("baumarten.py").read_text(encoding="utf-8"))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="hole_kachel")
        ns=dict(os=os,json=json,hashlib=hashlib,io=io,Image=Image,
                pruefe_kachel=pruefe_kachel,BASIS="https://example.invalid",EBENE="test",HEADERS={})
        requests=SimpleNamespace(get=Mock())
        ns['requests']=requests
        exec(compile(ast.Module(body=[fn],type_ignores=[]),"baumarten.py","exec"),ns)
        with tempfile.TemporaryDirectory() as tmp:
            pfad=str(Path(tmp)/"test.tif")
            with rasterio.open(pfad,"w",driver="GTiff",width=40,height=40,count=1,
                               dtype="uint8",crs="EPSG:4326",transform=from_origin(10,53,.025,.025)) as dst:
                dst.write(np.zeros((40,40),dtype="uint8"),1)
            data=Path(pfad).read_bytes()
            cache={"anfrage":{"quelle":ns['BASIS'],"ebene":"test","gebiet":[52,10,53,11],"groesse":[40,40]},
                   "geografie":pruefe_kachel(pfad),"sha256":hashlib.sha256(data).hexdigest()}
            Path(pfad+".json").write_text(json.dumps(cache))
            self.assertTrue(ns['hole_kachel'](52,10,53,11,40,40,pfad)[0])
            requests.get.assert_not_called()
            requests.get.return_value=SimpleNamespace(status_code=200,headers={'Content-Type':'image/tiff'},content=b'x'*1500)
            self.assertFalse(ns['hole_kachel'](52,10,53,12,40,40,pfad)[0])
            self.assertEqual(3,requests.get.call_count)
            self.assertEqual(data,Path(pfad).read_bytes())
            requests.get.reset_mock()
            Path(pfad+".json").unlink()
            self.assertFalse(ns['hole_kachel'](52,10,53,11,40,40,pfad)[0])
            self.assertEqual(3,requests.get.call_count)

if __name__ == '__main__':unittest.main()
