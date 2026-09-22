import hashlib
import json
import math
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RADAR_REF = "config/arcgis/radar-catalog-footprints-epsg32645.json"
DEM_REF = "config/arcgis/approved-dem-tile-boxes-epsg32645.json"
PNG_REF = "docs/assets/radar-catalog-dem-coverage-epsg32645.png"
RECEIPT_REF = "records/observations/m2-radar-catalog-dem-coverage-map-001.json"


class RadarCatalogCoverageMapTests(unittest.TestCase):
    def test_projected_metadata_layers(self):
        radar = json.loads((ROOT / RADAR_REF).read_text(encoding="utf-8"))
        dem = json.loads((ROOT / DEM_REF).read_text(encoding="utf-8"))
        self.assertEqual(radar["spatialReference"]["wkid"], 32645)
        self.assertEqual(dem["spatialReference"]["wkid"], 32645)
        self.assertEqual([f["attributes"]["SOURCE_ID"] for f in radar["features"]],
                         [f"M1-SRC-{i:03d}" for i in range(1, 7)])
        self.assertEqual([f["attributes"]["DEM_ID"] for f in dem["features"]],
                         [f"M2-DEM-{i:03d}" for i in range(1, 5)])
        for layer in (radar, dem):
            self.assertIn("not verified valid-pixel coverage", layer["projectMetadata"]["claimBoundary"])
            for feature in layer["features"]:
                ring = feature["geometry"]["rings"][0]
                self.assertEqual(ring[0], ring[-1])
                self.assertGreater(len(ring), 4)
                self.assertTrue(all(100000 < x < 700000 and 2800000 < y < 3400000 and math.isfinite(x + y)
                                    for x, y in ring))
                area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
                self.assertLess(area, 0)

    def test_preview_and_receipt_bindings(self):
        receipt = json.loads((ROOT / RECEIPT_REF).read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "projected_metadata_context_only_not_arcgis_runtime_validated")
        for item in receipt["input_bindings"] + receipt["outputs"]:
            digest = hashlib.sha256((ROOT / item["ref"]).read_bytes()).hexdigest()
            self.assertEqual(item["sha256"], digest)
        self.assertEqual(receipt["checks"]["proj_network"], "OFF")
        self.assertEqual([row["feature_count"] for row in receipt["checks"]["ogr_reopen"]], [6, 4])
        with (ROOT / PNG_REF).open("rb") as stream:
            header = stream.read(24)
        self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", header[16:24]), (2520, 1260))


if __name__ == "__main__":
    unittest.main()
