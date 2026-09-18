#!/usr/bin/env python3
"""Render the blank review surface for receipt-persistence recovery-002."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "contracts/m2-dem-vertical-datum-proj25-receipt-persistence-recovery-002-proposal.json"
OUTPUT = ROOT / "docs/assets/m2-dem-proj25-receipt-persistence-recovery-002-review.png"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)
    except OSError:
        return ImageFont.load_default()


def wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int, face: ImageFont.ImageFont, fill: str, leading: int = 31) -> int:
    x, y = xy
    for line in textwrap.wrap(text, width):
        draw.text((x, y), line, font=face, fill=fill)
        y += leading
    return y


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if OUTPUT.exists() and not args.replace:
        raise SystemExit(f"output collision: {OUTPUT}")
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    proposal_sha = sha256(PROPOSAL)
    image = Image.new("RGB", (1800, 1660), "#f4f0e8")
    draw = ImageDraw.Draw(image)
    title = font("segoeuib.ttf", 41)
    heading = font("segoeuib.ttf", 27)
    body = font("segoeui.ttf", 22)
    small = font("segoeui.ttf", 18)
    bold = font("segoeuib.ttf", 23)
    navy, ink, teal, amber, red, pale, line = "#17334b", "#20282f", "#126b5d", "#956000", "#9a382d", "#fffdfa", "#cbd2d3"

    draw.rectangle((0, 0, 1800, 225), fill=navy)
    draw.text((75, 40), "NEPAL 2026  |  M2 POST-OBSERVATION REVIEW", font=heading, fill="#9ed7cf")
    draw.text((75, 90), "Receipt persistence after exact promotion", font=title, fill="white")
    draw.text((75, 165), f"Proposal SHA-256  {proposal_sha}", font=small, fill="#d8e5eb")

    cards = [
        ("RECOVERY-001", "Terminal: success and failure receipts both failed after promotion; no retry is allowed.", red),
        ("DIRECT OBSERVATION", "Destination and staging are the same 80,585,622-byte file identity and exact approved SHA-256.", teal),
        ("ROOT CAUSE", "ArcGIS arcpy rebound the module-level datetime class name before receipt timestamps were built.", amber),
    ]
    top, gap = 270, 24
    width = (1800 - 150 - 2 * gap) // 3
    for index, (label, value, color) in enumerate(cards):
        left = 75 + index * (width + gap)
        draw.rounded_rectangle((left, top, left + width, top + 225), radius=14, fill=pale, outline=line, width=2)
        draw.rectangle((left, top, left + 10, top + 225), fill=color)
        draw.text((left + 30, top + 24), label, font=heading, fill=color)
        wrapped(draw, value, (left + 30, top + 78), 45, body, ink)

    draw.text((75, 550), "WHAT APPROVAL WOULD CHANGE", font=heading, fill=navy)
    steps = [
        "1  Preserve recovery-001, its missing terminal receipt, and the exact promoted hard link unchanged.",
        "2  Make timestamp creation local and ArcGIS-safe; change no scientific, source, CRS, sign, or tolerance rule.",
        "3  Reserve one append-only recovery-002 receipt before one read-only inspection; make zero network requests.",
        "4  Verify exact bytes, hard-link identity, official metadata, and ArcGIS readability; perform no new promotion.",
        "5  Only on pass, run the unchanged sign preflight and four fixed-order one-attempt conversions; stop on failure.",
    ]
    y = 595
    for item in steps:
        draw.rounded_rectangle((75, y, 1725, y + 74), radius=9, fill="white", outline=line)
        draw.text((100, y + 21), item, font=body, fill=ink)
        y += 85

    draw.text((75, 1045), "HARD LIMITS", font=heading, fill=navy)
    limits = [
        "0 network requests  |  0 recovery-001 retries  |  0 new promotion actions",
        "1 receipt-recovery-002 inspection  |  1 conversion attempt per exact DEM  |  stop on first failure",
        "No source overwrite, alternate grid, software install, orbit/radar action, analysis, attribution, or publication",
    ]
    y = 1090
    for item in limits:
        draw.rounded_rectangle((75, y, 1725, y + 66), radius=9, fill="#fffaf0", outline="#decda8")
        draw.text((100, y + 18), item, font=body, fill=ink)
        y += 77

    draw.text((75, 1340), "POST-OBSERVATION LIMIT", font=heading, fill=red)
    wrapped(draw, proposal["observed_state"]["post_observation_bias"], (85, 1382), 128, body, ink)
    draw.rectangle((0, 1535, 1800, 1660), fill="#e3ebe8")
    draw.text((75, 1573), "DECISION REQUIRED", font=heading, fill=navy)
    draw.text((420, 1570), "Approve  |  Revise  |  Defer — with owner attestation", font=bold, fill=teal)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="PNG", optimize=True)
    print(json.dumps({"output": str(OUTPUT), "proposal_sha256": proposal_sha, "width": 1800, "height": 1660}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
