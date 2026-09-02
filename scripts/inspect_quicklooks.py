#!/usr/bin/env python3
"""Acquire public quicklook assets only and create an auditable review sheet."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any
import json
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "records/source-gates/catalog-metadata.json"
OUTPUT = ROOT / "records/source-gates/quicklook-review.json"
SCRATCH = ROOT / "scratch/quicklooks"
CONTACT_SHEET = SCRATCH / "candidate-contact-sheet.jpg"
ENDPOINT = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def request_bytes(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "nepal-2026-before-after-map/1.0 quicklook-only"},
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read(), response.headers.get_content_type()
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"quicklook request failed after retries: {last_error}")


def request_json(url: str) -> dict[str, Any]:
    payload, _ = request_bytes(url)
    return json.loads(payload)


def make_contact_sheet(items: list[dict[str, Any]]) -> str:
    tile_width = 420
    tile_height = 390
    columns = 2
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, item in enumerate(items):
        image_path = ROOT / item["local_scratch_path"]
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((400, 310))
        x0 = (index % columns) * tile_width + 10
        y0 = (index // columns) * tile_height + 10
        sheet.paste(image, (x0, y0))
        label = item["product_stem"]
        wrapped = [label[start:start + 58] for start in range(0, len(label), 58)]
        text_y = y0 + 318
        for line in wrapped[:2]:
            draw.text((x0, text_y), line, fill="black", font=font)
            text_y += 14
        draw.text(
            (x0, text_y + 2),
            f"{item['content_type']} {item['width']}x{item['height']}",
            fill="black",
            font=font,
        )
    sheet.save(CONTACT_SHEET, "JPEG", quality=92)
    return sha256(CONTACT_SHEET.read_bytes()).hexdigest()


def main() -> None:
    metadata = json.loads(INPUT.read_text(encoding="utf-8"))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for record in metadata["records"]:
        exact_name = record["name"]
        params = {
            "$filter": f"Name eq '{exact_name}'",
            "$expand": "Assets",
            "$top": "1",
        }
        query_url = ENDPOINT + "?" + urllib.parse.urlencode(params)
        response = request_json(query_url)
        values = response.get("value", [])
        if len(values) != 1:
            raise RuntimeError(f"missing exact product while expanding assets: {exact_name}")
        assets = [
            asset for asset in values[0].get("Assets", [])
            if asset.get("Type") == "QUICKLOOK"
        ]
        result: dict[str, Any] = {
            "product_stem": record["product_stem"],
            "provider_product_id": record["provider_product_id"],
            "asset_query_url": query_url,
            "quicklook_asset_count": len(assets),
            "availability": "available" if len(assets) == 1 else "unavailable_or_ambiguous",
            "automated_checks": {},
            "visual_review_status": "pending",
            "visual_observations": [],
            "pixel_usability_status": "not_established",
            "disposition": "candidate",
        }
        if len(assets) == 1:
            asset = assets[0]
            payload, content_type = request_bytes(asset["DownloadLink"])
            image = Image.open(BytesIO(payload))
            extension = ".png" if content_type == "image/png" else ".jpg"
            local_path = SCRATCH / (record["product_stem"] + extension)
            local_path.write_bytes(payload)
            result.update({
                "quicklook_asset_id": asset.get("Id"),
                "download_link": asset.get("DownloadLink"),
                "content_type": content_type,
                "byte_size": len(payload),
                "sha256": sha256(payload).hexdigest(),
                "width": image.width,
                "height": image.height,
                "local_scratch_path": str(local_path.relative_to(ROOT)).replace("\\", "/"),
                "automated_checks": {
                    "asset_unique": "pass",
                    "image_decode": "pass",
                    "nonzero_dimensions": "pass" if image.width and image.height else "fail",
                    "full_product_download": "not_performed",
                },
            })
        results.append(result)

    downloadable = [item for item in results if item["availability"] == "available"]
    contact_hash = make_contact_sheet(downloadable) if downloadable else None
    review = {
        "schema_version": "1.0",
        "review_id": "QUICKLOOK-REVIEW-001",
        "status": "in_progress",
        "retrieved_at_utc": now_utc(),
        "source": "Copernicus Data Space OData product Assets expansion",
        "candidate_count": len(results),
        "available_quicklook_count": len(downloadable),
        "contact_sheet_scratch_path": str(CONTACT_SHEET.relative_to(ROOT)).replace("\\", "/") if downloadable else None,
        "contact_sheet_sha256": contact_hash,
        "authentication": "none",
        "product_download": "not_performed",
        "claim_boundary": (
            "Quicklooks support coarse visual screening only and cannot establish "
            "AOI pixel usability, quantitative change, or event causation."
        ),
        "records": results,
        "overall_observations": [],
        "limitations": [
            "Quicklooks are reduced-resolution browse assets.",
            "Scratch images are excluded from Git and are not approved source custody.",
            "Cloud, snow, terrain, radar geometry, masks, and co-registration still require product-level review.",
        ],
    }
    OUTPUT.write_text(
        json.dumps(review, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        f"Quicklooks available {len(downloadable)}/{len(results)}; "
        f"contact sheet {contact_hash}"
    )


if __name__ == "__main__":
    main()
