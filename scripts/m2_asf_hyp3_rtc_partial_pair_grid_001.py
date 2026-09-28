"""No-resampling EPSG:32645 RTC grid alignment for a local partial panel.

GDAL readers in this module are lazy. Real provider pixels require a separate
published execution gate; tests use only generated disposable rasters.
"""

from __future__ import annotations

import math

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_core_001 import check_pair_grids


CELL_M = 10.0
MAX_DISPLAY_CELLS = 20_000_000


def choose_target_grid(before: dict, after: dict, rings: list[list[list[float]]],
                       contract: dict) -> dict:
    """Snap the two approved AOIs' union bounds to the first grid's 10 m cells."""
    if check_pair_grids(before, after, contract)["status"] != "pass_grid_for_local_visual_only":
        raise ValueError("partial_pair_grids_incompatible")
    if (
        abs(before["cell_size_x"] - CELL_M) > 1e-6
        or abs(before["cell_size_y"] - CELL_M) > 1e-6
        or not isinstance(rings, list) or len(rings) != 2
        or any(not isinstance(ring, list) or len(ring) < 4
               or ring[0] != ring[-1]
               or any(not isinstance(point, list) or len(point) != 2
                      or any(type(v) not in (int, float) or not math.isfinite(v)
                             for v in point) for point in ring)
               for ring in rings)
    ):
        raise ValueError("partial_pair_target_input_invalid")
    xs = [point[0] for ring in rings for point in ring]
    ys = [point[1] for ring in rings for point in ring]
    xmin = before["origin_x"] + math.floor((min(xs) - before["origin_x"]) / CELL_M) * CELL_M
    xmax = before["origin_x"] + math.ceil((max(xs) - before["origin_x"]) / CELL_M) * CELL_M
    ymax = before["origin_y"] - math.floor((before["origin_y"] - max(ys)) / CELL_M) * CELL_M
    ymin = before["origin_y"] - math.ceil((before["origin_y"] - min(ys)) / CELL_M) * CELL_M
    width = round((xmax - xmin) / CELL_M)
    height = round((ymax - ymin) / CELL_M)
    if width <= 0 or height <= 0 or width * height > MAX_DISPLAY_CELLS:
        raise ValueError("partial_pair_target_too_large_or_empty")
    return {"wkid": 32645, "xmin": xmin, "ymin": ymin,
            "xmax": xmax, "ymax": ymax, "width": width,
            "height": height, "cell_size_m": CELL_M,
            "resampling_performed": False}


def read_band_on_target(dataset, target: dict, *, fill: float | int,
                        dtype) -> np.ndarray:
    """Read only intersecting native cells; pad uncovered cells with fill."""
    if target.get("wkid") != 32645 or target.get("cell_size_m") != CELL_M:
        raise ValueError("partial_pair_target_invalid")
    width, height = target["width"], target["height"]
    if (type(width) is not int or type(height) is not int
            or width <= 0 or height <= 0 or width * height > MAX_DISPLAY_CELLS):
        raise ValueError("partial_pair_target_invalid")
    gt = dataset.GetGeoTransform()
    if (gt is None or len(gt) != 6 or abs(gt[1] - CELL_M) > 1e-6
            or abs(gt[5] + CELL_M) > 1e-6 or gt[2] != 0 or gt[4] != 0):
        raise ValueError("partial_pair_source_grid_invalid")
    dx = (target["xmin"] - gt[0]) / CELL_M
    dy = (gt[3] - target["ymax"]) / CELL_M
    if abs(dx - round(dx)) > 1e-6 or abs(dy - round(dy)) > 1e-6:
        raise ValueError("partial_pair_source_not_aligned")
    source_x_at_target_zero, source_y_at_target_zero = round(dx), round(dy)
    out_x0 = max(0, -source_x_at_target_zero)
    out_y0 = max(0, -source_y_at_target_zero)
    out_x1 = min(width, dataset.RasterXSize - source_x_at_target_zero)
    out_y1 = min(height, dataset.RasterYSize - source_y_at_target_zero)
    output = np.full((height, width), fill, dtype=dtype)
    if out_x1 <= out_x0 or out_y1 <= out_y0:
        return output
    src_x = source_x_at_target_zero + out_x0
    src_y = source_y_at_target_zero + out_y0
    section = dataset.GetRasterBand(1).ReadAsArray(
        src_x, src_y, out_x1 - out_x0, out_y1 - out_y0)
    if section is None or section.shape != (out_y1 - out_y0, out_x1 - out_x0):
        raise ValueError("partial_pair_window_read_invalid")
    output[out_y0:out_y1, out_x0:out_x1] = section
    return output


def rasterize_ring_on_target(ring: list[list[float]], target: dict) -> np.ndarray:
    """Rasterize one projected AOI on the exact shared native grid."""
    from osgeo import gdal, ogr, osr

    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32645)
    linear = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in ring:
        linear.AddPoint_2D(float(x), float(y))
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(linear)
    if polygon.IsEmpty() or not polygon.IsValid():
        raise ValueError("partial_pair_aoi_polygon_invalid")
    raster = gdal.GetDriverByName("MEM").Create(
        "", target["width"], target["height"], 1, gdal.GDT_Byte)
    raster.SetGeoTransform((target["xmin"], CELL_M, 0,
                            target["ymax"], 0, -CELL_M))
    raster.SetSpatialRef(spatial)
    raster.GetRasterBand(1).Fill(0)
    vector = ogr.GetDriverByName("Memory").CreateDataSource("")
    layer = vector.CreateLayer("aoi", spatial, ogr.wkbPolygon)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(polygon)
    layer.CreateFeature(feature)
    feature = None
    if gdal.RasterizeLayer(raster, [1], layer, burn_values=[1]) != 0:
        raise ValueError("partial_pair_aoi_rasterize_failed")
    output = raster.GetRasterBand(1).ReadAsArray()
    if output is None or output.shape != (target["height"], target["width"]):
        raise ValueError("partial_pair_aoi_mask_invalid")
    return output
