#!/usr/bin/env python3
"""Check anonymous HTTPS headers for fourteen prospective DEM tiles; acquire no payload."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_REF = "records/observations/m2-radar-dem-swath-catalog-001.json"
DEM_MANIFEST_REF = "records/source-gates/m2-dem-candidate-manifest.json"
DEM_APPROVAL_REF = "records/source-gates/m2-dem-amendment-approval.json"
OUTPUT_REF = "records/observations/m2-radar-dem-candidate-heads-001.json"
HOST = "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def head(item_id: str) -> dict[str, object]:
    url = f"{HOST}/{item_id}/{item_id}.tif"
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Nepal-evidence-map-source-review/1.0"})
    result: dict[str, object] = {"item_id": item_id, "anonymous_https_url": url, "checked_at_utc": now_utc()}
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
            result.update({
                "http_status": response.status,
                "content_length_bytes": int(response.headers.get("Content-Length", "0")),
                "content_type": response.headers.get("Content-Type"),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "accept_ranges": response.headers.get("Accept-Ranges"),
                "redirect_followed": False,
                "response_body_read": False,
            })
    except urllib.error.HTTPError as exc:
        result.update({"http_status": exc.code, "error_type": "HTTPError", "redirect_followed": False, "response_body_read": False})
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        result.update({"http_status": None, "error_type": type(exc).__name__, "redirect_followed": False, "response_body_read": False})
    return result


def main() -> int:
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("candidate HEAD observation already exists")
    catalog = json.loads((ROOT / CATALOG_REF).read_text(encoding="utf-8"))
    dem_manifest = json.loads((ROOT / DEM_MANIFEST_REF).read_text(encoding="utf-8"))
    approval = json.loads((ROOT / DEM_APPROVAL_REF).read_text(encoding="utf-8"))
    if (
        catalog.get("status") != "local_zero_decision_public_metadata_inventory_only"
        or len(catalog.get("public_stac_observations", [])) != 14
        or any(row.get("http_status") != 200 or row.get("item_id") != row.get("returned_item_id") for row in catalog["public_stac_observations"])
        or len(approval.get("authorized_source_ids", [])) != 4
        or dem_manifest.get("distribution_route", {}).get("method") != "anonymous HTTPS GET after approval and fresh preflight"
    ):
        raise SystemExit("candidate or prior approval binding differs")
    observations = [head(row["item_id"]) for row in catalog["public_stac_observations"]]
    value = {
        "schema_version": "1.0",
        "observation_id": "NEPAL-M2-RADAR-DEM-CANDIDATE-HEADS-001",
        "observed_at_utc": now_utc(),
        "status": "local_zero_decision_public_asset_header_inventory_only",
        "input_bindings": [{"ref": ref, "sha256": sha256(ref)} for ref in (CATALOG_REF, DEM_MANIFEST_REF, DEM_APPROVAL_REF)],
        "method": "One unauthenticated HEAD per prospective public S3 mirror TIFF URL; redirects refused; no payload bytes requested or read.",
        "observations": observations,
        "limits": {
            "prior_four_tile_license_document_acceptance_reused_as_rights_context_only": True,
            "four_tile_acquisition_approval_extended": False,
            "new_tile_source_adopted_or_acquired": False,
            "payload_integrity_or_raster_fitness_established": False,
            "no_network_or_content_action_authorized_by_this_record": True,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "count": len(observations), "http_200": sum(row.get("http_status") == 200 for row in observations)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
