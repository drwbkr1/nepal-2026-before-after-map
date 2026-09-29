#!/usr/bin/env python3
"""Pure, predeclared Landsat-9 visual-only geometry and pixel predicates.

No provider access, ArcGIS invocation, file read, or scientific change analysis.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from landsat_c2_qa_flags import decode_qa_pixel, decode_qa_radsat, decode_sr_qa_aerosol

CELL = 30.0
SCALE = 0.0000275
OFFSET = -0.2
REASONS = ("outside_footprint", "fill_nodata", "cloud_cirrus_shadow", "snow_ice",
           "saturation_terrain", "aerosol_uncertainty", "nonphysical_band", "strict_valid")


class PixelMethodError(ValueError):
    pass


def polygon_area(points: Sequence[Sequence[float]]) -> float:
    if len(points) < 4 or points[0] != points[-1]:
        raise PixelMethodError("aoi_ring_invalid")
    area = sum(points[i][0] * points[i + 1][1] - points[i + 1][0] * points[i][1]
               for i in range(len(points) - 1)) / 2.0
    if not math.isfinite(area) or abs(area) <= 0:
        raise PixelMethodError("aoi_area_invalid")
    return abs(area)


def _clip(poly: list[tuple[float, float]], axis: int, bound: float,
          keep_greater: bool) -> list[tuple[float, float]]:
    if not poly:
        return []
    result = []
    previous = poly[-1]
    prev_inside = previous[axis] >= bound if keep_greater else previous[axis] <= bound
    for current in poly:
        inside = current[axis] >= bound if keep_greater else current[axis] <= bound
        if inside != prev_inside:
            delta = current[axis] - previous[axis]
            if delta:
                t = (bound - previous[axis]) / delta
                result.append((previous[0] + t * (current[0] - previous[0]),
                               previous[1] + t * (current[1] - previous[1])))
        if inside:
            result.append(current)
        previous, prev_inside = current, inside
    return result


def cell_intersection_area(ring: Sequence[Sequence[float]], west: float, south: float,
                           cell: float = CELL) -> float:
    poly = [(float(x), float(y)) for x, y in ring[:-1]]
    for axis, bound, keep in ((0, west, True), (0, west + cell, False),
                              (1, south, True), (1, south + cell, False)):
        poly = _clip(poly, axis, bound, keep)
    if len(poly) < 3:
        return 0.0
    area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                   - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly))) / 2.0)
    return min(cell * cell, max(0.0, area))


def aoi_cell_weights(ring: Sequence[Sequence[float]], xmin: float, ymax: float,
                     columns: int, rows: int, cell: float = CELL) -> np.ndarray:
    """Exact cell/polygon clipping; no center-point or all-touched approximation."""
    if columns <= 0 or rows <= 0 or cell <= 0:
        raise PixelMethodError("aoi_window_invalid")
    weights = np.zeros((rows, columns), dtype=np.float64)
    # Approved AOIs are small quadrilaterals. Clip only their bounding cells.
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    c0 = max(0, math.floor((min(xs) - xmin) / cell))
    c1 = min(columns, math.ceil((max(xs) - xmin) / cell))
    r0 = max(0, math.floor((ymax - max(ys)) / cell))
    r1 = min(rows, math.ceil((ymax - min(ys)) / cell))
    if c1 <= c0 or r1 <= r0:
        return weights
    # On a convex quadrilateral, a cell with all four corners inside is full.
    vertices = np.asarray(ring[:-1], dtype=np.float64)
    if len(vertices) != 4:
        raise PixelMethodError("aoi_geometry_not_approved_quadrilateral")
    sign = np.sign(sum(vertices[i, 0] * vertices[(i + 1) % 4, 1]
                       - vertices[(i + 1) % 4, 0] * vertices[i, 1]
                       for i in range(4)))
    cc = np.arange(c0, c1)[None, :]
    rr = np.arange(r0, r1)[:, None]
    x = xmin + cc * cell
    y = ymax - rr * cell
    full = np.ones((r1 - r0, c1 - c0), dtype=bool)
    for dx in (0.0, cell):
        for dy in (0.0, -cell):
            inside = np.ones_like(full)
            for i in range(4):
                a, b = vertices[i], vertices[(i + 1) % 4]
                cross = (b[0] - a[0]) * (y + dy - a[1]) - (b[1] - a[1]) * (x + dx - a[0])
                inside &= sign * cross >= -1e-7
            full &= inside
    view = weights[r0:r1, c0:c1]
    view[full] = cell * cell
    for local_r, local_c in np.argwhere(~full):
        col = c0 + int(local_c)
        row = r0 + int(local_r)
        view[local_r, local_c] = cell_intersection_area(
            ring, xmin + col * cell, ymax - (row + 1) * cell, cell)
    expected = polygon_area(ring)
    if abs(float(weights.sum()) - expected) / expected > .02:
        raise PixelMethodError("aoi_area_accounting_invalid")
    return weights


def validate_headers(headers: dict[str, dict[str, dict]]) -> dict:
    """Require eight single-band TIFFs per date and a shared native 30 m lattice."""
    roles = ("QA_PIXEL", "QA_RADSAT", "SR_QA_AEROSOL", "SR_B3", "SR_B4",
             "SR_B5", "SR_B6", "SR_B7")
    if set(headers) != {"before", "after"}:
        raise PixelMethodError("source_roles_invalid")
    grid = {}
    for date in ("before", "after"):
        if set(headers[date]) != set(roles):
            raise PixelMethodError("required_tiff_members_missing")
        reference = headers[date]["SR_B3"]
        for role in roles:
            item = headers[date][role]
            if (item["wkid"] != 32645 or item["bands"] != 1
                    or item["rows"] <= 0 or item["columns"] <= 0
                    or abs(item["cell_x"] - CELL) > 1e-6
                    or abs(item["cell_y"] - CELL) > 1e-6
                    or abs((item["xmax"] - item["xmin"]) - CELL * item["columns"]) > 1e-4
                    or abs((item["ymax"] - item["ymin"]) - CELL * item["rows"]) > 1e-4
                    or item.get("rotation_x", 0) != 0 or item.get("rotation_y", 0) != 0
                    or "nodata" not in item):
                raise PixelMethodError("tiff_header_grid_or_nodata_invalid")
            for field in ("xmin", "ymin", "xmax", "ymax", "rows", "columns"):
                if abs(item[field] - reference[field]) > (1e-4 if field in ("xmin", "ymin", "xmax", "ymax") else 0):
                    raise PixelMethodError("within_scene_grid_mismatch")
        grid[date] = reference
    before, after = grid["before"], grid["after"]
    dx = (after["xmin"] - before["xmin"]) / CELL
    dy = (after["ymax"] - before["ymax"]) / CELL
    if abs(dx - round(dx)) > 1e-6 or abs(dy - round(dy)) > 1e-6:
        raise PixelMethodError("cross_scene_lattice_mismatch")
    if min(before["xmax"], after["xmax"]) <= max(before["xmin"], after["xmin"]) or min(before["ymax"], after["ymax"]) <= max(before["ymin"], after["ymin"]):
        raise PixelMethodError("cross_scene_extent_disjoint")
    return {"before": before, "after": after,
            "after_offset_columns": round(dx), "after_offset_rows": round(dy),
            "registration_residual_measured": False}


def classify_pixels(qa_pixel: np.ndarray, qa_radsat: np.ndarray,
                    aerosol: np.ndarray, bands: np.ndarray, footprint: np.ndarray,
                    nodata: Sequence[int]) -> dict:
    """Classify each cell once in frozen order and retain overlapping raw flags."""
    shape = qa_pixel.shape
    if (qa_radsat.shape != shape or aerosol.shape != shape or footprint.shape != shape
            or bands.shape != (5, *shape) or len(nodata) != 8):
        raise PixelMethodError("pixel_array_shape_invalid")
    q = decode_qa_pixel(qa_pixel)
    r = decode_qa_radsat(qa_radsat)
    a = decode_sr_qa_aerosol(aerosol)
    cloud = (q["dilated_cloud"] | q["high_confidence_cirrus"]
             | q["high_confidence_cloud"] | q["high_confidence_cloud_shadow"]
             | (q["cloud_confidence"] >= 2) | (q["cirrus_confidence"] >= 2)
             | (q["cloud_shadow_confidence"] >= 2))
    snow = q["high_confidence_snow"] | (q["snow_ice_confidence"] >= 2)
    saturation = r["terrain_occlusion"].copy()
    for band in range(3, 8):
        saturation |= r[f"band{band}_saturated"]
    aerosol_risk = ~a["valid_retrieval"] & (a["aerosol_level"] == 3)
    fill = (q["fill"] | a["fill"] | (qa_pixel == 65535) | (qa_radsat == 65535)
            | (aerosol == 255) | (qa_pixel == nodata[0])
            | (qa_radsat == nodata[1]) | (aerosol == nodata[2]))
    calibrated = bands.astype(np.float64) * SCALE + OFFSET
    nonphysical = np.any(~np.isfinite(calibrated) | (calibrated < 0) | (calibrated > 1), axis=0)
    for i in range(5):
        fill |= (bands[i] == 0) | (bands[i] == 65535) | (bands[i] == nodata[i + 3])
    flags = ("outside_footprint", "fill_nodata", "cloud_cirrus_shadow", "snow_ice",
             "saturation_terrain", "aerosol_uncertainty", "nonphysical_band")
    masks = (~footprint, fill, cloud, snow, saturation, aerosol_risk, nonphysical)
    reason = np.full(shape, 7, dtype=np.uint8)
    for i in range(6, -1, -1):
        reason[masks[i]] = i
    raw = {name: mask for name, mask in zip(flags, masks, strict=True)}
    raw.update({"water": q["water"] | a["water"],
                "aerosol_invalid_retrieval": ~a["valid_retrieval"],
                "aerosol_interpolated": a["interpolated"],
                "aerosol_high": a["aerosol_level"] == 3,
                "clear_bit": q["clear_bit"]})
    return {"reason": reason, "raw": raw, "calibrated": calibrated,
            "strict_valid": reason == 7}


def weighted_metrics(weights: np.ndarray, before: dict, after: dict,
                     before_footprint: np.ndarray, after_footprint: np.ndarray) -> dict:
    area = float(weights.sum())
    if area <= 0:
        raise PixelMethodError("aoi_area_invalid")
    output = {"aoi_area_m2": round(area, 3)}
    for date, result, footprint in (("before", before, before_footprint),
                                    ("after", after, after_footprint)):
        valid = result["strict_valid"]
        output[date] = {
            "footprint_fraction": round(float(weights[footprint].sum()) / area, 6),
            "strict_usable_fraction": round(float(weights[valid].sum()) / area, 6),
            "reason_fraction": {name: round(float(weights[result["reason"] == i].sum()) / area, 6)
                                for i, name in enumerate(REASONS)},
            "overlapping_raw_flag_fraction": {name: round(float(weights[mask].sum()) / area, 6)
                                              for name, mask in result["raw"].items()},
        }
        if abs(sum(output[date]["reason_fraction"].values()) - 1) > 1e-5:
            raise PixelMethodError("reason_area_accounting_invalid")
    paired = before["strict_valid"] & after["strict_valid"]
    paired_fraction = float(weights[paired].sum()) / area
    output["paired_strict_usable_fraction"] = round(paired_fraction, 6)
    if all(output[d]["footprint_fraction"] >= .99 for d in ("before", "after")) and paired_fraction >= .2:
        if paired_fraction >= .8 and all(output[d]["strict_usable_fraction"] >= .8 for d in ("before", "after")):
            output["visual_status"] = "pixel_qa_pass_for_visual_comparison_only"
        else:
            output["visual_status"] = "partial_insufficient_for_full_area_comparison"
    else:
        output["visual_status"] = "no_visual_panel_for_aoi"
    return output


def nearest_rank_stretch(values: np.ndarray) -> tuple[float, float]:
    finite = np.sort(np.asarray(values, dtype=np.float64)[np.isfinite(values)])
    if finite.size == 0:
        raise PixelMethodError("stretch_population_empty")
    low = float(finite[max(0, math.ceil(.02 * finite.size) - 1)])
    high = float(finite[max(0, math.ceil(.98 * finite.size) - 1)])
    if high <= low:
        raise PixelMethodError("stretch_range_degenerate")
    return low, high
