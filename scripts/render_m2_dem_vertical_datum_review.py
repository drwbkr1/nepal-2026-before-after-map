#!/usr/bin/env python3
"""Render the M2 DEM vertical-datum method review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 1520
MARGIN = 80


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def wrapped(
    draw: ImageDraw.ImageDraw,
    value: str,
    box: tuple[int, int, int],
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    spacing: int = 7,
) -> int:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    capability = json.loads(args.capability.read_text(encoding="utf-8"))
    proposal_sha = sha256(args.proposal)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f0e8")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, teal, amber, red, line, pale = (
        "#17334b", "#20282f", "#5e6970", "#126b5d", "#956000", "#9a382d", "#cbd2d3", "#fffdfa"
    )

    draw.rectangle((0, 0, WIDTH, 255), fill=navy)
    draw.text((MARGIN, 42), "NEPAL 2026  |  M2 METHOD REVIEW", font=font(27, bold=True), fill="#9ed7cf")
    draw.text((MARGIN, 92), "DEM vertical datum before radar processing", font=font(45, bold=True), fill="white")
    draw.text((MARGIN, 170), f"Proposal SHA-256  {proposal_sha}", font=font(21), fill="#d8e5eb")

    facts = [
        ("COPERNICUS", "Source elevations are EGM2008 orthometric heights.", teal),
        ("ARCGIS GEOID", "The SAR switch converts with EGM96, a different model.", amber),
        ("ARCGIS NONE", "Valid only after the DEM is in ellipsoidal height.", red),
    ]
    card_top, card_height, gap = 300, 190, 24
    card_width = (WIDTH - 2 * MARGIN - 2 * gap) // 3
    for index, (title, body, color) in enumerate(facts):
        x = MARGIN + index * (card_width + gap)
        draw.rounded_rectangle((x, card_top, x + card_width, card_top + card_height), radius=15, fill=pale, outline=line, width=2)
        draw.rectangle((x, card_top, x + 10, card_top + card_height), fill=color)
        draw.text((x + 32, card_top + 25), title, font=font(21, bold=True), fill=color)
        wrapped(draw, body, (x + 32, card_top + 70, x + card_width - 25), font(24), ink)

    left, right = MARGIN, 880
    draw.text((left, 545), "RECOMMENDED PRODUCTION ROUTE", font=font(23, bold=True), fill=navy)
    steps = [
        "1  Owner separately installs ArcGIS Coordinate Systems Data: world1x1_vert.",
        "2  Verify Dataset_egm2008-1.grd and transformation WKID 110018 over the AOIs.",
        "3  Convert copies from EPSG:3855 orthometric to WGS 84 ellipsoidal height.",
        "4  Check h = H + N, AOI coverage, seams, artifacts, and terrain plausibility.",
        "5  Use NONE only with the verified ellipsoidal derivatives.",
    ]
    y = 594
    for step in steps:
        draw.rounded_rectangle((left, y, 820, y + 88), radius=10, fill="white", outline=line)
        wrapped(draw, step, (left + 22, y + 16, 798), font(21), ink, 5)
        y += 100

    draw.text((right, 545), "CURRENT MACHINE", font=font(23, bold=True), fill=navy)
    current_box = (right, 590, WIDTH - MARGIN, 825)
    draw.rounded_rectangle(current_box, radius=14, fill="white", outline=line, width=2)
    current = capability["inspection"]
    current_lines = [
        f"ArcGIS Pro {capability['runtime']['version']} {capability['runtime']['license_level']}",
        f"Built-in EGM96 grid: {'present' if current['builtin_egm96_grid']['present'] else 'absent'}",
        f"EGM2008 one-minute grid: {'present' if current['matching_egm2008_grids'] else 'absent'}",
        f"Usable exact transformations over AOI: {len(current['listed_transformations'])}",
    ]
    y = 620
    for item in current_lines:
        draw.ellipse((right + 28, y + 8, right + 40, y + 20), fill=teal if "present" in item and "EGM96" in item else red)
        draw.text((right + 58, y), item, font=font(22), fill=ink)
        y += 48
    draw.text((right + 28, 780), "Exact route status: DEFER until owner installation", font=font(20, bold=True), fill=red)

    draw.text((right, 875), "APPROVAL BOUNDARY", font=font(23, bold=True), fill=navy)
    y = wrapped(draw, "Approval selects the EGM2008 one-minute preconversion method and allows controlled conversion only after the owner installs the matching component.", (right, 920, WIDTH - MARGIN), font(22), ink)
    y += 24
    draw.text((right, y), "STILL REQUIRES OWNER CONTROL", font=font(20, bold=True), fill=red)
    y += 38
    wrapped(draw, "My Esri sign-in, license acceptance, software download or install, and UAC. No alternate geoid grid, source-tile overwrite, orbit download, premature radar run, or scientific claim is authorized.", (right, y, WIDTH - MARGIN), font(21), ink)

    footer_top = 1260
    draw.rectangle((0, footer_top, WIDTH, HEIGHT), fill="#e3ebe8")
    draw.text((MARGIN, footer_top + 36), "DECISION", font=font(22, bold=True), fill=navy)
    draw.text((MARGIN, footer_top + 82), "Approve  |  Revise  |  Defer", font=font(34, bold=True), fill=teal)
    wrapped(draw, "Use the exact blank response generated from the bundle-bound review contract. The review itself performs no installation, conversion, or radar processing.", (MARGIN, footer_top + 140, WIDTH - MARGIN), font(22), ink)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({
        "status": "rendered",
        "width": WIDTH,
        "height": HEIGHT,
        "output": str(args.output),
        "output_sha256": sha256(args.output),
        "proposal_sha256": proposal_sha,
    }, indent=2))


if __name__ == "__main__":
    main()
