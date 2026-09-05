#!/usr/bin/env python3
"""Render the blank M2 materialization and pixel-readiness review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 2140
MARGIN = 76


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def wrapped(draw: ImageDraw.ImageDraw, text: str, left: int, top: int, right: int, size: int, *, bold: bool = False, fill: str = "#1c2730", spacing: int = 7) -> int:
    face = font(size, bold=bold)
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if not current or draw.textbbox((0, 0), candidate, font=face)[2] <= right - left:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    y = top
    for line in lines:
        draw.text((left, y), line, font=face, fill=fill)
        y += size + spacing
    return y


def card(draw: ImageDraw.ImageDraw, left: int, top: int, right: int, height: int, title: str, body: str, color: str) -> None:
    draw.rounded_rectangle((left, top, right, top + height), radius=15, fill="white", outline="#c5ced3", width=2)
    draw.text((left + 24, top + 20), title, font=font(21, bold=True), fill=color)
    wrapped(draw, body, left + 24, top + 63, right - 24, 20, fill="#1c2730")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    proposal_sha = sha256(args.proposal)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f3f0e8")
    draw = ImageDraw.Draw(image)
    navy, teal, amber, red, ink, muted = "#17334b", "#167064", "#a15e00", "#9a382d", "#1c2730", "#5d6971"
    draw.rectangle((0, 0, WIDTH, 250), fill=navy)
    draw.text((MARGIN, 38), "NEPAL 2026  |  M2 OWNER REVIEW", font=font(28, bold=True), fill="#9fd9d1")
    draw.text((MARGIN, 88), "Materialization and pixel readiness", font=font(43, bold=True), fill="white")
    draw.text((MARGIN, 176), f"Proposal SHA-256  {proposal_sha}", font=font(20), fill="#d8e3e9")

    stats = [
        ("8", "archives verified"),
        ("3", "already materialized"),
        ("5", "planned once each"),
        ("7.27 GB", "planned extracted bytes"),
    ]
    y = 286
    gap = 18
    width = (WIDTH - 2 * MARGIN - gap * 3) // 4
    for index, (value, label) in enumerate(stats):
        left = MARGIN + index * (width + gap)
        draw.rounded_rectangle((left, y, left + width, y + 112), radius=13, fill="white", outline="#c5ced3", width=2)
        draw.text((left + 20, y + 14), value, font=font(31, bold=True), fill=navy)
        draw.text((left + 20, y + 69), label, font=font(18), fill=muted)

    y = 438
    draw.text((MARGIN, y), "CURRENT GATE", font=font(22, bold=True), fill=amber)
    y = wrapped(draw, "M2-VERIFY proves archive custody and SAFE structure only. Five products remain unmaterialized. The blank packet authorizes nothing until the owner returns one exact completed response.", MARGIN, y + 43, WIDTH - MARGIN, 24, fill=ink)

    card_top = y + 34
    card_width = (WIDTH - 2 * MARGIN - 22) // 2
    card(draw, MARGIN, card_top, MARGIN + card_width, 328, "STAGE 1  |  MATERIALIZE", "M1-SRC-004, 005, 006, 010, then 008. One append-only attempt each. Re-hash and recheck every archive before output. Stop on the first materialization failure. No network, authentication, overwrite, retry, or source mutation.", teal)
    card(draw, MARGIN + card_width + 22, card_top, WIDTH - MARGIN, 328, "STAGE 2  |  HEADERS", "Only after all five pass: publish exact six-source radar and two-source optical header gates; require portable and ArcGIS synthetic proof plus public CI; then one read-only real inspection per route. No measurement pixels.", teal)

    second_top = card_top + 355
    card(draw, MARGIN, second_top, MARGIN + card_width, 352, "STAGE 3  |  OPTICAL PIXEL QA", "Only after optical headers pass and a second implementation, public-CI, and final no-pixel preflight gate: one exact run on the RUM pair and three approved AOIs. Measure coverage, conservative masks, 20 m EPSG:32645 grids, and registration only.", amber)
    card(draw, MARGIN + card_width + 22, second_top, WIDTH - MARGIN, 352, "STILL PROHIBITED", "Radar pixels, orbit recovery or application, DEM vertical conversion, calibration, terrain correction, baselines, change rasters, candidate polygons, interpretation, attribution, emergency guidance, raster publication, source substitution, or threshold tuning.", red)

    risk_top = second_top + 394
    draw.text((MARGIN, risk_top), "KNOWN OPTICAL RISK", font=font(22, bold=True), fill=amber)
    y = wrapped(draw, "The 27 August scene may be too cloudy. DEFER or BLOCK remains a valid terminal result; approval does not permit another date or product. Radar pixel readiness remains outside this proposal because orbit and DEM vertical-datum gates are unresolved.", MARGIN, risk_top + 44, WIDTH - MARGIN, 24, fill=ink)

    evidence_top = y + 28
    free_gib = preflight["storage"]["observed_free_bytes"] / (1024 ** 3)
    draw.rounded_rectangle((MARGIN, evidence_top, WIDTH - MARGIN, evidence_top + 176), radius=14, fill="#edf7f4", outline="#8bbcb4", width=2)
    draw.text((MARGIN + 24, evidence_top + 20), "READ-ONLY PREFLIGHT: PASS", font=font(22, bold=True), fill=teal)
    wrapped(draw, f"Five exact archives and receipts re-hashed; planned paths absent; {free_gib:.1f} GiB free. The preflight performed no extraction, authentication, network request, external mutation, or pixel read. It must be repeated before execution.", MARGIN + 24, evidence_top + 65, WIDTH - MARGIN - 24, 21, fill=ink)

    decision_top = evidence_top + 214
    draw.rounded_rectangle((MARGIN, decision_top, WIDTH - MARGIN, decision_top + 268), radius=15, fill="#fff7df", outline="#d4a13b", width=3)
    draw.text((MARGIN + 24, decision_top + 20), "OWNER DECISION REQUIRED", font=font(23, bold=True), fill=amber)
    draw.text((MARGIN + 34, decision_top + 80), "[ ]  APPROVE", font=font(26, bold=True), fill=ink)
    draw.text((MARGIN + 410, decision_top + 80), "[ ]  REVISE", font=font(26, bold=True), fill=ink)
    draw.text((MARGIN + 760, decision_top + 80), "[ ]  DEFER", font=font(26, bold=True), fill=ink)
    wrapped(draw, "No option is selected. A completed response must bind item M2-MATERIALIZATION-PIXEL-READINESS-001, the exact review-bundle hash, and the reviewer's attestation.", MARGIN + 34, decision_top + 145, WIDTH - MARGIN - 34, 22, fill=ink)

    footer_y = decision_top + 310
    draw.line((MARGIN, footer_y, WIDTH - MARGIN, footer_y), fill="#b6c0c6", width=2)
    wrapped(draw, "PASS here would authorize bounded work only. It would not prove materialization, readable headers, usable pixels, observable change, interpretation, attribution, or scientific fitness.", MARGIN, footer_y + 24, WIDTH - MARGIN, 20, bold=True, fill=navy)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({"status":"rendered_blank_review_surface","width":WIDTH,"height":HEIGHT,"output":str(args.output),"output_sha256":sha256(args.output),"proposal_sha256":proposal_sha,"human_decision_count":0}, indent=2))


if __name__ == "__main__":
    main()
