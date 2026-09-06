from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_m2_orbit_osv_precision_amendment_001_review as review  # noqa: E402


class OrbitOsvPrecisionAmendmentReviewTests(unittest.TestCase):
    def test_exact_tolerance_and_zero_network_boundary(self) -> None:
        proposal = json.loads((ROOT / review.PROPOSAL_REF).read_text(encoding="utf-8"))
        amendment = proposal["proposed_amendment"]
        self.assertEqual(amendment["maximum_osv_endpoint_tolerance_seconds"], 1.0)
        self.assertEqual(amendment["maximum_new_owner_handoffs"], 0)
        self.assertEqual(amendment["maximum_new_catalog_requests"], 0)
        self.assertEqual(amendment["maximum_new_download_requests"], 0)
        self.assertEqual(amendment["maximum_local_validation_attempts"], 1)
        self.assertFalse(amendment["automatic_retry_authorized"])
        prohibited = " ".join(proposal["approval_would_not_authorize"])
        for source_id in ("M2-ORB-002", "M2-ORB-003", "M2-ORB-004"):
            self.assertIn(source_id, prohibited)

    def test_source_record_separates_observation_inference_and_attribution(self) -> None:
        source = json.loads((ROOT / review.SOURCE_REF).read_text(encoding="utf-8"))
        local = source["local_observation"]
        self.assertEqual(local["validity_stop_shortfall_seconds"], 0.031829)
        self.assertEqual(local["sha256"], review.STAGED_SHA256)
        self.assertEqual(local["provider_md5"], review.PROVIDER_MD5)
        self.assertEqual(local["provider_blake3"], review.PROVIDER_BLAKE3)
        self.assertEqual(set(source["interpretation"]), {"observation", "inference", "attribution"})
        self.assertIn("does not explicitly define", source["limitations"][0])

    def test_review_is_blank_and_hash_bound(self) -> None:
        bundle = json.loads((ROOT / review.BUNDLE_REF).read_text(encoding="utf-8"))
        contract = json.loads((ROOT / review.CONTRACT_REF).read_text(encoding="utf-8"))
        blank = json.loads((ROOT / review.BLANK_REF).read_text(encoding="utf-8"))
        readiness = json.loads((ROOT / review.READINESS_REF).read_text(encoding="utf-8"))
        self.assertEqual(contract["review_bundle"]["manifest_sha256"], review.sha256(review.BUNDLE_REF))
        self.assertEqual(contract["items"], [{"item_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001", "evidence_sha256": review.sha256(review.BUNDLE_REF)}])
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])
        self.assertEqual(readiness["review"]["human_decision_count"], 0)
        self.assertFalse(readiness["assertions"]["amendment_authorized"])
        self.assertTrue(bundle["review_surface"]["blank_state_verified"])


if __name__ == "__main__":
    unittest.main()
