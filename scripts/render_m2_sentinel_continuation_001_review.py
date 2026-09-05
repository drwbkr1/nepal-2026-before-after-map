#!/usr/bin/env python3
"""Render the M2 Sentinel continuation-001 review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT, MARGIN = 1800, 1900, 78


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf")), size)


def wrapped(draw: ImageDraw.ImageDraw, text: str, left: int, top: int, right: int, size: int, *, bold: bool = False, fill: str = "#1d252c", spacing: int = 7) -> int:
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


def card(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], title: str, body: str, color: str) -> None:
    left, top, right, _ = rect
    draw.rounded_rectangle(rect, radius=14, fill="white", outline="#c8d0d3", width=2)
    draw.text((left + 24, top + 20), title, font=font(21, bold=True), fill=color)
    wrapped(draw, body, left + 24, top + 64, right - 24, 20)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    proposal_sha = sha256(args.proposal)

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f0e7")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, teal, amber, red, line = "#18324a", "#1d252c", "#5e6a72", "#167061", "#9a5d00", "#9a382d", "#c8d0d3"

    draw.rectangle((0, 0, WIDTH, 248), fill=navy)
    draw.text((MARGIN, 40), "NEPAL 2026  |  M2 SENTINEL CONTINUATION REVIEW", font=font(28, bold=True), fill="#9fd8d0")
    draw.text((MARGIN, 91), "Recovery passed; continuation stopped", font=font(43, bold=True), fill="white")
    draw.text((MARGIN, 174), f"Proposal SHA-256  {proposal_sha}", font=font(21), fill="#d7e3ea")

    stats = [("4", "promoted + container pass"), ("4", "authorized, unattempted"), ("0", "continuation attempts"), ("0", "pixel results")]
    stat_top = 280
    stat_width = (WIDTH - 2 * MARGIN - 54) // 4
    for index, (value, label) in enumerate(stats):
        x = MARGIN + index * (stat_width + 18)
        draw.rounded_rectangle((x, stat_top, x + stat_width, stat_top + 112), radius=12, fill="white", outline=line)
        draw.text((x + 20, stat_top + 13), value, font=font(32, bold=True), fill=navy)
        draw.text((x + 20, stat_top + 67), label, font=font(18), fill=muted)

    y = 438
    draw.text((MARGIN, y), "RECOVERY-002 SUCCEEDED", font=font(22, bold=True), fill=teal)
    y = wrapped(draw, "M1-SRC-004 transferred 1,732,332,897 bytes from byte zero, matched the provider MD5, and passed ZIP/SAFE container verification. Its local SHA-256 is a606cac063cc23e60a623f020192fc097d327f3dafadf1115802b2a458eaceab. Both prior partials remain preserved.", MARGIN, y + 44, WIDTH - MARGIN, 23)

    y += 24
    draw.text((MARGIN, y), "CONTINUATION STOPPED BEFORE MUTATION", font=font(22, bold=True), fill=red)
    y = wrapped(draw, "The supervisor failed in continuation_live_preflight with a generic code. No M1-SRC-005 attempt, payload request, staging directory, event directory, or destination exists. The exact cause is unknown because no safe underlying exception category was retained.", MARGIN, y + 44, WIDTH - MARGIN, 23)

    top = y + 34
    gap = 22
    card_width = (WIDTH - 2 * MARGIN - gap) // 2
    card(draw, (MARGIN, top, MARGIN + card_width, top + 345), "PROPOSED ROUTE", "A new continuation-only detached worker may process M1-SRC-005, 006, 008, and 010 in that exact order. Each gets at most one byte-zero attempt and must pass transfer plus container checks before the next source starts.", teal)
    card(draw, (MARGIN + card_width + gap, top, WIDTH - MARGIN, top + 345), "STILL PROHIBITED", "Any M1-SRC-004 request; resume or reuse; retry after failure; token storage or exception leakage; product or order changes; account, terms, MFA, or cost actions; pixels, baselines, terrain, change, attribution, or publication.", red)

    y = top + 395
    draw.text((MARGIN, y), "PROOF BEFORE TOKEN OR PAYLOAD", font=font(22, bold=True), fill=amber)
    y = wrapped(draw, "Synthetic tests must prove source isolation, safe error classification, secret exclusion, one-attempt ceilings, stop-on-first-failure, exclusive paths, redirect refusal, byte-zero requests, checksums, atomic promotion, and container gating. The exact commit must be on origin/main with passing public CI, followed by a final no-payload preflight.", MARGIN, y + 44, WIDTH - MARGIN, 23)

    y += 24
    draw.text((MARGIN, y), "LIMITATION", font=font(22, bold=True), fill=amber)
    y = wrapped(draw, "The correction can improve future evidence but cannot recover the missing exception category from the completed run. Container success establishes no raster readability, usable pixels, registration, or scientific change.", MARGIN, y + 44, WIDTH - MARGIN, 23)

    decision_top = y + 40
    draw.rounded_rectangle((MARGIN, decision_top, WIDTH - MARGIN, decision_top + 245), radius=14, fill="#fff7df", outline="#d7a53b", width=3)
    draw.text((MARGIN + 24, decision_top + 20), "OWNER DECISION REQUIRED", font=font(22, bold=True), fill=amber)
    draw.text((MARGIN + 30, decision_top + 76), "[ ]  APPROVE", font=font(25, bold=True), fill=ink)
    draw.text((MARGIN + 395, decision_top + 76), "[ ]  REVISE", font=font(25, bold=True), fill=ink)
    draw.text((MARGIN + 735, decision_top + 76), "[ ]  DEFER", font=font(25, bold=True), fill=ink)
    wrapped(draw, "No option is selected. A completed response must bind item M2-SENTINEL-CONTINUATION-001 and include the reviewer's attestation.", MARGIN + 30, decision_top + 133, WIDTH - MARGIN - 30, 22, fill=ink)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({"status": "rendered_text_only", "width": WIDTH, "height": HEIGHT, "output": str(args.output), "output_sha256": sha256(args.output), "proposal_sha256": proposal_sha, "human_decision_count": 0}, indent=2))


if __name__ == "__main__":
    main()
