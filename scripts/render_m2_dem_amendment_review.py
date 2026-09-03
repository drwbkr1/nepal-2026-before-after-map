#!/usr/bin/env python3
"""Render the exact four-tile DEM amendment as a human-review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 1580
MARGIN = 80


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def wrapped(draw: ImageDraw.ImageDraw, value: str, box: tuple[int, int, int], text_font: ImageFont.FreeTypeFont, fill: str, spacing: int = 5) -> int:
    left, top, right = box
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textbbox((0, 0), candidate, font=text_font)[2] <= right - left:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    y = top
    for line in lines:
        draw.text((left, y), line, font=text_font, fill=fill)
        y += text_font.size + spacing
    return y


def map_point(lon: float, lat: float, rect: tuple[int, int, int, int]) -> tuple[float, float]:
    left, top, right, bottom = rect
    x = left + (lon - 84.0) / 2.0 * (right - left)
    y = bottom - (lat - 27.0) / 2.0 * (bottom - top)
    return x, y


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    aoi = json.loads(Path("config/aoi/approved-study-areas.geojson").read_text(encoding="utf-8"))
    proposal_sha = sha256(args.proposal)
    license_sha = manifest["license"]["document_sha256"]

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f5f1e8")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, teal, amber, red, line, pale = (
        "#18324a", "#1d252c", "#5e6a72", "#167061", "#9a5d00", "#9a382d", "#c8d0d3", "#fffdf9"
    )

    draw.rectangle((0, 0, WIDTH, 250), fill=navy)
    draw.text((MARGIN, 44), "NEPAL 2026  |  M2 DEM AMENDMENT REVIEW", font=font(28, bold=True), fill="#9fd8d0")
    draw.text((MARGIN, 94), "Four-tile terrain-correction dependency", font=font(46, bold=True), fill="white")
    draw.text((MARGIN, 173), f"Proposal SHA-256  {proposal_sha}", font=font(21), fill="#d7e3ea")

    stats = [
        ("4", "exact COG tiles"),
        (f"{manifest['summary']['combined_content_length_mib']:.3f} MiB", "remote total"),
        ("30 m", "nominal GSD"),
        ("4326 → 32645", "source → analysis CRS"),
    ]
    stat_top = 282
    stat_width = (WIDTH - 2 * MARGIN - 54) // 4
    for index, (value, label) in enumerate(stats):
        x = MARGIN + index * (stat_width + 18)
        draw.rounded_rectangle((x, stat_top, x + stat_width, stat_top + 112), radius=12, fill="white", outline=line)
        draw.text((x + 20, stat_top + 15), value, font=font(31, bold=True), fill=navy)
        draw.text((x + 20, stat_top + 67), label, font=font(18), fill=muted)

    map_rect = (MARGIN, 450, 840, 1110)
    draw.rounded_rectangle(map_rect, radius=14, fill="white", outline=line, width=2)
    draw.text((MARGIN + 25, 420), "APPROVED AOIS AND REQUIRED 1° TILES", font=font(21, bold=True), fill=navy)
    inner = (map_rect[0] + 80, map_rect[1] + 55, map_rect[2] - 50, map_rect[3] - 70)
    draw.rectangle(inner, fill="#edf4f2", outline=navy, width=2)
    for lon in (84, 85, 86):
        x, _ = map_point(lon, 27, inner)
        draw.line((x, inner[1], x, inner[3]), fill="#709390", width=2)
        draw.text((x - 18, inner[3] + 14), f"{lon}°E", font=font(16), fill=muted)
    for lat in (27, 28, 29):
        _, y = map_point(84, lat, inner)
        draw.line((inner[0], y, inner[2], y), fill="#709390", width=2)
        draw.text((inner[0] - 57, y - 11), f"{lat}°N", font=font(16), fill=muted)
    for tile in manifest["records"]:
        west, south, east, north = tile["bbox_wgs84"]
        x1, y1 = map_point(west, north, inner)
        x2, y2 = map_point(east, south, inner)
        draw.text((x1 + 14, y1 + 14), tile["source_id"], font=font(18, bold=True), fill=navy)
    colors = {"AOI-OVERVIEW": red, "AOI-SOURCE": amber, "AOI-UPPER-CORRIDOR": teal}
    for feature in aoi["features"]:
        aoi_id = feature["properties"]["aoi_id"]
        points = feature["geometry"]["coordinates"][0]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        x1, y1 = map_point(min(xs), max(ys), inner)
        x2, y2 = map_point(max(xs), min(ys), inner)
        draw.rectangle((x1, y1, x2, y2), outline=colors[aoi_id], width=5)
    legend_y = inner[3] + 43
    for index, aoi_id in enumerate(("AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR")):
        x = inner[0] + index * 195
        draw.line((x, legend_y, x + 28, legend_y), fill=colors[aoi_id], width=5)
        draw.text((x + 36, legend_y - 11), aoi_id.replace("AOI-", ""), font=font(15), fill=ink)

    right_left = 900
    draw.text((right_left, 420), "WHY A SEPARATE DECISION IS REQUIRED", font=font(21, bold=True), fill=red)
    y = wrapped(draw, "ArcGIS Pro exposes the radar calibration and terrain-correction tools, but those tools require a DEM and the active M2 approval covers only eight Sentinel products.", (right_left, 460, WIDTH - MARGIN), font(23), ink, 7)
    y += 28
    draw.text((right_left, y), "LICENSE GATE", font=font(20, bold=True), fill=amber)
    y += 38
    y = wrapped(draw, "Article 1 requires the user to accept the exact Copernicus WorldDEM-30 license. No acceptance occurred during metadata review.", (right_left, y, WIDTH - MARGIN), font(22), ink, 7)
    y += 18
    draw.text((right_left, y), "License SHA-256", font=font(18, bold=True), fill=navy)
    y += 34
    y = wrapped(draw, license_sha, (right_left, y, WIDTH - MARGIN), font(20), muted, 5)
    y += 23
    draw.text((right_left, y), "APPROVAL WOULD ADD ONLY", font=font(20, bold=True), fill=teal)
    y += 38
    y = wrapped(draw, "Exact license acceptance; anonymous download of these four named COGs; fail-closed integrity and GeoTIFF checks; non-Git custody; use only for approved Sentinel-1 terrain correction and geometry masks.", (right_left, y, WIDTH - MARGIN), font(22), ink, 7)
    y += 23
    draw.text((right_left, y), "STILL OUTSIDE SCOPE", font=font(20, bold=True), fill=red)
    y += 38
    wrapped(draw, "Accounts, CDSE CCM registration or secrets, paid or requester-pays routes, other DEM tiles, raw DEM redistribution, Git storage of rasters, scientific publication, attribution, and emergency guidance.", (right_left, y, WIDTH - MARGIN), font(22), ink, 7)

    table_top = 1170
    draw.text((MARGIN, table_top - 40), "EXACT CANDIDATE ASSETS", font=font(21, bold=True), fill=navy)
    columns = [(MARGIN, 165, "SOURCE"), (245, 910, "EXACT ITEM ID"), (1165, 210, "SIZE"), (1385, 335, "AOI COVERAGE")]
    draw.rectangle((MARGIN, table_top, WIDTH - MARGIN, table_top + 50), fill="#dfe8e8")
    for x, _, label in columns:
        draw.text((x + 10, table_top + 13), label, font=font(17, bold=True), fill=navy)
    y = table_top + 50
    for index, tile in enumerate(manifest["records"]):
        if index % 2 == 0:
            draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + 70), fill=pale)
        draw.line((MARGIN, y + 70, WIDTH - MARGIN, y + 70), fill=line)
        values = [
            tile["source_id"],
            tile["item_id"],
            f"{tile['anonymous_head']['content_length_bytes'] / (1024**2):.3f} MiB",
            ", ".join(value.replace("AOI-", "") for value in tile["intersects_approved_aois"]),
        ]
        for (x, width, _), value in zip(columns, values, strict=True):
            wrapped(draw, value, (x + 10, y + 14, x + width - 8), font(17, bold=value.startswith("M2-DEM")), ink, 3)
        y += 70

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({"status": "rendered", "width": WIDTH, "height": HEIGHT, "output": str(args.output), "output_sha256": sha256(args.output), "proposal_sha256": proposal_sha}, indent=2))


if __name__ == "__main__":
    main()
