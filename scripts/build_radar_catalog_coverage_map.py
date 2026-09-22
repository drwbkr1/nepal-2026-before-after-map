#!/usr/bin/env python3
"""Project approved catalog polygons and render a metadata-only coverage preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

os.environ["PROJ_NETWORK"] = "OFF"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as PlotPolygon
from osgeo import gdal, ogr, osr

osr.UseExceptions()
ogr.UseExceptions()


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REF = "records/source-manifest.json"
SOURCE_APPROVAL_REF = "records/source-gates/source-manifest-approval.json"
DEM_REF = "records/source-gates/m2-dem-candidate-manifest.json"
DEM_APPROVAL_REF = "records/source-gates/m2-dem-amendment-approval.json"
AOI_REF = "config/aoi/approved-study-areas-epsg32645.json"
RADAR_OUT = "config/arcgis/radar-catalog-footprints-epsg32645.json"
DEM_OUT = "config/arcgis/approved-dem-tile-boxes-epsg32645.json"
PNG_OUT = "docs/assets/radar-catalog-dem-coverage-epsg32645.png"
RECEIPT_OUT = "records/observations/m2-radar-catalog-dem-coverage-map-001.json"
SOURCE_IDS = tuple(f"M1-SRC-{i:03d}" for i in range(1, 7))
DEM_IDS = tuple(f"M2-DEM-{i:03d}" for i in range(1, 5))
DEM_BOXES = (
    (84.0, 27.0, 85.0, 28.0),
    (85.0, 27.0, 86.0, 28.0),
    (84.0, 28.0, 85.0, 29.0),
    (85.0, 28.0, 86.0, 29.0),
)


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def write_json(ref: str, value: dict) -> None:
    path = ROOT / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def signed_double_area(points: list[list[float]]) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:]))


def project_ring(ring: list[list[float]], forward, inverse) -> list[list[float]]:
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError("expected closed polygon ring")
    dense = []
    for start, end in zip(ring, ring[1:]):
        segments = max(1, math.ceil(max(abs(end[0] - start[0]), abs(end[1] - start[1])) / 0.05))
        for step in range(segments):
            fraction = step / segments
            dense.append((start[0] + fraction * (end[0] - start[0]), start[1] + fraction * (end[1] - start[1])))
    dense.append((float(ring[-1][0]), float(ring[-1][1])))
    projected = []
    for lon, lat in dense:
        x, y, _ = forward.TransformPoint(lon, lat)
        back_lon, back_lat, _ = inverse.TransformPoint(x, y)
        if max(abs(back_lon - lon), abs(back_lat - lat)) > 1e-7:
            raise ValueError("projection round-trip exceeds tolerance")
        projected.append([round(x, 6), round(y, 6)])
    projected[-1] = projected[0]
    if signed_double_area(projected) > 0:
        projected = list(reversed(projected))
    if not all(math.isfinite(value) for point in projected for value in point):
        raise ValueError("nonfinite projected coordinate")
    return projected


def feature_set(name: str, fields: list[dict], features: list[dict], input_refs: list[dict]) -> dict:
    return {
        "objectIdFieldName": "",
        "uniqueIdField": {"name": fields[0]["name"], "isSystemMaintained": False},
        "globalIdFieldName": "",
        "geometryType": "esriGeometryPolygon",
        "spatialReference": {"wkid": 32645, "latestWkid": 32645},
        "fields": fields,
        "features": features,
        "projectMetadata": {
            "layerName": name,
            "inputBindings": input_refs,
            "sourceCrs": "EPSG:4326",
            "analysisCrs": "EPSG:32645",
            "projectionEngine": f"GDAL {gdal.VersionInfo('RELEASE_NAME')} / PROJ {osr.GetPROJVersionMajor()}.{osr.GetPROJVersionMinor()}",
            "edgeDensification": "linear WGS84 catalog edges sampled at <=0.05 degree before projection",
            "sourceNotice": "Source metadata: Copernicus Data Space Ecosystem Sentinel-1 catalog and Copernicus DEM STAC; project-approved AOIs.",
            "claimBoundary": "Catalog footprint or DEM tile box, not verified valid-pixel coverage or mapped change.",
        },
    }


def draw_polygon(ax, ring: list[list[float]], **kwargs) -> None:
    ax.add_patch(PlotPolygon([(x / 1000, y / 1000) for x, y in ring], closed=True, **kwargs))


def render(radar: dict, dem: dict, aois: dict, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={"width_ratios": [1.25, 1]})
    fig.patch.set_facecolor("#f8fafc")
    aoi_rings = [feature["geometry"]["rings"][0] for feature in aois["features"]]
    for ax in axes:
        ax.set_facecolor("white")
        for feature in dem["features"]:
            draw_polygon(ax, feature["geometry"]["rings"][0], facecolor="#b7e4c7", edgecolor="#238b45", linewidth=1.2, alpha=0.45, zorder=1)
        for feature in radar["features"]:
            before = feature["attributes"]["EVENT_ROLE"] == "before"
            draw_polygon(ax, feature["geometry"]["rings"][0], facecolor="none", edgecolor="#2563eb" if before else "#d97706", linestyle="-" if before else "--", linewidth=1.3, alpha=0.75, zorder=2)
        for index, ring in enumerate(aoi_rings):
            draw_polygon(ax, ring, facecolor="none", edgecolor="#dc2626" if index == 0 else "#991b1b", linewidth=2 if index == 0 else 1.4, zorder=4)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, color="#e2e8f0", linewidth=0.6)
        ax.set_xlabel("Easting (km), WGS 84 / UTM zone 45N")
        ax.set_ylabel("Northing (km)")
    all_points = [point for feature in radar["features"] + dem["features"] for point in feature["geometry"]["rings"][0]]
    xs = [point[0] / 1000 for point in all_points]
    ys = [point[1] / 1000 for point in all_points]
    axes[0].set_xlim(min(xs) - 15, max(xs) + 15)
    axes[0].set_ylim(min(ys) - 15, max(ys) + 15)
    axes[0].set_title("Approved radar catalog swaths and DEM tile boxes")
    for index, label in enumerate(("001 / 004", "002 / 005", "003 / 006")):
        ring = radar["features"][index]["geometry"]["rings"][0][:-1]
        center_x = sum(point[0] for point in ring) / len(ring) / 1000
        center_y = sum(point[1] for point in ring) / len(ring) / 1000
        axes[0].text(center_x, center_y, label, ha="center", va="center", fontsize=9,
                     fontweight="bold", color="#1e293b",
                     bbox={"facecolor": "white", "edgecolor": "#94a3b8", "boxstyle": "round,pad=0.2", "alpha": 0.85},
                     zorder=6)
    aoi_points = [point for ring in aoi_rings for point in ring]
    ax = [point[0] / 1000 for point in aoi_points]
    ay = [point[1] / 1000 for point in aoi_points]
    axes[1].set_xlim(min(ax) - 15, max(ax) + 15)
    axes[1].set_ylim(min(ay) - 15, max(ay) + 15)
    axes[1].set_title("Approved search and review AOIs")
    handles = [
        Line2D([], [], color="#2563eb", label="Before radar catalog footprint"),
        Line2D([], [], color="#d97706", linestyle="--", label="After radar catalog footprint"),
        Patch(facecolor="#b7e4c7", edgecolor="#238b45", alpha=0.5, label="Approved DEM tile box"),
        Line2D([], [], color="#dc2626", linewidth=2, label="Approved AOI"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.085))
    fig.suptitle("Nepal 2026 radar and terrain catalog coverage", fontsize=16, fontweight="bold", y=0.985)
    fig.text(0.5, 0.051, "Source metadata: Copernicus Data Space Ecosystem Sentinel-1 catalog and Copernicus DEM STAC; project-approved AOIs", ha="center", fontsize=8.5, color="#475569")
    fig.text(0.5, 0.023, "Metadata context only • boxes and catalog polygons do not prove usable pixels, GTC fitness, or event change", ha="center", fontsize=9, color="#475569")
    fig.subplots_adjust(top=0.89, bottom=0.18, left=0.07, right=0.98, wspace=0.2)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-at-utc", required=True)
    args = parser.parse_args()
    for ref in (RADAR_OUT, DEM_OUT, PNG_OUT, RECEIPT_OUT):
        if (ROOT / ref).exists():
            raise SystemExit(f"output collision: {ref}")
    source = json.loads((ROOT / SOURCE_REF).read_text(encoding="utf-8"))
    source_approval = json.loads((ROOT / SOURCE_APPROVAL_REF).read_text(encoding="utf-8"))
    dem = json.loads((ROOT / DEM_REF).read_text(encoding="utf-8"))
    dem_approval = json.loads((ROOT / DEM_APPROVAL_REF).read_text(encoding="utf-8"))
    aois = json.loads((ROOT / AOI_REF).read_text(encoding="utf-8"))
    if source_approval["status"] != "approved" or source_approval["reviewed_manifest_sha256"] != sha256(SOURCE_REF):
        raise SystemExit("source approval binding differs")
    source_rows = [row for row in source["records"] if row.get("source_id") in SOURCE_IDS]
    if tuple(row["source_id"] for row in source_rows) != SOURCE_IDS:
        raise SystemExit("six radar source identities or order differ")
    if tuple(row["source_id"] for row in dem["records"]) != DEM_IDS or tuple(tuple(row["bbox_wgs84"]) for row in dem["records"]) != DEM_BOXES:
        raise SystemExit("four DEM identities or boxes differ")
    if dem_approval["status"] != "approved" or tuple(dem_approval["authorized_source_ids"]) != DEM_IDS:
        raise SystemExit("DEM approval binding differs")
    if aois["spatialReference"]["wkid"] != 32645 or len(aois["features"]) != 3:
        raise SystemExit("approved projected AOI differs")

    wgs84, utm45 = osr.SpatialReference(), osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    utm45.ImportFromEPSG(32645)
    wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    utm45.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    forward, inverse = osr.CoordinateTransformation(wgs84, utm45), osr.CoordinateTransformation(utm45, wgs84)
    source_bindings = [{"ref": ref, "sha256": sha256(ref)} for ref in (SOURCE_REF, SOURCE_APPROVAL_REF, AOI_REF)]
    dem_bindings = [{"ref": ref, "sha256": sha256(ref)} for ref in (DEM_REF, DEM_APPROVAL_REF, AOI_REF)]
    radar_features = []
    for row in source_rows:
        ring = project_ring(row["footprint"]["coordinates"][0], forward, inverse)
        radar_features.append({
            "attributes": {
                "SOURCE_ID": row["source_id"],
                "EVENT_ROLE": row["event_role"],
                "ANALYSIS_ROLE": row["proposed_disposition"]["analysis_role"],
                "ACQUIRED_UTC": row["acquisition_start_utc"],
                "RECORD_KIND": "catalog_footprint_not_pixel_coverage",
            },
            "geometry": {"rings": [ring], "spatialReference": {"wkid": 32645, "latestWkid": 32645}},
        })
    dem_features = []
    for row in dem["records"]:
        west, south, east, north = row["bbox_wgs84"]
        ring = project_ring([[west, south], [east, south], [east, north], [west, north], [west, south]], forward, inverse)
        dem_features.append({
            "attributes": {"DEM_ID": row["source_id"], "RECORD_KIND": "approved_stac_tile_box_not_valid_pixel_coverage"},
            "geometry": {"rings": [ring], "spatialReference": {"wkid": 32645, "latestWkid": 32645}},
        })
    str_field = lambda name, length: {"name": name, "type": "esriFieldTypeString", "alias": name.replace("_", " ").title(), "length": length}
    radar = feature_set("Approved radar catalog footprints", [str_field("SOURCE_ID", 40), str_field("EVENT_ROLE", 20), str_field("ANALYSIS_ROLE", 80), str_field("ACQUIRED_UTC", 40), str_field("RECORD_KIND", 80)], radar_features, source_bindings)
    dem_set = feature_set("Approved DEM tile boxes", [str_field("DEM_ID", 40), str_field("RECORD_KIND", 80)], dem_features, dem_bindings)
    write_json(RADAR_OUT, radar)
    write_json(DEM_OUT, dem_set)
    ogr_checks = []
    for ref, expected in ((RADAR_OUT, 6), (DEM_OUT, 4)):
        dataset = ogr.Open(str(ROOT / ref))
        if dataset is None or dataset.GetLayerCount() != 1:
            raise SystemExit(f"OGR cannot reopen projected FeatureSet: {ref}")
        layer = dataset.GetLayer(0)
        count = layer.GetFeatureCount()
        wkid = layer.GetSpatialRef().GetAuthorityCode(None) if layer.GetSpatialRef() else None
        if count != expected or wkid != "32645":
            raise SystemExit(f"OGR FeatureSet count or CRS differs: {ref}")
        ogr_checks.append({"ref": ref, "feature_count": count, "epsg": wkid})
        dataset = None
    render(radar, dem_set, aois, ROOT / PNG_OUT)
    receipt = {
        "schema_version": "1.0",
        "observation_id": "NEPAL-M2-RADAR-CATALOG-DEM-COVERAGE-MAP-001",
        "generated_at_utc": args.generated_at_utc,
        "status": "projected_metadata_context_only_not_arcgis_runtime_validated",
        "input_bindings": source_bindings + dem_bindings[:2],
        "outputs": [{"ref": ref, "sha256": sha256(ref)} for ref in (RADAR_OUT, DEM_OUT, PNG_OUT)],
        "checks": {"radar_features": len(radar_features), "dem_box_features": len(dem_features), "approved_aoi_features": len(aois["features"]), "crs": "EPSG:32645", "round_trip_tolerance_degrees": 1e-7, "proj_network": os.environ["PROJ_NETWORK"], "ogr_reopen": ogr_checks},
        "limitations": ["Catalog polygons and STAC DEM boxes are not valid-pixel coverage.", "This PNG is a metadata context preview, not an ArcGIS export or scientific map.", "ArcGIS FeatureSet import and map rendering have not yet been validated in ArcGIS Pro.", "No GTC cause, radar recovery readiness, baseline, or event change is established."],
    }
    write_json(RECEIPT_OUT, receipt)
    print(json.dumps({"status": receipt["status"], "outputs": receipt["outputs"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
