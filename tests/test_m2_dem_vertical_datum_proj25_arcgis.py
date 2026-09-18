from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

HAS_ARCGIS = importlib.util.find_spec("arcpy") is not None and importlib.util.find_spec("osgeo") is not None


@unittest.skipUnless(HAS_ARCGIS, "requires the existing ArcGIS Pro Python runtime")
class DemVerticalDatumProj25ArcGISTests(unittest.TestCase):
    def test_exact_official_metadata_representation_is_accepted_in_arcgis_runtime(self) -> None:
        from osgeo import gdal

        from m2_dem_vertical_datum_proj25_core import (
            EXPECTED_GRID_COPYRIGHT,
            EXPECTED_GRID_DESCRIPTION,
            inspect_arcgis_readability,
            inspect_grid,
        )

        os.environ["PROJ_NETWORK"] = "OFF"
        gdal.UseExceptions()
        scratch = ROOT / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            grid = Path(temporary) / "synthetic-official-metadata-grid.tif"
            driver = gdal.GetDriverByName("GTiff")
            dataset = driver.Create(
                str(grid), 8640, 4321, 1, gdal.GDT_Float32,
                options=["TILED=YES", "SPARSE_OK=YES", "BIGTIFF=YES"],
            )
            self.assertIsNotNone(dataset)
            dataset.SetGeoTransform((-180.02083333333334, 1.0 / 24.0, 0.0, 90.02083333333333, 0.0, -1.0 / 24.0))
            dataset.SetMetadataItem("AREA_OR_POINT", "Point")
            dataset.SetMetadataItem("TIFFTAG_IMAGEDESCRIPTION", EXPECTED_GRID_DESCRIPTION)
            dataset.SetMetadataItem("TIFFTAG_COPYRIGHT", EXPECTED_GRID_COPYRIGHT)
            band = dataset.GetRasterBand(1)
            band.SetMetadataItem("TYPE", "VERTICAL_OFFSET_GEOGRAPHIC_TO_VERTICAL")
            band.SetMetadataItem("area_of_use", "World")
            band.SetMetadataItem("target_crs_epsg_code", "3855")
            dataset.FlushCache()
            dataset = None

            metadata = inspect_grid(grid)
            self.assertIsNone(metadata["source_crs"])
            self.assertIsNone(metadata["target_crs"])
            self.assertEqual(metadata["tiff_tag_imagedescription"], EXPECTED_GRID_DESCRIPTION)
            self.assertEqual(metadata["target_crs_epsg_code"], "3855")
            readable = inspect_arcgis_readability(grid)
            self.assertTrue(readable["readable"])
            self.assertEqual(readable["width"], 8640)
            self.assertEqual(readable["height"], 4321)
            self.assertEqual(readable["band_count"], 1)

    def test_synthetic_inverse_grid_conversion_is_sign_correct_and_arcgis_readable(self) -> None:
        import numpy as np
        from osgeo import gdal, osr

        from convert_m2_dem_vertical_datum_proj25 import arcgis_readability, verify_staged_output
        from m2_dem_vertical_datum_proj25_core import vertical_pipeline

        os.environ["PROJ_NETWORK"] = "OFF"
        gdal.UseExceptions()
        scratch = ROOT / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            base = Path(temporary)
            grid, source, output = base / "synthetic-grid.tif", base / "source.tif", base / "output.tif"
            driver = gdal.GetDriverByName("GTiff")
            srs_4979 = osr.SpatialReference()
            srs_4979.ImportFromEPSG(4979)
            srs_4979.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            grid_dataset = driver.Create(str(grid), 9, 5, 1, gdal.GDT_Float32)
            grid_dataset.SetGeoTransform((-202.5, 45.0, 0.0, 112.5, 0.0, -45.0))
            grid_dataset.SetSpatialRef(srs_4979)
            grid_dataset.SetMetadataItem("AREA_OR_POINT", "Point")
            grid_dataset.GetRasterBand(1).WriteArray(np.full((5, 9), -40.0, dtype=np.float32))
            grid_dataset = None

            srs_4326 = osr.SpatialReference()
            srs_4326.ImportFromEPSG(4326)
            srs_4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            source_dataset = driver.Create(str(source), 8, 8, 1, gdal.GDT_Float32)
            source_dataset.SetGeoTransform((84.0, 0.25, 0.0, 29.0, 0.0, -0.25))
            source_dataset.SetSpatialRef(srs_4326)
            values = np.full((8, 8), 1000.0, dtype=np.float32)
            values[0, 0] = -9999.0
            source_dataset.GetRasterBand(1).SetNoDataValue(-9999.0)
            source_dataset.GetRasterBand(1).WriteArray(values)
            source_dataset = None
            source_before = hashlib.sha256(source.read_bytes()).hexdigest()

            options = gdal.WarpOptions(
                format="GTiff",
                srcSRS="EPSG:9518",
                dstSRS="EPSG:4979",
                coordinateOperation=vertical_pipeline(grid),
                outputBounds=(84.0, 27.0, 86.0, 29.0),
                width=8,
                height=8,
                resampleAlg="near",
                srcNodata=-9999.0,
                dstNodata=-9999.0,
                outputType=gdal.GDT_Float32,
                creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3"],
                warpOptions=["INIT_DEST=NO_DATA"],
            )
            converted = gdal.Warp(str(output), str(source), options=options)
            self.assertIsNotNone(converted)
            converted.FlushCache()
            converted = None
            output_dataset = gdal.Open(str(output))
            observed = output_dataset.GetRasterBand(1).ReadAsArray()
            output_dataset = None
            self.assertTrue(np.allclose(observed[1:, 1:], 1040.0, atol=0.001))
            verification = verify_staged_output(source, output)
            self.assertEqual(verification["approved_aoi_nonfinite_count"], 0)
            self.assertAlmostEqual(verification["correction_m"]["sampled_p50"], 40.0, places=3)
            readable = arcgis_readability(output, 8, 8)
            self.assertTrue(readable["readable"])
            self.assertEqual(readable["width"], 8)
            self.assertEqual(source_before, hashlib.sha256(source.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
