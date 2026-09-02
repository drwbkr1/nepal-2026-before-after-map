#!/usr/bin/env python3
"""Render the M1 candidate manifest as a compact PNG review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
MARGIN = 80


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], text_font: ImageFont.FreeTypeFont, fill: str, spacing: int = 6) -> int:
    left, top, right, _ = box
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= right - left or not line:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    y = top
    for value in lines:
        draw.text((left, y), value, font=text_font, fill=fill)
        y += text_font.size + spacing
    return y


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    digest = sha256(args.manifest)
    row_height = 76
    height = 480 + row_height * len(manifest["records"]) + 300
    image = Image.new("RGB", (WIDTH, height), "#f6f3ec")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, line = "#18324a", "#1d252c", "#5e6a72", "#ccd3d6"
    draw.rectangle((0, 0, WIDTH, 250), fill=navy)
    draw.text((MARGIN, 54), "NEPAL 2026  |  M1 SOURCE REVIEW", font=font(28, bold=True), fill="#9fd8d0")
    draw.text((MARGIN, 104), "Candidate satellite source manifest", font=font(48, bold=True), fill="white")
    draw.text((MARGIN, 180), f"Manifest SHA-256  {digest}", font=font(22), fill="#d7e3ea")

    summary = manifest["summary"]
    stats = [
        ("10", "catalog candidates"),
        (str(summary["proposed_accept_count"]), "proposed accept"),
        (str(summary["proposed_defer_count"]), "proposed defer"),
        (f"{summary['proposed_acquisition_catalog_gib']:.3f} GiB", "catalog volume"),
    ]
    stat_top = 285
    stat_width = (WIDTH - 2 * MARGIN - 54) // 4
    for index, (value, label) in enumerate(stats):
        x = MARGIN + index * (stat_width + 18)
        draw.rounded_rectangle((x, stat_top, x + stat_width, stat_top + 110), radius=12, fill="white", outline=line)
        draw.text((x + 22, stat_top + 14), value, font=font(32, bold=True), fill=navy)
        draw.text((x + 22, stat_top + 63), label, font=font(19), fill=muted)

    y = 435
    columns = [
        (MARGIN, 250, "SOURCE"),
        (330, 130, "ROLE"),
        (470, 270, "SENSOR"),
        (750, 220, "ORBIT / TILE"),
        (980, 140, "DETAIL AOI"),
        (1130, 120, "CLOUD"),
        (1260, 460, "PROPOSED DISPOSITION"),
    ]
    draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + 56), fill="#dfe8e8")
    for x, _, label in columns:
        draw.text((x + 12, y + 15), label, font=font(18, bold=True), fill=navy)
    y += 56
    for index, record in enumerate(manifest["records"]):
        if index % 2 == 0:
            draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + row_height), fill="#fffdf9")
        draw.line((MARGIN, y + row_height, WIDTH - MARGIN, y + row_height), fill=line, width=1)
        orbit = record["orbit_or_tile"]
        orbit_text = orbit["tile_id"] or f"{orbit['orbit_direction'].title()} r{orbit['relative_orbit_number']}"
        intersections = record["coverage_status"]["approved_aoi_intersections"]
        detailed = intersections["AOI-SOURCE"] or intersections["AOI-UPPER-CORRIDOR"]
        cloud = record["catalog_cloud_cover_percent"]
        proposal = record["proposed_disposition"]["disposition"]
        proposal_color = "#196b5b" if proposal.startswith("accept") else "#9a5d00"
        values = [
            record["source_id"],
            record["event_role"].title(),
            record["collection"],
            orbit_text,
            "Yes" if detailed else "No",
            "n/a" if cloud is None else f"{cloud:.2f}%",
            proposal.replace("_", " "),
        ]
        for (x, width, _), value in zip(columns, values, strict=True):
            current_font = font(18, bold=value == record["source_id"] or value == values[-1])
            color = proposal_color if value == values[-1] else ink
            draw_wrapped(draw, value, (x + 12, y + 14, x + width - 8, y + row_height - 6), current_font, color, 3)
        y += row_height

    y += 45
    draw.text((MARGIN, y), "DECISION BOUNDARY", font=font(22, bold=True), fill=navy)
    y += 42
    boundary = "Approval locks eight proposed sources and preserves two optical context records as deferred. It does not authorize authentication, terms acceptance, full-product download, pixel-usability claims, or scientific conclusions."
    y = draw_wrapped(draw, boundary, (MARGIN, y, WIDTH - MARGIN, y + 120), font(24), ink, 7)
    y += 26
    draw.text((MARGIN, y), "KNOWN LIMITATIONS", font=font(22, bold=True), fill=navy)
    y += 42
    limitations = "Post-event Sentinel-2 RUM is high-cloud-risk. Radar terrain effects and all masks, registration, and pixel coverage remain untested. No candidate has entered full-product custody."
    draw_wrapped(draw, limitations, (MARGIN, y, WIDTH - MARGIN, y + 140), font(22), muted, 7)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({"status": "rendered", "width": WIDTH, "height": height, "manifest_sha256": digest, "output": str(args.output), "output_sha256": sha256(args.output)}, indent=2))


if __name__ == "__main__":
    main()
