#!/usr/bin/env python3
"""Render the blank review surface for the PROJ25 metadata recovery proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "contracts/m2-dem-vertical-datum-proj25-metadata-recovery-001-proposal.json"
OUTPUT = ROOT / "docs/assets/m2-dem-vertical-datum-proj25-metadata-recovery-001-review.png"


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
    image = Image.new("RGB", (1800, 1580), "#f4f0e8")
    draw = ImageDraw.Draw(image)
    title = font("segoeuib.ttf", 42)
    heading = font("segoeuib.ttf", 27)
    body = font("segoeui.ttf", 22)
    small = font("segoeui.ttf", 18)
    bold = font("segoeuib.ttf", 23)
    navy, ink, teal, amber, red, pale, line = "#17334b", "#20282f", "#126b5d", "#956000", "#9a382d", "#fffdfa", "#cbd2d3"

    draw.rectangle((0, 0, 1800, 225), fill=navy)
    draw.text((75, 40), "NEPAL 2026  |  M2 RECOVERY REVIEW", font=heading, fill="#9ed7cf")
    draw.text((75, 90), "Exact PROJ grid; metadata-key mismatch", font=title, fill="white")
    draw.text((75, 165), f"Proposal SHA-256  {proposal_sha}", font=small, fill="#d8e5eb")

    cards = [
        ("TERMINAL ATTEMPT", "One request was consumed. real-001 is terminal and cannot be retried.", red),
        ("EXACT BYTES", "80,585,622 bytes and approved SHA-256 match; staging is preserved outside Git.", teal),
        ("FAILED PREDICATE", "Official metadata uses an image description and target_crs_epsg_code, not two generic keys.", amber),
    ]
    top, gap = 270, 24
    width = (1800 - 150 - 2 * gap) // 3
    for index, (label, value, color) in enumerate(cards):
        left = 75 + index * (width + gap)
        draw.rounded_rectangle((left, top, left + width, top + 220), radius=14, fill=pale, outline=line, width=2)
        draw.rectangle((left, top, left + 10, top + 220), fill=color)
        draw.text((left + 30, top + 24), label, font=heading, fill=color)
        wrapped(draw, value, (left + 30, top + 76), 46, body, ink)

    draw.text((75, 545), "OBSERVED OFFICIAL METADATA", font=heading, fill=navy)
    y = 592
    observed = [
        "TIFFTAG_IMAGEDESCRIPTION: WGS 84 (EPSG:4979) to EGM2008 height (EPSG:3855)",
        "target_crs_epsg_code: 3855    TYPE: VERTICAL_OFFSET_GEOGRAPHIC_TO_VERTICAL",
        "GTiff, 1 band, 8640 x 4321, world coverage, area_of_use World, public-domain tag",
    ]
    for line_text in observed:
        draw.rounded_rectangle((75, y, 1725, y + 66), radius=10, fill="white", outline=line)
        draw.text((100, y + 18), line_text, font=body, fill=ink)
        y += 78

    draw.text((75, 855), "BOUNDED RECOVERY IF APPROVED", font=heading, fill=navy)
    steps = [
        "1  Correct only metadata extraction; retain exact bytes, structure, extent, type, area, license, and CRS relation.",
        "2  Add focused acceptance and drift-refusal tests; require fresh public default-branch CI.",
        "3  Make zero network requests; verify the preserved exact bytes once, offline, with no automatic retry.",
        "4  Only on pass, promote without replacement and run the unchanged sign and operation preflight.",
        "5  Only if all gates pass, convert four approved DEM copies once each in fixed order; stop on first failure.",
    ]
    y = 900
    for item in steps:
        draw.rounded_rectangle((75, y, 1725, y + 67), radius=9, fill="white", outline=line)
        draw.text((100, y + 18), item, font=body, fill=ink)
        y += 77

    draw.text((75, 1308), "POST-OBSERVATION LIMIT", font=heading, fill=red)
    y = wrapped(draw, proposal["observed_representation"]["post_observation_bias"], (85, 1350), 128, body, ink)
    draw.rectangle((0, 1460, 1800, 1580), fill="#e3ebe8")
    draw.text((75, 1495), "DECISION REQUIRED", font=heading, fill=navy)
    draw.text((420, 1492), "Approve  |  Revise  |  Defer — with owner attestation", font=bold, fill=teal)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="PNG", optimize=True)
    print(json.dumps({"output": str(OUTPUT), "proposal_sha256": proposal_sha, "width": 1800, "height": 1580}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
