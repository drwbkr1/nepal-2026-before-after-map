#!/usr/bin/env python3
"""Render a lightweight M1 review map from draft AOIs and catalog footprints."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as PlotPolygon

ROOT = Path(__file__).resolve().parents[1]
AOI_PATH = ROOT / "config/aoi/draft-study-areas.geojson"
FOOTPRINT_PATH = ROOT / "records/source-gates/candidate-footprints.geojson"
OUTPUT = ROOT / "docs/assets/m1-aoi-footprint-review.png"


def rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        return [ring for polygon in geometry["coordinates"] for ring in polygon]
    raise ValueError(f"Unsupported geometry: {geometry['type']}")


def footprint_style(properties: dict[str, Any]) -> tuple[str, str]:
    if properties.get("platform") == "SENTINEL-2":
        stem = properties["product_stem"]
        return ("#d97706", "Sentinel-2 RUM") if "T45RUM" in stem else (
            "#64748b", "Sentinel-2 RUL"
        )
    return ("#2563eb", "Sentinel-1 ascending") if (
        properties.get("orbit_direction") == "ASCENDING"
    ) else ("#7c3aed", "Sentinel-1 descending")


def draw(ax: Any, aois: dict[str, Any], footprints: dict[str, Any], zoom: bool) -> None:
    seen_labels: set[str] = set()
    for feature in footprints["features"]:
        color, label = footprint_style(feature["properties"])
        for ring in rings(feature["geometry"]):
            ax.add_patch(PlotPolygon(
                ring,
                closed=True,
                fill=False,
                edgecolor=color,
                linewidth=1.0,
                alpha=0.38,
                label=label if label not in seen_labels else None,
            ))
        seen_labels.add(label)

    aoi_colors = {
        "AOI-OVERVIEW-DRAFT": "#111827",
        "AOI-SOURCE-DRAFT": "#dc2626",
        "AOI-UPPER-CORRIDOR-DRAFT": "#059669",
    }
    for feature in aois["features"]:
        aoi_id = feature["properties"]["aoi_id"]
        color = aoi_colors[aoi_id]
        ring = feature["geometry"]["coordinates"][0]
        ax.add_patch(PlotPolygon(
            ring,
            closed=True,
            fill=True,
            facecolor=color,
            edgecolor=color,
            linewidth=2.0,
            alpha=0.10 if aoi_id == "AOI-OVERVIEW-DRAFT" else 0.18,
        ))
        bbox = feature["bbox"]
        if zoom and aoi_id == "AOI-OVERVIEW-DRAFT":
            continue
        ax.text(
            (bbox[0] + bbox[2]) / 2,
            (bbox[1] + bbox[3]) / 2,
            feature["properties"]["name"],
            color=color,
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="center",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 1.5},
        )

    if zoom:
        ax.set_xlim(85.18, 85.68)
        ax.set_ylim(28.00, 28.46)
        ax.set_title("Draft source and upper-corridor review")
    else:
        ax.set_xlim(84.55, 86.20)
        ax.set_ylim(27.55, 29.05)
        ax.set_title("Candidate product footprints and draft AOIs")
    center_lat = sum(ax.get_ylim()) / 2
    ax.set_aspect(1 / math.cos(math.radians(center_lat)))
    ax.grid(True, color="#cbd5e1", linewidth=0.5, alpha=0.8)
    ax.set_xlabel("Longitude (EPSG:4326 review coordinates)")
    ax.set_ylabel("Latitude")


def main() -> None:
    aois = json.loads(AOI_PATH.read_text(encoding="utf-8"))
    footprints = json.loads(FOOTPRINT_PATH.read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.5))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.82, bottom=0.23, wspace=0.24)
    draw(axes[0], aois, footprints, zoom=False)
    draw(axes[1], aois, footprints, zoom=True)
    legend = [
        Line2D([0], [0], color="#2563eb", lw=2, label="Sentinel-1 ascending"),
        Line2D([0], [0], color="#7c3aed", lw=2, label="Sentinel-1 descending"),
        Line2D([0], [0], color="#d97706", lw=2, label="Sentinel-2 RUM"),
        Line2D([0], [0], color="#64748b", lw=2, label="Sentinel-2 RUL"),
        Patch(facecolor="#dc2626", alpha=0.20, edgecolor="#dc2626", label="Draft source AOI"),
        Patch(facecolor="#059669", alpha=0.20, edgecolor="#059669", label="Draft upper corridor"),
        Patch(facecolor="#111827", alpha=0.10, edgecolor="#111827", label="Draft overview"),
    ]
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.075),
        ncol=4,
        frameon=False,
    )
    fig.suptitle(
        "Nepal 2026 M1 geometry review\n"
        "Catalog footprints and rectangular planning AOIs — not pixel coverage or event attribution",
        fontsize=14,
        fontweight="bold",
        y=0.96,
    )
    fig.text(
        0.5,
        0.02,
        "GeoJSON review coordinates are WGS84. Approved analytical geometry will be projected to EPSG:32645.",
        ha="center",
        fontsize=9,
        color="#334155",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(OUTPUT)


if __name__ == "__main__":
    main()
