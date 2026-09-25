"""Portable checks for the approved, still conditional optical pair packet."""

import hashlib
import json
import unittest
from pathlib import Path

from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = "reviews/m2-optical-pair-pilot-001/review-bundle.json"
PROPOSAL = "contracts/milestone-002-optical-pair-pilot-001-proposal.json"
APPROVAL = "records/source-gates/m2-optical-pair-pilot-001-approval.json"


def load(ref):
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha(ref):
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OpticalPairPilotReviewTest(unittest.TestCase):
    def test_exact_packet_and_conditional_authority(self):
        bundle = load(BUNDLE)
        proposal = load(PROPOSAL)
        approval = load(APPROVAL)
        self.assertEqual(sha(BUNDLE), "0aa10813289f917e44cb684c86d78e8b1b381a8271993b202c87d6e262703870")
        self.assertEqual(sha(PROPOSAL), "82f394235b3beee5e8e05e8a6515f425b88bba1b7b947422efaacab720f252a5")
        for artifact in bundle["artifacts"]:
            self.assertEqual(sha(artifact["path"]), artifact["sha256"])
        self.assertEqual(approval["decision"], "approve")
        self.assertEqual(approval["owner_statement_verbatim"], "approve")
        self.assertFalse(approval["explicit_attestation_statement"])
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], sha(BUNDLE))
        self.assertEqual(approval["bindings"]["proposal_sha256"], sha(PROPOSAL))
        self.assertEqual(approval["authority"]["exact_product_ids_in_order"],
                         [item["provider_product_id"] for item in proposal["exact_sources"]])
        self.assertFalse(approval["authority"]["new_terms_acceptance"])
        self.assertFalse(approval["authority"]["baseline_admission_or_change_analysis"])
        self.assertFalse(approval["authority"]["derived_pixel_or_scientific_publication"])

    def test_exact_catalog_identity_and_footprint_scope(self):
        proposal = load(PROPOSAL)
        catalog = load("records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json")
        live = load("records/observations/m2-optical-shortlist-live-metadata-001.json")
        areas = load("config/aoi/approved-study-areas.geojson")
        by_id = {row["provider_product_id"]: row for row in catalog["rows"]}
        live_by_id = {row["provider_product_id"]: row for row in live["products"]}
        area_by_id = {row["properties"]["aoi_id"]: shape(row["geometry"]) for row in areas["features"]}
        self.assertEqual([row["role"] for row in proposal["exact_sources"]], ["before", "after"])
        for source in proposal["exact_sources"]:
            source_id = source["provider_product_id"]
            row = by_id[source_id]
            checked = live_by_id[source_id]
            self.assertEqual(source["name"], row["name"])
            self.assertEqual(source["name"], checked["name"])
            self.assertEqual(source["content_length_bytes"], checked["content_length_bytes"])
            checksums = {item["Algorithm"]: item["Value"] for item in checked["provider_checksums"]}
            self.assertEqual(source["provider_md5"], checksums["MD5"])
            self.assertEqual(source["provider_blake3"], checksums["BLAKE3"])
            footprint = shape(row["footprint"])
            self.assertTrue(footprint.covers(area_by_id["AOI-SOURCE"]))
            self.assertTrue(footprint.covers(area_by_id["AOI-UPPER-CORRIDOR"]))
            self.assertFalse(footprint.covers(area_by_id["AOI-OVERVIEW"]))
        self.assertTrue(proposal["claim_boundary"]["overview_full_pixel_coverage_claim"] is False)


if __name__ == "__main__":
    unittest.main()
