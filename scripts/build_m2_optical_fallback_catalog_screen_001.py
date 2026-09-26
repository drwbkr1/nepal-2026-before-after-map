#!/usr/bin/env python3
"""Local, metadata-only EPSG:32645 optical candidate screen; no source adoption.

Reads only versioned repository catalog, AOI, and prior exact-source binding.
Writes one distinct append-only GeoPackage and receipt under local scratch.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json"
AOI = ROOT / "config/aoi/approved-study-areas.geojson"
EXACT_OLD_PAIR = ROOT / "contracts/milestone-002-optical-gdal-header-pixel-recovery-002-proposal.json"
OLD_QA = ROOT / "records/readiness/m2-optical-gdal-header-pixel-recovery-002-terminal.json"
OUT = ROOT / "scratch/optical-fallback-catalog-screen-001"
GPKG = OUT / "Optical_Fallback_Catalog_Metadata_EPSG32645.gpkg"
RECEIPT = OUT / "receipt.json"
EXPECTED_CATALOG_SHA256 = "0ffd82483be80f5f75bd8a41da7379f58dbb6ed33db3ca451e89013e7f05072c"
EXPECTED_AOI_SHA256 = "17af33b60f59faef3a8f9cb2a44978a4e241e00d7329ee99076cce688073bd98"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, record: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _srs(osr, epsg: int):
    value = osr.SpatialReference()
    if value.ImportFromEPSG(epsg) != 0:
        raise RuntimeError("epsg_import_failed")
    value.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return value


def _projected_geometry(ogr, geometry: dict, transform):
    value = ogr.CreateGeometryFromJson(json.dumps(geometry, separators=(",", ":")))
    if value is None or not value.IsValid() or value.IsEmpty():
        raise RuntimeError("catalog_or_aoi_geometry_invalid")
    if value.Transform(transform) != 0 or not value.IsValid() or value.IsEmpty():
        raise RuntimeError("catalog_or_aoi_projection_failed")
    return value


def _add_fields(ogr, layer, fields):
    for name, field_type in fields:
        if layer.CreateField(ogr.FieldDefn(name, field_type)) != 0:
            raise RuntimeError("gpkg_field_create_failed")


def _feature(ogr, layer, geometry, values):
    item = ogr.Feature(layer.GetLayerDefn())
    item.SetGeometry(geometry)
    for key, value in values.items():
        if value is not None:
            item.SetField(key, value)
    if layer.CreateFeature(item) != 0:
        raise RuntimeError("gpkg_feature_create_failed")


def run() -> dict:
    if OUT.exists():
        raise RuntimeError("append_only_optical_screen_identity_collision")
    if sha(CATALOG) != EXPECTED_CATALOG_SHA256 or sha(AOI) != EXPECTED_AOI_SHA256:
        raise RuntimeError("versioned_catalog_or_aoi_drift")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    aoi = json.loads(AOI.read_text(encoding="utf-8"))
    old_pair = json.loads(EXACT_OLD_PAIR.read_text(encoding="utf-8"))
    old_qa = json.loads(OLD_QA.read_text(encoding="utf-8"))
    old_ids = {item["provider_product_id"] for item in old_pair["exact_existing_sources"]}
    if (len(old_ids) != 2 or old_qa.get("pixel_status") != "block"
            or len(catalog["rows"]) != 85):
        raise RuntimeError("prior_optical_identity_or_terminal_drift")
    from osgeo import ogr, osr  # type: ignore

    geographic, projected = _srs(osr, 4326), _srs(osr, 32645)
    transform = osr.CoordinateTransformation(geographic, projected)
    aois = {feature["properties"]["aoi_id"]: _projected_geometry(
        ogr, feature["geometry"], transform) for feature in aoi["features"]}
    if set(aois) != {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
        raise RuntimeError("approved_aoi_set_changed")
    selected = [row for row in catalog["rows"] if
                row["aoi_footprint_intersects"]["AOI-SOURCE"]
                and row["aoi_footprint_intersects"]["AOI-UPPER-CORRIDOR"]]
    if (len(selected) != 29 or Counter(row["window"] for row in selected) !=
            {"before": 14, "after": 15}):
        raise RuntimeError("catalog_candidate_cohort_changed")
    if len({row["provider_product_id"] for row in selected}) != len(selected):
        raise RuntimeError("duplicate_catalog_product_id")
    OUT.mkdir(parents=True, exist_ok=False)
    driver = ogr.GetDriverByName("GPKG")
    datasource = driver.CreateDataSource(str(GPKG))
    if datasource is None:
        raise RuntimeError("gpkg_create_failed")
    observations = []
    try:
        aoi_layer = datasource.CreateLayer("Approved_AOIs", srs=projected,
                                            geom_type=ogr.wkbPolygon)
        _add_fields(ogr, aoi_layer, [("AOI_ID", ogr.OFTString),
                                     ("Evidence", ogr.OFTString)])
        for aoi_id, geometry in aois.items():
            _feature(ogr, aoi_layer, geometry, {"AOI_ID": aoi_id,
                                                "Evidence": "approved search/review extent"})
        layer = datasource.CreateLayer("Optical_Catalog_Candidates", srs=projected,
                                       geom_type=ogr.wkbPolygon)
        _add_fields(ogr, layer, [("ProductID", ogr.OFTString),
                                  ("Product", ogr.OFTString),
                                  ("Window", ogr.OFTString),
                                  ("AcquiredUTC", ogr.OFTString),
                                  ("CloudPct", ogr.OFTReal),
                                  ("SourceFrac", ogr.OFTReal),
                                  ("CorridorFrac", ogr.OFTReal),
                                  ("OverviewFrac", ogr.OFTReal),
                                  ("PriorQA", ogr.OFTString),
                                  ("PixelFitness", ogr.OFTString),
                                  ("Adoption", ogr.OFTString)])
        for row in selected:
            geometry = _projected_geometry(ogr, row["footprint"], transform)
            fractions = {key: round(geometry.Intersection(area).GetArea() / area.GetArea(), 6)
                         for key, area in aois.items()}
            if any(not 0 <= value <= 1.000001 for value in fractions.values()):
                raise RuntimeError("projected_fraction_invalid")
            previously_assessed = row["provider_product_id"] in old_ids
            values = {"ProductID": row["provider_product_id"],
                      "Product": row["name"], "Window": row["window"],
                      "AcquiredUTC": row["content_start_utc"],
                      "CloudPct": row["catalog_cloud_cover_percent"],
                      "SourceFrac": fractions["AOI-SOURCE"],
                      "CorridorFrac": fractions["AOI-UPPER-CORRIDOR"],
                      "OverviewFrac": fractions["AOI-OVERVIEW"],
                      "PriorQA": "BLOCKED_EXACT_PAIR" if previously_assessed else "NOT_TESTED",
                      "PixelFitness": "BLOCKED_EXACT_PAIR" if previously_assessed else "UNKNOWN",
                      "Adoption": "NONE"}
            _feature(ogr, layer, geometry, values)
            observations.append({"provider_product_id": row["provider_product_id"],
                                 "window": row["window"],
                                 "acquired_utc": row["content_start_utc"],
                                 "catalog_cloud_cover_percent": row["catalog_cloud_cover_percent"],
                                 "footprint_fraction": fractions,
                                 "previous_exact_pair_qa": values["PriorQA"],
                                 "pixel_fitness": values["PixelFitness"],
                                 "source_adoption": "none"})
    finally:
        datasource = None
    reopened = ogr.Open(str(GPKG), update=0)
    if reopened is None:
        raise RuntimeError("gpkg_reopen_failed")
    try:
        candidate_layer = reopened.GetLayerByName("Optical_Catalog_Candidates")
        aoi_layer = reopened.GetLayerByName("Approved_AOIs")
        if candidate_layer.GetFeatureCount() != 29 or aoi_layer.GetFeatureCount() != 3:
            raise RuntimeError("gpkg_reopened_feature_count_mismatch")
        for layer in (candidate_layer, aoi_layer):
            if layer.GetSpatialRef().GetAuthorityCode(None) != "32645":
                raise RuntimeError("gpkg_reopened_crs_mismatch")
    finally:
        reopened = None
    with sqlite3.connect(f"file:{GPKG.as_posix()}?mode=ro", uri=True) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("gpkg_sqlite_integrity_failed")
    result = {"schema_version": "1.0", "status": "pass_local_projected_catalog_metadata_screen_only",
              "catalog_ref": str(CATALOG.relative_to(ROOT)).replace("\\", "/"),
              "catalog_sha256": sha(CATALOG), "aoi_sha256": sha(AOI),
              "old_exact_pair_binding_sha256": sha(EXACT_OLD_PAIR),
              "old_pixel_qa_terminal_sha256": sha(OLD_QA),
              "gpkg_ref": str(GPKG.relative_to(ROOT)).replace("\\", "/"),
              "gpkg_sha256": sha(GPKG), "gpkg_size_bytes": GPKG.stat().st_size,
              "analysis_wkid": 32645, "candidate_count": 29,
              "window_counts": {"before": 14, "after": 15},
              "prior_blocked_product_count": sum(item["previous_exact_pair_qa"] == "BLOCKED_EXACT_PAIR"
                                                 for item in observations),
              "candidates": observations,
              "claim_boundary": "Footprint area and tile cloud are metadata. No AOI clear-pixel, mask, registration, source adoption, change, or event attribution is established.",
              "external_network_or_credentials_used": False,
              "protected_product_or_dem_pixels_read": False,
              "new_source_adopted": False,
              "baseline_or_change_analysis_performed": False}
    write_new(RECEIPT, result)
    return result


if __name__ == "__main__":
    value = run()
    print(json.dumps({"status": value["status"],
                      "candidates": value["candidate_count"],
                      "prior_blocked": value["prior_blocked_product_count"]}))
