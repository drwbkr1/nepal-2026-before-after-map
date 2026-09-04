#!/usr/bin/env python3
"""Render the text-only M2 DEM terrain-result owner-review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 1680
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
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    proposal_sha = sha256(args.proposal)
    receipt_sha = sha256(args.receipt)
    audit_sha = sha256(args.audit)

    if proposal["candidate"]["receipt_sha256"] != receipt_sha:
        raise SystemExit("proposal receipt hash does not match")
    if proposal["authority"]["review_required_by_sha256"] != audit_sha:
        raise SystemExit("proposal readiness-decision hash does not match")
    if receipt["status"] != "pass_terrain_qa_only_vertical_datum_and_independent_accuracy_deferred":
        raise SystemExit("terrain receipt status differs")
    if audit["decision"] != "defer":
        raise SystemExit("readiness decision must remain defer")

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f3f0e8")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, green, amber, red, line, pale = (
        "#17334b", "#20282f", "#5e6970", "#16715f", "#9a6500", "#9a382d", "#cbd2d3", "#fffdfa"
    )

    draw.rectangle((0, 0, WIDTH, 260), fill=navy)
    draw.text((MARGIN, 40), "NEPAL 2026  |  M2 RESULT REVIEW", font=font(27, bold=True), fill="#9ed7cf")
    draw.text((MARGIN, 92), "DEM terrain screen: owner decision", font=font(47, bold=True), fill="white")
    draw.text((MARGIN, 176), f"Proposal SHA-256  {proposal_sha}", font=font(21), fill="#d8e5eb")

    cards = [
        ("4 / 4", "SOURCE TILES PASS", "Finite values, range, curvature, and plateau screens", green),
        ("4 / 4", "NATIVE SEAMS PASS", "Largest absolute residual 58.19 m; none above 100 m", green),
        ("189 / 189", "STABLE FILES MATCH", "Paths, sizes, and SHA-256 reconcile after ArcGIS exit", green),
    ]
    card_top, card_height, gap = 310, 205, 24
    card_width = (WIDTH - 2 * MARGIN - 2 * gap) // 3
    for index, (value, title, body, color) in enumerate(cards):
        x = MARGIN + index * (card_width + gap)
        draw.rounded_rectangle((x, card_top, x + card_width, card_top + card_height), radius=15, fill=pale, outline=line, width=2)
        draw.text((x + 28, card_top + 22), value, font=font(42, bold=True), fill=color)
        draw.text((x + 28, card_top + 85), title, font=font(20, bold=True), fill=navy)
        wrapped(draw, body, (x + 28, card_top + 126, x + card_width - 25), font(20), ink, 5)

    left, right = MARGIN, 915
    draw.text((left, 570), "WHAT PASSED", font=font(24, bold=True), fill=navy)
    passed = [
        "EPSG:32645 output at 30 metre cells",
        "AOI slope screen: 0.00181% above 85 degrees",
        "Source hashes unchanged before and after",
        "PNG and rendered PDF: five visual criteria",
        "No remaining ArcGIS lock files",
    ]
    y = 620
    for item in passed:
        draw.ellipse((left, y + 8, left + 16, y + 24), fill=green)
        y = wrapped(draw, item, (left + 34, y, 820), font(23), ink, 5) + 20

    draw.rounded_rectangle((left, 995, 820, 1235), radius=14, fill="#e4efe9", outline="#91b9a8", width=2)
    draw.text((left + 28, 1022), "APPROVAL MEANS", font=font(22, bold=True), fill=green)
    wrapped(
        draw,
        "Accept the exact terrain-screen evidence and limitations as the completed owner result review. Only that audit gate may be reassessed after the response is locked and reconciled.",
        (left + 28, 1072, 792),
        font(22),
        ink,
    )

    draw.text((right, 570), "READINESS STILL DEFERRED", font=font(24, bold=True), fill=amber)
    deferred = [
        "EGM2008 vertical-datum method and owner installation",
        "Independent elevation accuracy",
        "Pair-specific radar processing and geometry masks",
        "Sentinel acquisition and real-pixel usability",
        "Satellite change, interpretation, and attribution",
    ]
    y = 620
    for item in deferred:
        draw.rectangle((right, y + 7, right + 16, y + 23), fill=amber)
        y = wrapped(draw, item, (right + 34, y, WIDTH - MARGIN), font(23), ink, 5) + 20

    draw.rounded_rectangle((right, 995, WIDTH - MARGIN, 1235), radius=14, fill="#f5e8e4", outline="#c99589", width=2)
    draw.text((right + 28, 1022), "APPROVAL DOES NOT", font=font(22, bold=True), fill=red)
    wrapped(
        draw,
        "Select a vertical route, install software, acquire another DEM or orbit file, run Sentinel terrain correction, publish DEM-derived pixels, or create a scientific claim.",
        (right + 28, 1072, WIDTH - MARGIN - 28),
        font(22),
        ink,
    )

    draw.rectangle((0, 1300, WIDTH, HEIGHT), fill="#e2ebe8")
    draw.text((MARGIN, 1336), "DECISION", font=font(23, bold=True), fill=navy)
    draw.text((MARGIN, 1385), "Approve  |  Revise  |  Defer", font=font(38, bold=True), fill=green)
    wrapped(
        draw,
        "Inspect the exact external APRX, PDF, or PNG identified in the instructions, then complete the bundle-bound blank response with an explicit attestation. The public review surface contains no DEM-derived map pixels.",
        (MARGIN, 1455, WIDTH - MARGIN),
        font(23),
        ink,
    )
    draw.text((MARGIN, 1608), f"Receipt {receipt_sha[:20]}...  |  Readiness audit {audit_sha[:20]}...", font=font(19), fill=muted)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({
        "status": "rendered",
        "width": WIDTH,
        "height": HEIGHT,
        "output": str(args.output),
        "output_sha256": sha256(args.output),
        "proposal_sha256": proposal_sha,
        "receipt_sha256": receipt_sha,
        "audit_sha256": audit_sha,
    }, indent=2))


if __name__ == "__main__":
    main()
