from __future__ import annotations

import json
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REF = "records/source-gates/m2-orbit-osv-time-format-evidence.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-osv-precision-amendment-001-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-osv-precision-amendment-001/review-contract.json"
BLANK_REF = "reviews/m2-orbit-osv-precision-amendment-001/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-osv-precision-amendment-001-review-readiness.json"
STAGED_SHA256 = "a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4"
PROVIDER_MD5 = "ca7f36b1892073c883c4cff5c0517b9c"
PROVIDER_BLAKE3 = "ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b"


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OrbitOsvPrecisionAmendmentReviewTests(unittest.TestCase):
    def test_exact_tolerance_and_zero_network_boundary(self) -> None:
        proposal = json.loads((ROOT / PROPOSAL_REF).read_text(encoding="utf-8"))
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
        source = json.loads((ROOT / SOURCE_REF).read_text(encoding="utf-8"))
        local = source["local_observation"]
        self.assertEqual(local["validity_stop_shortfall_seconds"], 0.031829)
        self.assertEqual(local["sha256"], STAGED_SHA256)
        self.assertEqual(local["provider_md5"], PROVIDER_MD5)
        self.assertEqual(local["provider_blake3"], PROVIDER_BLAKE3)
        self.assertEqual(set(source["interpretation"]), {"observation", "inference", "attribution"})
        self.assertIn("does not explicitly define", source["limitations"][0])

    def test_review_is_blank_and_hash_bound(self) -> None:
        bundle = json.loads((ROOT / BUNDLE_REF).read_text(encoding="utf-8"))
        contract = json.loads((ROOT / CONTRACT_REF).read_text(encoding="utf-8"))
        blank = json.loads((ROOT / BLANK_REF).read_text(encoding="utf-8"))
        readiness = json.loads((ROOT / READINESS_REF).read_text(encoding="utf-8"))
        self.assertEqual(contract["review_bundle"]["manifest_sha256"], sha256(BUNDLE_REF))
        self.assertEqual(contract["items"], [{"item_id": "M2-ORBIT-OSV-PRECISION-AMENDMENT-001", "evidence_sha256": sha256(BUNDLE_REF)}])
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])
        self.assertEqual(readiness["review"]["human_decision_count"], 0)
        self.assertFalse(readiness["assertions"]["amendment_authorized"])
        self.assertTrue(bundle["review_surface"]["blank_state_verified"])


if __name__ == "__main__":
    unittest.main()
