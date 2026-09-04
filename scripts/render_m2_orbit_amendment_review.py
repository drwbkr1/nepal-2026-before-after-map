#!/usr/bin/env python3
"""Render the exact four-file Sentinel-1 orbit amendment review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 2100
MARGIN = 78


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
    spacing: int = 5,
) -> int:
    left, top, right = box
    max_width = right - left
    words: list[str] = []
    for raw_word in value.split():
        if draw.textbbox((0, 0), raw_word, font=text_font)[2] <= max_width:
            words.append(raw_word)
            continue
        chunk = ""
        for character in raw_word:
            candidate = chunk + character
            if chunk and draw.textbbox((0, 0), candidate, font=text_font)[2] > max_width:
                words.append(chunk)
                chunk = character
            else:
                chunk = candidate
        if chunk:
            words.append(chunk)
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
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


def card(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], title: str, body: str, title_color: str) -> None:
    left, top, right, bottom = rect
    draw.rounded_rectangle(rect, radius=14, fill="white", outline="#c8d0d3", width=2)
    draw.text((left + 24, top + 20), title, font=font(20, bold=True), fill=title_color)
    wrapped(draw, body, (left + 24, top + 62, right - 22), font(21), "#1d252c", 7)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    proposal_sha = sha256(args.proposal)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f0e7")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, teal, amber, red, line = (
        "#18324a",
        "#1d252c",
        "#5e6a72",
        "#167061",
        "#9a5d00",
        "#9a382d",
        "#c8d0d3",
    )

    draw.rectangle((0, 0, WIDTH, 250), fill=navy)
    draw.text((MARGIN, 42), "NEPAL 2026  |  M2 ORBIT AMENDMENT REVIEW", font=font(28, bold=True), fill="#9fd8d0")
    draw.text((MARGIN, 92), "Restituted S1D orbit vectors for six radar scenes", font=font(43, bold=True), fill="white")
    draw.text((MARGIN, 171), f"Proposal SHA-256  {proposal_sha}", font=font(21), fill="#d7e3ea")

    summary = manifest["summary"]
    stats = [
        (str(summary["selected_file_count"]), "exact EOF files"),
        (str(summary["covered_sentinel_source_count"]), "bound Sentinel scenes"),
        (f"{summary['combined_content_length_mib']:.3f} MiB", "remote total"),
        (str(summary["precise_covering_file_count_at_assessment"]), "precise files available"),
    ]
    stat_top = 282
    stat_width = (WIDTH - 2 * MARGIN - 54) // 4
    for index, (value, label) in enumerate(stats):
        x = MARGIN + index * (stat_width + 18)
        draw.rounded_rectangle((x, stat_top, x + stat_width, stat_top + 112), radius=12, fill="white", outline=line)
        draw.text((x + 20, stat_top + 14), value, font=font(31, bold=True), fill=navy)
        draw.text((x + 20, stat_top + 67), label, font=font(18), fill=muted)

    draw.text((MARGIN, 440), "WHY A SEPARATE DECISION IS REQUIRED", font=font(22, bold=True), fill=red)
    y = wrapped(
        draw,
        "The six approved GRD scenes contain predicted state vectors. ArcGIS recommends updating recent Sentinel-1 data to restituted vectors, but these four EOF files are additional product identities outside the active eight-product approval.",
        (MARGIN, 484, WIDTH - MARGIN),
        font(24),
        ink,
        8,
    )
    y += 22
    draw.text((MARGIN, y), "CURRENT QUALITY CHOICE", font=font(21, bold=True), fill=amber)
    y += 42
    y = wrapped(
        draw,
        "Four full-coverage AUX_RESORB files are online. No AUX_POEORB file covered any scene at assessment time. Restituted vectors enable time-sensitive controlled QA; precise substitution remains a later exact review.",
        (MARGIN, y, WIDTH - MARGIN),
        font(23),
        ink,
        8,
    )
    y += 24
    draw.text((MARGIN, y), "FIXED SELECTION RULE", font=font(21, bold=True), fill=teal)
    y += 42
    y = wrapped(
        draw,
        "For each unique acquisition window: require full validity coverage, maximize the minimum temporal margin around the scene, then break ties by latest publication and provider UUID. This is a declared project rule, not an ESA rule.",
        (MARGIN, y, WIDTH - MARGIN),
        font(23),
        ink,
        8,
    )

    card_top = y + 35
    gap = 22
    card_width = (WIDTH - 2 * MARGIN - gap) // 2
    card(
        draw,
        (MARGIN, card_top, MARGIN + card_width, card_top + 250),
        "APPROVAL WOULD AUTHORIZE ONLY",
        "Existing secret-safe CDSE token use; four exact downloads; byte, checksum, XML, OSV, validity, and scene-binding verification; non-Git custody; explicit application only to six bound Sentinel sources.",
        teal,
    )
    card(
        draw,
        (MARGIN + card_width + gap, card_top, WIDTH - MARGIN, card_top + 250),
        "STILL OUTSIDE SCOPE",
        "Accounts, new terms, S3-secret generation, costs, other orbit files, silent precise substitution, unresolved DEM gates, premature radar processing, payload publication, and scientific conclusions.",
        red,
    )

    table_top = card_top + 310
    draw.text((MARGIN, table_top - 42), "EXACT CANDIDATE ORBIT FILES", font=font(22, bold=True), fill=navy)
    headers = [(MARGIN, 150, "SOURCE"), (230, 310, "BOUND SCENES"), (550, 710, "EXACT EOF NAME"), (1270, 195, "MIN MARGIN"), (1475, 245, "SIZE / TYPE")]
    draw.rectangle((MARGIN, table_top, WIDTH - MARGIN, table_top + 52), fill="#dfe8e8")
    for x, _, label in headers:
        draw.text((x + 10, table_top + 14), label, font=font(17, bold=True), fill=navy)
    row_top = table_top + 52
    row_height = 136
    for index, record in enumerate(manifest["records"]):
        if index % 2 == 0:
            draw.rectangle((MARGIN, row_top, WIDTH - MARGIN, row_top + row_height), fill="#fffdf9")
        draw.line((MARGIN, row_top + row_height, WIDTH - MARGIN, row_top + row_height), fill=line)
        values = [
            record["source_id"],
            ", ".join(record["sentinel_source_ids"]),
            record["exact_product_name"],
            f"{record['minimum_scene_margin_seconds']:,} s",
            f"{record['content_length_bytes']:,} B\nAUX_RESORB",
        ]
        for (x, width, _), value in zip(headers, values, strict=True):
            wrapped(draw, value.replace("\n", " "), (x + 10, row_top + 18, x + width - 8), font(18, bold=value.startswith("M2-ORB")), ink, 4)
        row_top += row_height

    decision_top = row_top + 45
    draw.rounded_rectangle((MARGIN, decision_top, WIDTH - MARGIN, decision_top + 170), radius=14, fill="#fff7df", outline="#d7a53b", width=3)
    draw.text((MARGIN + 24, decision_top + 20), "OWNER DECISION REQUIRED", font=font(22, bold=True), fill=amber)
    wrapped(
        draw,
        "Choose approve, revise, or defer for bundle-bound item M2-ORBIT-AMENDMENT-001 and attest the completed decision. No option is selected on this review surface. Approval would not start a transfer until the original Sentinel token and custody prerequisites are satisfied.",
        (MARGIN + 24, decision_top + 64, WIDTH - MARGIN - 24),
        font(22),
        ink,
        7,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(
        json.dumps(
            {
                "status": "rendered_text_only",
                "width": WIDTH,
                "height": HEIGHT,
                "output": str(args.output),
                "output_sha256": sha256(args.output),
                "proposal_sha256": proposal_sha,
                "human_decision_count": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
