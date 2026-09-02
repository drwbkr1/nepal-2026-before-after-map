#!/usr/bin/env python3
"""Render the proposed M2 controlled-acquisition plan for human review."""

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


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    value: str,
    left: int,
    top: int,
    right: int,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    spacing: int = 6,
) -> int:
    words = value.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if not line or draw.textbbox((0, 0), candidate, font=text_font)[2] <= right - left:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    y = top
    for text in lines:
        draw.text((left, y), text, font=text_font, fill=fill)
        y += text_font.size + spacing
    return y


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    digest = sha256(args.plan)
    records = plan["records"]
    row_height = 72
    height = 600 + row_height * len(records) + 500
    image = Image.new("RGB", (WIDTH, height), "#f5f1e8")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, teal, amber, line = (
        "#18324a",
        "#1d252c",
        "#5e6a72",
        "#167061",
        "#9a5d00",
        "#c8d0d3",
    )

    draw.rectangle((0, 0, WIDTH, 255), fill=navy)
    draw.text((MARGIN, 50), "NEPAL 2026  |  M2 ACTIVATION REVIEW", font=font(28, bold=True), fill="#9fd8d0")
    draw.text((MARGIN, 101), "Controlled acquisition proposal", font=font(48, bold=True), fill="white")
    draw.text((MARGIN, 181), f"Plan SHA-256  {digest}", font=font(22), fill="#d7e3ea")

    stats = [
        (str(plan["selection"]["planned_download_count"]), "exact products"),
        (f'{plan["selection"]["catalog_content_length_gib"]:.3f} GiB', "catalog volume"),
        (f'{plan["custody"]["minimum_free_space_gib_before_start"]} GiB', "planning minimum"),
        ("0", "downloads authorized"),
    ]
    stat_top = 290
    stat_width = (WIDTH - 2 * MARGIN - 54) // 4
    for index, (value, label) in enumerate(stats):
        x = MARGIN + index * (stat_width + 18)
        draw.rounded_rectangle((x, stat_top, x + stat_width, stat_top + 110), radius=12, fill="white", outline=line)
        draw.text((x + 22, stat_top + 14), value, font=font(32, bold=True), fill=navy)
        draw.text((x + 22, stat_top + 63), label, font=font(19), fill=muted)

    y = 435
    draw.text((MARGIN, y), "PLANNED EXTERNAL CUSTODY", font=font(20, bold=True), fill=navy)
    y = draw_wrapped(draw, plan["custody"]["planned_external_root"], MARGIN, y + 38, WIDTH - MARGIN, font(25), ink)
    y += 28

    columns = [
        (MARGIN, 150, "SOURCE"),
        (230, 150, "ROLE"),
        (390, 280, "SENSOR"),
        (680, 290, "PROVIDER ID (ABBREVIATED)"),
        (980, 180, "CATALOG SIZE"),
        (1170, 550, "STATUS"),
    ]
    draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + 54), fill="#dfe8e8")
    for x, _, label in columns:
        draw.text((x + 12, y + 14), label, font=font(18, bold=True), fill=navy)
    y += 54
    for index, record in enumerate(records):
        if index % 2 == 0:
            draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + row_height), fill="#fffdf9")
        draw.line((MARGIN, y + row_height, WIDTH - MARGIN, y + row_height), fill=line, width=1)
        values = [
            record["source_id"],
            record["event_role"].title(),
            record["collection"],
            f'{record["provider_product_id"][:8]}…{record["provider_product_id"][-4:]}',
            f'{record["catalog_content_length_bytes"] / (1024 ** 3):.3f} GiB',
            "Blocked pending exact M2 activation",
        ]
        for (x, width, _), value in zip(columns, values, strict=True):
            color = amber if value.startswith("Blocked") else ink
            draw_wrapped(draw, value, x + 12, y + 13, x + width - 8, font(17, bold=value == record["source_id"]), color, 3)
        y += row_height

    y += 42
    draw.text((MARGIN, y), "WHAT AN APPROVAL WOULD AUTHORIZE", font=font(22, bold=True), fill=teal)
    y += 40
    allow = "Fresh custody preflight; creation of the external data root; use of an owner-controlled existing Copernicus account or session; download of only these eight products; checksum, archive, band, coverage, and baseline QA."
    y = draw_wrapped(draw, allow, MARGIN, y, WIDTH - MARGIN, font(23), ink, 7)
    y += 26
    draw.text((MARGIN, y), "WHAT REMAINS OUTSIDE THE DECISION", font=font(22, bold=True), fill=amber)
    y += 40
    deny = "New or changed terms, account creation or recovery, credential disclosure, spending, restricted imagery, quicklook redistribution, Git storage of heavy data, and publication of scientific conclusions or emergency guidance."
    y = draw_wrapped(draw, deny, MARGIN, y, WIDTH - MARGIN, font(23), ink, 7)
    y += 26
    draw.text((MARGIN, y), "STOP CONDITIONS", font=font(22, bold=True), fill=navy)
    y += 40
    stops = "Stop for owner action if login or MFA is required, terms change, product identity or access differs, free space falls below the planning minimum, or a paid or unapproved route appears. No product currently has established usable pixels."
    draw_wrapped(draw, stops, MARGIN, y, WIDTH - MARGIN, font(22), muted, 7)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({
        "status": "rendered",
        "width": WIDTH,
        "height": height,
        "plan_sha256": digest,
        "output": str(args.output),
        "output_sha256": sha256(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
