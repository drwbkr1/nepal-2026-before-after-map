"""Approved fixed-policy USGS metadata discovery. No asset content or credentials.

Every HTTP operation reserves an exclusive intent before sending. Search cannot
be resumed: a crash leaves an indeterminate request, not permission to replay it.
The whole inventory precedes the immutable, prospective source-selection lock.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from run_m2_landsat9_pixel_visual_recovery_001 import now, write_new
from m2_transfer_core import is_reparse_point, sha256_file

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
SCOPE = "optical-alternate-source-route-001"
APPROVAL = "records/source-gates/m2-optical-alternate-source-route-001-approval.json"
APPROVAL_SHA = "eea904b27f94d3055c9b98ed523b7f46c0bebf0ecd20fbe681d06fea2693a532"
PROPOSAL = "contracts/milestone-002-optical-alternate-source-route-001-proposal.json"
PROPOSAL_SHA = "9ff230d9edc31fb6df5afeda4ca8bf115ca105ea084ccd0e770fe3b188c765a7"
BUNDLE = "reviews/m2-optical-alternate-source-route-001/review-bundle.json"
BUNDLE_SHA = "98ab5b8969692461bc5e2c128ac99b1df9f1770c6b1e46e3734cc6d027d57d07"
CATALOG = "https://landsatlook.usgs.gov/stac-server/"
SEARCH = CATALOG + "search"
RIGHTS = "https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products"
COLLECTION = "landsat-c2l2-sr"
WINDOWS = {"before": ("2026-07-27T00:00:00Z", "2026-08-25T23:59:59.999999Z"),
           "after": ("2026-08-27T00:00:00Z", "2026-09-25T23:59:59.999999Z")}
ORDER = tuple((sensor, role) for sensor in ("landsat-8", "landsat-9") for role in WINDOWS)
PROVIDER_PLATFORM = {"landsat-8": "LANDSAT_8", "landsat-9": "LANDSAT_9"}
AOIS = ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")
EXCLUDED = frozenset(("LC09_L2SP_141040_20260810_20260811_02_T1",
                      "LC09_L2SP_141040_20260826_20260827_02_T1"))
PRODUCT = re.compile(r"LC0([89])_L2SP_141040_(\d{8})_(\d{8})_02_T1\Z")
SCENE = re.compile(r"LC([89])141040(\d{7})[A-Z]{3}\d{2}\Z")
LIMITS = {"root": 2, "search": 8, "detail": 4, "rights": 2, "recovery": 2}
MAX_RESPONSE = 5_000_000


class PolicyStop(RuntimeError):
    """Fixed public failure code; never raw provider/exception text."""


def unique_json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def read(path):
    p = Path(path)
    if not p.is_file() or p.is_symlink() or is_reparse_point(p):
        raise PolicyStop("required_control_missing_or_unsafe")
    return json.loads(p.read_text(encoding="utf-8"))


def safe_path(root, path):
    root, path = Path(root).absolute(), Path(path).absolute()
    if not path.is_relative_to(root) or path == root:
        raise PolicyStop("controlled_path_escape")
    for p in (path, *path.parents):
        if p.is_symlink() or (p.exists() and is_reparse_point(p)):
            raise PolicyStop("controlled_path_unsafe")
        if p == root:
            break


def controls():
    for ref, digest in ((APPROVAL, APPROVAL_SHA), (PROPOSAL, PROPOSAL_SHA), (BUNDLE, BUNDLE_SHA)):
        if sha256_file(ROOT / ref) != digest:
            raise PolicyStop("approved_control_hash_drift")
    a = read(ROOT / APPROVAL)
    if (a.get("decision") != "approved_one_conditional_envelope"
            or a.get("proposal_sha256") != PROPOSAL_SHA or a.get("review_bundle_sha256") != BUNDLE_SHA):
        raise PolicyStop("owner_approval_invalid")
    for item in read(ROOT / BUNDLE)["bound_files"]:
        if sha256_file(ROOT / item["ref"]) != item["sha256"]:
            raise PolicyStop("bound_evidence_drift")
    return a


def focus_geometries():
    from shapely.geometry import shape
    aoi = read(ROOT / "config/aoi/approved-study-areas.geojson")
    result = {f["properties"]["aoi_id"]: f["geometry"] for f in aoi["features"]
              if f["properties"]["aoi_id"] in AOIS}
    if set(result) != set(AOIS) or any(not shape(g).is_valid or shape(g).is_empty for g in result.values()):
        raise PolicyStop("approved_focus_geometry_invalid")
    return result


def utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("utc_required")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def exact_integer_identity(value, expected):
    return (not isinstance(value, bool) and
            ((isinstance(value, int) and value == expected) or
             (isinstance(value, str) and re.fullmatch(r"\d+", value) is not None and int(value) == expected)))


def item_disposition(item, sensor, role, geometries):
    """Retain rejection reasons; independent fields must agree with product ID."""
    from shapely.geometry import shape
    reasons, out = [], {"query_platform": sensor, "query_role": role}
    if not isinstance(item, dict):
        return {**out, "eligible": False, "reasons": ["item_not_object"]}
    props = item.get("properties")
    if not isinstance(props, dict):
        return {**out, "eligible": False, "reasons": ["properties_missing"]}
    item_id = item.get("id")
    # USGS SR item identity may carry a collection-role suffix. Exact product
    # identity must still agree with any independent product-ID property.
    base = item_id[:-3] if isinstance(item_id, str) and item_id.endswith("_SR") else item_id
    product = props.get("landsat:product_id", base)
    if product != base:
        reasons.append("item_product_identity_disagreement")
    match = PRODUCT.fullmatch(product) if isinstance(product, str) else None
    out.update({"item_id": item_id if isinstance(item_id, str) else None,
                "product_id": product if isinstance(product, str) else None})
    if not match:
        reasons.append("product_identity_outside_fixed_policy")
    if product in EXCLUDED:
        reasons.append("known_terminal_product_never_requeue")
    if item.get("type") != "Feature" or item.get("collection") != COLLECTION:
        reasons.append("item_type_or_collection_invalid")
    reported_platform = props.get("platform")
    platform = {"LANDSAT_8": "landsat-8", "LANDSAT_9": "landsat-9"}.get(reported_platform, reported_platform)
    out["reported_catalog_platform"] = reported_platform if isinstance(reported_platform, str) else None
    out["platform"] = platform if isinstance(platform, str) else None
    if platform != sensor or (match and platform != "landsat-" + match[1]):
        reasons.append("platform_identity_mismatch")
    for key, expected in (("landsat:wrs_path", 141), ("landsat:wrs_row", 40),
                          ("landsat:collection_number", 2), ("landsat:collection_category", "T1")):
        value = props.get(key)
        good = exact_integer_identity(value, expected) if isinstance(expected, int) else value == expected
        if isinstance(value, bool) or not good:
            reasons.append(key.replace(":", "_") + "_missing_or_mismatch")
    # Product ID itself explicitly encodes L2SP. When reported independently it
    # must agree; absence is recorded rather than inventing a catalog field.
    reported_level = props.get("landsat:processing_level", props.get("landsat:correction"))
    if reported_level is not None and reported_level != "L2SP":
        reasons.append("processing_level_disagreement")
    out["processing_level"] = "L2SP" if match else None
    out["processing_level_identity_source"] = "exact_product_id_and_independent_field_when_present"
    instant = props.get("datetime")
    out["acquired_at_utc"] = instant if isinstance(instant, str) else None
    try:
        acquired = utc(instant)
        if not utc(WINDOWS[role][0]) <= acquired <= utc(WINDOWS[role][1]):
            reasons.append("acquisition_outside_fixed_window")
        if match and acquired.strftime("%Y%m%d") != match[2]:
            reasons.append("acquisition_product_date_disagreement")
    except (ValueError, TypeError):
        acquired = None
        reasons.append("acquisition_utc_missing_or_invalid")
    scene = props.get("landsat:scene_id")
    out["scene_id"] = scene if isinstance(scene, str) else None
    scene_match = SCENE.fullmatch(scene) if isinstance(scene, str) else None
    if (not scene_match or not acquired or not match or scene_match[1] != match[1]
            or scene_match[2] != acquired.strftime("%Y%j")):
        reasons.append("scene_identity_missing_or_disagreeing")
    cloud = props.get("eo:cloud_cover")
    if isinstance(cloud, bool) or not isinstance(cloud, (int, float)) or not math.isfinite(cloud) or not 0 <= cloud <= 100:
        reasons.append("cloud_cover_unknown_or_invalid")
        cloud = None
    out["eo_cloud_cover"] = cloud
    containment = {}
    try:
        geometry = item.get("geometry")
        footprint = shape(geometry)
        if geometry.get("type") not in ("Polygon", "MultiPolygon") or not footprint.is_valid or footprint.is_empty:
            raise ValueError("invalid_footprint")
        if not (-180 <= footprint.bounds[0] <= footprint.bounds[2] <= 180 and
                -90 <= footprint.bounds[1] <= footprint.bounds[3] <= 90):
            raise ValueError("invalid_bounds")
        containment = {key: footprint.covers(shape(g)) for key, g in geometries.items()}
        if not all(containment.values()):
            reasons.append("catalog_footprint_not_full_focus_containment")
    except (ValueError, TypeError, AttributeError):
        reasons.append("catalog_footprint_unknown_or_invalid")
    out.update({"catalog_focus_containment": containment, "geometry": item.get("geometry"),
                "eligible": not reasons, "reasons": reasons,
                "metadata_footprint_is_not_pixel_qa": True})
    return out


def rank_pairs(dispositions, complete):
    if not complete:
        raise PolicyStop("incomplete_inventory_cannot_rank_or_select")
    unique = {}
    for item in dispositions:
        if item["eligible"]:
            key = item["product_id"]
            if key in unique and unique[key] != item:
                raise PolicyStop("duplicate_catalog_identity_disagreement")
            unique[key] = item
    pairs = []
    for sensor in ("landsat-8", "landsat-9"):
        before = [i for i in unique.values() if i["platform"] == sensor and i["query_role"] == "before"]
        after = [i for i in unique.values() if i["platform"] == sensor and i["query_role"] == "after"]
        for b in before:
            for a in after:
                rank = [max(b["eo_cloud_cover"], a["eo_cloud_cover"]), b["eo_cloud_cover"] + a["eo_cloud_cover"],
                        (utc(a["acquired_at_utc"]) - utc(b["acquired_at_utc"])).total_seconds(), b["product_id"], a["product_id"]]
                pairs.append({"platform": sensor, "before": b, "after": a, "rank_tuple": rank})
    pairs.sort(key=lambda p: tuple(p["rank_tuple"]))
    return [{"locked_rank": n, **pair} for n, pair in enumerate(pairs[:2], 1)]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Redirect is an outcome; not an uncounted new request.


def http(method, url, body):
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method=method,
                                    headers={"User-Agent": "nepal-2026-before-after-map/alternate-optical-metadata-only",
                                             "Content-Type": "application/json", "Accept": "application/json,text/html"})
    opener = urllib.request.build_opener(NoRedirect())
    try:
        response = opener.open(request, timeout=45)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read(MAX_RESPONSE + 1)
        return response.code, response.headers.get("Content-Type", ""), raw


class MetadataLedger:
    def __init__(self, path, transport=http, sleeper=time.sleep, *, seed=None):
        self.path, self.transport, self.sleeper = Path(path), transport, sleeper
        if self.path.exists() or self.path.is_symlink():
            raise PolicyStop("metadata_attempt_already_reserved")
        self.path.mkdir(parents=True, exist_ok=False)
        write_new(self.path / "intent.json", {"status": "reserved_before_any_http", "at_utc": now(),
                                              "approval_sha256": APPROVAL_SHA, "maximum_requests": 18})
        self.counts = {key: 0 for key in LIMITS} if seed is None else dict(seed["counts"])
        self.total, self.outcomes = (0, []) if seed is None else (seed["total"], list(seed["outcomes"]))
        if seed is not None:
            write_new(self.path / "inherited-budget.json", {"previous_attempt_terminal_sha256": seed["terminal_sha256"],
                       "prior_request_count": self.total, "prior_counts": self.counts,
                       "mechanical_correction_not_transient_retry": True})

    @staticmethod
    def sealed_budget(path):
        path = Path(path)
        terminal = read(path / "terminal.json")
        if terminal.get("status") != "defer_no_eligible_metadata_pair" or terminal.get("pairs") != []:
            raise PolicyStop("prior_metadata_terminal_not_expected")
        counts, total, outcomes = {key: 0 for key in LIMITS}, 0, []
        for intent_path in sorted(path.glob("request-*-intent.json")):
            intent = read(intent_path); n = intent["number"]
            if n != total + 1:
                raise PolicyStop("prior_metadata_request_sequence_invalid")
            outcome = read(path / f"request-{n:02d}-outcome.json")
            response = path / f"response-{n:02d}.{'html' if intent['kind']=='rights' else 'json'}"
            if not response.is_file() or outcome.get("http_status") != 200:
                raise PolicyStop("prior_metadata_outcome_incomplete")
            counts["recovery" if intent["recovery"] else intent["kind"]] += 1
            total = n; outcomes.append(outcome)
        if counts != terminal["metadata_budget_counts"] or total != terminal["metadata_http_requests"]:
            raise PolicyStop("prior_metadata_budget_drift")
        return {"counts": counts, "total": total, "outcomes": outcomes, "terminal_sha256": sha256_file(path / "terminal.json")}

    @classmethod
    def rights_refresh(cls, path, transport=http, sleeper=time.sleep):
        """Continue only the one remaining rights read after sealed discovery.

        Never replay a request whose outcome is absent, including after a crash.
        """
        obj = cls.__new__(cls)
        obj.path, obj.transport, obj.sleeper = Path(path), transport, sleeper
        terminal = read(obj.path / "terminal.json")
        if terminal.get("status") != "pass_complete_fixed_policy_selection_locked":
            raise PolicyStop("sealed_selection_required_for_rights_refresh")
        inherited = read(obj.path / "inherited-budget.json") if (obj.path / "inherited-budget.json").is_file() else None
        obj.counts, obj.total, obj.outcomes = (dict(inherited["prior_counts"]), inherited["prior_request_count"], []) if inherited else ({key: 0 for key in LIMITS}, 0, [])
        for p in sorted(obj.path.glob("request-*-intent.json")):
            intent = read(p)
            n = intent["number"]
            if n != obj.total + 1 or not (obj.path / f"request-{n:02d}-outcome.json").is_file():
                raise PolicyStop("indeterminate_metadata_request_no_replay")
            obj.total = n
            obj.counts["recovery" if intent["recovery"] else intent["kind"]] += 1
            obj.outcomes.append(read(obj.path / f"request-{n:02d}-outcome.json"))
        obj.rights_only = True
        return obj

    def validate_url(self, kind, url):
        u = urllib.parse.urlsplit(url)
        if (u.scheme != "https" or u.username is not None or u.password is not None
                or u.fragment or u.port not in (None, 443)):
            raise PolicyStop("metadata_url_unsafe")
        if kind == "rights":
            valid = url == RIGHTS
        else:
            valid = u.netloc == "landsatlook.usgs.gov"
            if kind == "root":
                valid &= u.path in ("/stac-server/", "/stac-server/conformance") and not u.query
            elif kind == "search":
                valid &= u.path == "/stac-server/search"
            elif kind == "detail":
                valid &= bool(re.fullmatch(r"/stac-server/collections/landsat-c2l2-sr/items/LC0[89]_L2SP_141040_\d{8}_\d{8}_02_T1(?:_SR)?", u.path)) and not u.query
            else:
                valid = False
        if not valid:
            raise PolicyStop("metadata_host_or_path_outside_envelope")

    def request(self, kind, url, method="GET", body=None, recovery=False):
        if getattr(self, "rights_only", False) and kind != "rights":
            raise PolicyStop("sealed_catalog_cannot_query_again")
        self.validate_url(kind, url)
        if method not in ("GET", "POST") or (kind != "search" and method != "GET"):
            raise PolicyStop("metadata_http_method_invalid")
        if kind == "search" and hasattr(self, "query_context"):
            if method == "GET":
                values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query, strict_parsing=True)
                if any(len(v) != 1 for v in values.values()):
                    raise PolicyStop("pagination_duplicate_query_parameter")
                values = {key: value[0] for key, value in values.items()}
            else:
                values = body
            if not isinstance(values, dict) or set(values) - set(self.query_context) - {"token"}:
                raise PolicyStop("pagination_query_scope_unresolved")
            for key, expected in self.query_context.items():
                value = values.get(key)
                if key == "query" and isinstance(value, str):
                    value = json.loads(value, object_pairs_hook=unique_json_pairs)
                if key == "query":
                    expected = json.loads(expected)
                elif key == "limit":
                    value, expected = str(value), str(expected)
                if value != expected:
                    raise PolicyStop("pagination_changed_fixed_query_scope")
        if self.total >= 18 or (not recovery and self.counts[kind] >= LIMITS[kind]) or (recovery and self.counts["recovery"] >= 2):
            raise PolicyStop("metadata_request_budget_exhausted")
        self.total += 1
        self.counts["recovery" if recovery else kind] += 1
        n = self.total
        # Only approved, public metadata request URLs can enter this ledger.
        intent = {"number": n, "kind": kind, "url": url, "method": method, "body": body,
                  "recovery": recovery, "at_utc": now()}
        write_new(self.path / f"request-{n:02d}-intent.json", intent)
        try:
            status, mime, raw = self.transport(method, url, body)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            status, mime, raw = None, "", b""
        transient = status is None or status == 429 or (status is not None and 500 <= status <= 599)
        outcome = {"number": n, "kind": kind, "http_status": status, "response_bytes": len(raw),
                   "response_sha256": hashlib.sha256(raw).hexdigest(), "transient": transient, "at_utc": now()}
        write_new(self.path / f"request-{n:02d}-outcome.json", outcome)
        self.outcomes.append(outcome)
        if len(raw) > MAX_RESPONSE:
            raise PolicyStop("metadata_response_size_cap_or_truncation")
        if transient:
            if recovery or self.counts["recovery"] >= 2 or self.total >= 18:
                raise PolicyStop("metadata_transient_recovery_exhausted")
            self.sleeper(2)
            return self.request(kind, url, method, body, recovery=True)
        if status != 200:
            raise PolicyStop("metadata_access_or_provider_response_stop")
        if kind == "rights":
            if "text/html" not in mime:
                raise PolicyStop("official_page_content_type_invalid")
            with (self.path / f"response-{n:02d}.html").open("xb") as out:
                out.write(raw); out.flush()
            return raw.decode("utf-8", errors="strict")
        if "json" not in mime:
            raise PolicyStop("catalog_content_type_invalid")
        try:
            data = json.loads(raw, object_pairs_hook=unique_json_pairs,
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite")))
        except (ValueError, UnicodeError):
            raise PolicyStop("catalog_json_invalid") from None
        write_new(self.path / f"response-{n:02d}.json", data)
        return data


def discover(ledger, geometries):
    from shapely.geometry import shape
    from shapely.ops import unary_union
    bbox = list(unary_union([shape(g) for g in geometries.values()]).bounds)
    inventory, dispositions, queries = [], [], []
    for sensor, role in ORDER:
        params = {"collections": COLLECTION, "bbox": ",".join(map(str, bbox)),
                  "datetime": "/".join(WINDOWS[role]), "limit": 100,
                  "query": json.dumps({"platform": {"eq": PROVIDER_PLATFORM[sensor]}}, separators=(",", ":"))}
        # Same path/row policy is checked against the exact ID and independent
        # fields locally. Removing an unverified server-side numeric formatting
        # assumption changes no candidate eligibility or ranking predicate.
        url, method, body = SEARCH + "?" + urllib.parse.urlencode(params), "GET", None
        ledger.query_context = params
        seen, returned = set(), 0
        while True:
            fingerprint = json.dumps([url, method, body], sort_keys=True)
            if fingerprint in seen:
                raise PolicyStop("pagination_cycle_incomplete")
            seen.add(fingerprint)
            data = ledger.request("search", url, method, body)
            if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
                raise PolicyStop("search_schema_incomplete")
            features = data["features"]
            if len(features) > 100:
                raise PolicyStop("feature_page_cap_or_truncation")
            returned += len(features)
            for feature in features:
                inventory.append({"query_platform": sensor, "query_role": role, "item": feature})
                dispositions.append(item_disposition(feature, sensor, role, geometries))
            next_links = [link for link in data.get("links", []) if link.get("rel") == "next"]
            if len(next_links) > 1:
                raise PolicyStop("pagination_ambiguous_incomplete")
            matched = data.get("numberMatched", data.get("context", {}).get("matched"))
            if not next_links:
                if matched is not None and (not isinstance(matched, int) or matched != returned):
                    raise PolicyStop("pagination_count_incomplete")
                if len(features) == 100 and matched is None:
                    raise PolicyStop("unproven_complete_full_page")
                break
            link = next_links[0]
            url = urllib.parse.urljoin(SEARCH, link.get("href", ""))
            method = link.get("method", "GET")
            body = link.get("body")
            if method == "POST" and link.get("merge"):
                raise PolicyStop("pagination_merge_semantics_unresolved")
        queries.append({"platform": sensor, "role": role, "features_returned": returned,
                        "pages": len(seen), "complete": True})
    return {"queries": queries, "complete": True, "inventory": inventory, "dispositions": dispositions}


def lock_selection(ledger, discovery, geometries):
    # Full query evidence remains available even if shortlisted detail validation
    # fails. Detail content cannot change the prospective rank.
    write_new(ledger.path / "inventory.json", discovery)
    pairs = rank_pairs(discovery["dispositions"], discovery["complete"])
    details = {}
    for pair in pairs:
        for role in ("before", "after"):
            candidate = pair[role]
            product = candidate["product_id"]
            if product in details:
                continue
            url = CATALOG + "collections/" + COLLECTION + "/items/" + urllib.parse.quote(candidate["item_id"], safe="")
            detail = ledger.request("detail", url)
            checked = item_disposition(detail, pair["platform"], role, geometries)
            if checked != candidate:
                raise PolicyStop("selected_detail_identity_or_rank_drift")
            details[product] = checked
    result = {"schema_version": "1.0", "status": "pass_complete_fixed_policy_selection_locked" if pairs else "defer_no_eligible_metadata_pair",
              "locked_at_utc": now(), "approval_sha256": APPROVAL_SHA, "proposal_sha256": PROPOSAL_SHA,
              "inventory_sha256": sha256_file(ledger.path / "inventory.json"), "pairs": pairs,
              "metadata_requests": ledger.total, "metadata_budget_counts": ledger.counts,
              "source_payload_requests": 0, "registration_measured": False, "scientific_admission": False}
    write_new(ledger.path / "selection-manifest.json", result)
    return result
