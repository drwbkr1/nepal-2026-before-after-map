from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "prepare_m2_dem_amendment.py"
SPEC = importlib.util.spec_from_file_location("prepare_m2_dem_amendment", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2DemAmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = load("records/source-gates/m2-dem-metadata-receipt.json")
        cls.manifest = load("records/source-gates/m2-dem-candidate-manifest.json")
        cls.gate = load("records/source-gates/m2-dem-source-gate.json")
        cls.proposal = load("contracts/milestone-002-dem-amendment-proposal.json")
        cls.bundle = load("reviews/m2-dem-amendment/review-bundle.json")
        cls.contract = load("reviews/m2-dem-amendment/review-contract.json")
        cls.blank = load("reviews/m2-dem-amendment/blank-response.json")

    def test_exact_four_tile_set_and_total(self) -> None:
        self.assertEqual(
            {record["item_id"] for record in self.manifest["records"]},
            set(MODULE.TILE_IDS),
        )
        self.assertEqual(self.manifest["summary"]["tile_count"], 4)
        self.assertEqual(self.manifest["summary"]["combined_content_length_bytes"], 170302058)
        self.assertEqual(
            self.manifest["summary"]["combined_content_length_bytes"],
            sum(record["anonymous_head"]["content_length_bytes"] for record in self.manifest["records"]),
        )

    def test_union_bbox_requires_all_four_tiles(self) -> None:
        self.assertEqual(self.receipt["approved_aoi"]["overall_bbox_wgs84"], [84.7, 27.75, 85.65, 28.45])
        self.assertTrue(all("AOI-OVERVIEW" in record["intersects_approved_aois"] for record in self.manifest["records"]))
        detailed = next(record for record in self.manifest["records"] if record["source_id"] == "M2-DEM-004")
        self.assertEqual(
            detailed["intersects_approved_aois"],
            ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"],
        )

    def test_metadata_capture_requested_no_payload_or_account(self) -> None:
        assertions = self.receipt["assertions"]
        self.assertFalse(assertions["payload_bytes_requested"])
        self.assertFalse(assertions["account_or_authentication_used"])
        self.assertFalse(assertions["license_accepted"])
        self.assertTrue(assertions["all_stac_items_found"])
        self.assertTrue(assertions["all_anonymous_object_heads_found"])

    def test_license_and_scope_remain_real_blockers(self) -> None:
        self.assertEqual(self.gate["decision"]["status"], "blocked")
        self.assertEqual(len(self.gate["sources"]), 4)
        for source in self.gate["sources"]:
            by_id = {criterion["id"]: criterion for criterion in source["criteria"]}
            self.assertEqual(by_id["terms-acceptance"]["status"], "unknown")
            self.assertEqual(by_id["scope-authority"]["status"], "unknown")
        self.assertEqual(self.proposal["authority"]["mode"], "not_granted")
        self.assertEqual(self.proposal["license_decision"]["acceptance_status"], "pending_exact_owner_decision")

    def test_proposal_binds_candidate_evidence(self) -> None:
        self.assertEqual(self.proposal["candidate_manifest_sha256"], sha256("records/source-gates/m2-dem-candidate-manifest.json"))
        self.assertEqual(self.proposal["metadata_receipt_sha256"], sha256("records/source-gates/m2-dem-metadata-receipt.json"))
        self.assertEqual(self.proposal["source_gate_sha256"], sha256("records/source-gates/m2-dem-source-gate.json"))
        self.assertEqual(self.proposal["arcgis_capability_sha256"], sha256("records/surface-receipts/arcgis-sar-processing-capability.json"))

    def test_review_bundle_and_contract_are_exactly_bound(self) -> None:
        self.assertEqual(
            self.bundle["candidate_identity"],
            f"M2-DEM-AMENDMENT-PROPOSAL-SHA256:{sha256('contracts/milestone-002-dem-amendment-proposal.json')}",
        )
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], sha256("reviews/m2-dem-amendment/review-bundle.json"))
        for artifact in self.bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))

    def test_blank_response_has_zero_human_decisions(self) -> None:
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertEqual(len(self.blank["responses"]), 1)
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.blank["responses"][0]["notes"], "")


if __name__ == "__main__":
    unittest.main()
