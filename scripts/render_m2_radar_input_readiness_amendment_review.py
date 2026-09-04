#!/usr/bin/env python3
"""Render the M2 Sentinel-1 input-readiness label-amendment review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 1760
MARGIN = 78


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def wrapped(draw: ImageDraw.ImageDraw, text: str, left: int, top: int, right: int, size: int, *, bold: bool = False, fill: str = "#1d252c", spacing: int = 7) -> int:
    face = font(size, bold=bold)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
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


def card(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], title: str, body: str, color: str) -> None:
    left, top, right, _ = rect
    draw.rounded_rectangle(rect, radius=14, fill="white", outline="#c8d0d3", width=2)
    draw.text((left + 24, top + 20), title, font=font(21, bold=True), fill=color)
    wrapped(draw, body, left + 24, top + 64, right - 24, 21, fill="#1d252c")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    proposal_sha = sha256(args.proposal)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f0e7")
    draw = ImageDraw.Draw(image)
    navy, ink, muted = "#18324a", "#1d252c", "#5e6a72"
    teal, amber, red, line = "#167061", "#9a5d00", "#9a382d", "#c8d0d3"

    draw.rectangle((0, 0, WIDTH, 248), fill=navy)
    draw.text((MARGIN, 40), "NEPAL 2026  |  M2 RADAR INPUT REVIEW", font=font(28, bold=True), fill="#9fd8d0")
    draw.text((MARGIN, 91), "GRD annotation-label amendment", font=font(44, bold=True), fill="white")
    draw.text((MARGIN, 174), f"Proposal SHA-256  {proposal_sha}", font=font(21), fill="#d7e3ea")

    stats = [("3", "sources blocked"), ("6", "Detected labels"), ("6", "TIFF headers opened"), ("0", "pixels decoded")]
    top = 280
    width = (WIDTH - 2 * MARGIN - 54) // 4
    for index, (value, label) in enumerate(stats):
        x = MARGIN + index * (width + 18)
        draw.rounded_rectangle((x, top, x + width, top + 112), radius=12, fill="white", outline=line)
        draw.text((x + 20, top + 13), value, font=font(32, bold=True), fill=navy)
        draw.text((x + 20, top + 67), label, font=font(18), fill=muted)

    y = 438
    draw.text((MARGIN, y), "RETAINED RESULT: BLOCK", font=font(22, bold=True), fill=red)
    y = wrapped(draw, "The published contract required pixelValue = AMPLITUDE. All real VV and VH annotations say Detected. Every bound inventory, acquisition, embedded-orbit, U16, dimension, and ArcGIS header check otherwise passed. Real-001 remains immutable and cannot be reclassified.", MARGIN, y + 44, WIDTH - MARGIN, 24, fill=ink)

    y += 24
    draw.text((MARGIN, y), "OFFICIAL FORMAT EVIDENCE", font=font(22, bold=True), fill=teal)
    y = wrapped(draw, "S1-RS-MDA-52-7441 defines pixelValueType as Complex or Detected. The official processing page says GRD pixels represent detected amplitude. Detected is the XML label; detected amplitude is its physical interpretation.", MARGIN, y + 44, WIDTH - MARGIN, 24, fill=ink)

    cards_top = y + 34
    gap = 22
    card_width = (WIDTH - 2 * MARGIN - gap) // 2
    card(draw, (MARGIN, cards_top, MARGIN + card_width, cards_top + 312), "APPROVAL WOULD AUTHORIZE ONLY", "A new versioned contract changing one semantic value from AMPLITUDE to Detected; contract-driven validation and focused tests; new synthetic identities; publication and exact CI; then one read-only real-002 inspection of the same three sources and exact reconciliation.", teal)
    card(draw, (MARGIN + card_width + gap, cards_top, WIDTH - MARGIN, cards_top + 312), "STILL PROHIBITED", "Editing or hiding real-001; further acquisition or recovery; orbit or DEM action; pixel decoding; calibration; terrain correction; registration; baseline or change analysis; new sources; account or terms action; cost; or scientific publication.", red)

    bias_top = cards_top + 360
    draw.text((MARGIN, bias_top), "KNOWN POST-OBSERVATION BIAS", font=font(22, bold=True), fill=amber)
    y = wrapped(draw, "The correction is expected to clear the observed label mismatch. Real-002 would confirm the corrected implementation against the same inputs; it would not be blind or independent, and even a pass would release no pixel or baseline work.", MARGIN, bias_top + 44, WIDTH - MARGIN, 24, fill=ink)

    decision_top = y + 42
    draw.rounded_rectangle((MARGIN, decision_top, WIDTH - MARGIN, decision_top + 245), radius=14, fill="#fff7df", outline="#d7a53b", width=3)
    draw.text((MARGIN + 24, decision_top + 20), "OWNER DECISION REQUIRED", font=font(22, bold=True), fill=amber)
    draw.text((MARGIN + 30, decision_top + 76), "[ ]  APPROVE", font=font(25, bold=True), fill=ink)
    draw.text((MARGIN + 395, decision_top + 76), "[ ]  REVISE", font=font(25, bold=True), fill=ink)
    draw.text((MARGIN + 735, decision_top + 76), "[ ]  DEFER", font=font(25, bold=True), fill=ink)
    wrapped(draw, "No option is selected. A completed response must bind item M2-RADAR-INPUT-LABEL-AMENDMENT-001 and include the reviewer's attestation.", MARGIN + 30, decision_top + 133, WIDTH - MARGIN - 30, 22, fill=ink)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({"status":"rendered_text_only","width":WIDTH,"height":HEIGHT,"output":str(args.output),"output_sha256":sha256(args.output),"proposal_sha256":proposal_sha,"human_decision_count":0}, indent=2))


if __name__ == "__main__":
    main()
