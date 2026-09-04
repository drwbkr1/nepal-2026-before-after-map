#!/usr/bin/env python3
"""Render the M2 Sentinel retained-failure recovery review surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 1720
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
    trigger = proposal["trigger"]

    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f0e7")
    draw = ImageDraw.Draw(image)
    navy, ink, muted, teal, amber, red, line = "#18324a", "#1d252c", "#5e6a72", "#167061", "#9a5d00", "#9a382d", "#c8d0d3"

    draw.rectangle((0, 0, WIDTH, 248), fill=navy)
    draw.text((MARGIN, 40), "NEPAL 2026  |  M2 SENTINEL RECOVERY REVIEW", font=font(28, bold=True), fill="#9fd8d0")
    draw.text((MARGIN, 91), "Retained truncation and one fresh retry", font=font(44, bold=True), fill="white")
    draw.text((MARGIN, 174), f"Proposal SHA-256  {proposal_sha}", font=font(21), fill="#d7e3ea")

    stats = [
        ("3", "promoted + container pass"),
        ("1", "retained failed transfer"),
        ("4", "authorized, unattempted"),
        ("0", "pixel results"),
    ]
    stat_top = 280
    stat_width = (WIDTH - 2 * MARGIN - 54) // 4
    for index, (value, label) in enumerate(stats):
        x = MARGIN + index * (stat_width + 18)
        draw.rounded_rectangle((x, stat_top, x + stat_width, stat_top + 112), radius=12, fill="white", outline=line)
        draw.text((x + 20, stat_top + 13), value, font=font(32, bold=True), fill=navy)
        draw.text((x + 20, stat_top + 67), label, font=font(18), fill=muted)

    y = 438
    draw.text((MARGIN, y), "WHAT FAILED", font=font(22, bold=True), fill=red)
    y = wrapped(
        draw,
        f"{trigger['failed_source_id']} ended after {trigger['partial_bytes_preserved']:,} of {trigger['expected_size_bytes']:,} expected bytes. The partial is preserved with SHA-256 {trigger['partial_sha256']} and was never promoted.",
        MARGIN,
        y + 44,
        WIDTH - MARGIN,
        24,
        fill=ink,
    )

    y += 26
    draw.text((MARGIN, y), "WHY THERE IS NO RESUME", font=font(22, bold=True), fill=amber)
    y = wrapped(
        draw,
        "The failed response did not retain both verified byte-range support and an unchanged strong remote-object identity. Recovery therefore restarts from byte zero in a distinct staging path and keeps the failed bytes unchanged.",
        MARGIN,
        y + 44,
        WIDTH - MARGIN,
        24,
        fill=ink,
    )

    cards_top = y + 34
    gap = 22
    card_width = (WIDTH - 2 * MARGIN - gap) // 2
    card(
        draw,
        (MARGIN, cards_top, MARGIN + card_width, cards_top + 300),
        "APPROVAL WOULD AUTHORIZE ONLY",
        "One fresh transfer of the same exact product from byte zero; a new exclusive staging identity; current rights, catalog, path, length, checksum, and ZIP/SAFE checks; then continuation of the four untouched original products only after recovery passes.",
        teal,
    )
    card(
        draw,
        (MARGIN + card_width + gap, cards_top, WIDTH - MARGIN, cards_top + 300),
        "STILL PROHIBITED",
        "Resume or deletion of the partial; staging-path reuse; product substitution; source-scope changes; terms or account action; credential exposure; orbit or radar processing; pixel admission; change mapping; attribution; or scientific publication.",
        red,
    )

    boundary_top = cards_top + 350
    draw.text((MARGIN, boundary_top), "RECOVERY STOP RULE", font=font(22, bold=True), fill=navy)
    y = wrapped(
        draw,
        "Any second failure remains terminal for its new recovery identity. It stops the sequence and requires another explicit review. Approval does not authorize repeated attempts.",
        MARGIN,
        boundary_top + 44,
        WIDTH - MARGIN,
        24,
        fill=ink,
    )

    decision_top = y + 42
    draw.rounded_rectangle((MARGIN, decision_top, WIDTH - MARGIN, decision_top + 245), radius=14, fill="#fff7df", outline="#d7a53b", width=3)
    draw.text((MARGIN + 24, decision_top + 20), "OWNER DECISION REQUIRED", font=font(22, bold=True), fill=amber)
    draw.text((MARGIN + 30, decision_top + 76), "[ ]  APPROVE", font=font(25, bold=True), fill=ink)
    draw.text((MARGIN + 395, decision_top + 76), "[ ]  REVISE", font=font(25, bold=True), fill=ink)
    draw.text((MARGIN + 735, decision_top + 76), "[ ]  DEFER", font=font(25, bold=True), fill=ink)
    wrapped(
        draw,
        "No option is selected. A completed response must bind item M2-SENTINEL-RECOVERY-001 and include the reviewer's attestation.",
        MARGIN + 30,
        decision_top + 133,
        WIDTH - MARGIN - 30,
        22,
        fill=ink,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(json.dumps({
        "status": "rendered_text_only",
        "width": WIDTH,
        "height": HEIGHT,
        "output": str(args.output),
        "output_sha256": sha256(args.output),
        "proposal_sha256": proposal_sha,
        "human_decision_count": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
