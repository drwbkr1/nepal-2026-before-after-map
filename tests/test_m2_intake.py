from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "prepare_m2_intake.py"
SPEC = importlib.util.spec_from_file_location("prepare_m2_intake", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class M2IntakeControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = json.loads((ROOT / "records/acquisition-plan.json").read_text(encoding="utf-8"))
        cls.proposal = json.loads((ROOT / "contracts/milestone-002-proposal.json").read_text(encoding="utf-8"))
        cls.bundle = json.loads((ROOT / "reviews/m2-activation/review-bundle.json").read_text(encoding="utf-8"))
        cls.contract = MODULE.build_contract(
            cls.plan,
            MODULE.sha256_file(ROOT / "contracts/milestone-002-proposal.json"),
            MODULE.sha256_file(ROOT / "reviews/m2-activation/review-bundle.json"),
            "2026-09-02T04:46:03Z",
        )

    def test_exact_packet_passes_static_validation(self) -> None:
        self.assertEqual(MODULE.validate_packet(self.plan, self.proposal, self.bundle, self.contract), [])

    def test_generated_files_are_byte_reproducible(self) -> None:
        dry_run = MODULE.build_dry_run(self.plan, self.proposal, self.bundle, self.contract)
        self.assertEqual(
            (ROOT / "contracts/m2-intake-candidate.json").read_bytes(),
            MODULE.canonical_bytes(self.contract),
        )
        self.assertEqual(
            (ROOT / "records/acquisition/m2-intake-static-dry-run.json").read_bytes(),
            MODULE.canonical_bytes(dry_run),
        )

    def test_packet_contains_only_exact_approved_product_set(self) -> None:
        expected = {record["source_id"] for record in self.plan["records"]}
        actual = {asset["extensions"]["source_id"] for asset in self.contract["assets"]}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 8)

    def test_download_routes_are_secret_free_and_uuid_bound(self) -> None:
        for asset in self.contract["assets"]:
            provider_id = asset["extensions"]["provider_product_id"]
            self.assertEqual(
                asset["source"]["uri"],
                f"{MODULE.DOWNLOAD_BASE}({provider_id})/$value",
            )
            self.assertNotIn("?", asset["source"]["uri"])
            self.assertEqual(asset["source"]["authorization_ref"].split(":", 1)[0], "pending")

    def test_dry_run_cannot_claim_authority_or_mutation(self) -> None:
        dry_run = MODULE.build_dry_run(self.plan, self.proposal, self.bundle, self.contract)
        self.assertFalse(dry_run["authority"]["acquisition_authorized"])
        self.assertFalse(dry_run["authority"]["network_or_authentication_performed"])
        self.assertFalse(dry_run["path_model"]["directories_created"])
        self.assertTrue(all(asset["network_request"] == "not_performed" for asset in dry_run["assets"]))

    def test_mutated_collision_policy_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["collision_policy"] = "overwrite"
        errors = MODULE.validate_packet(self.plan, self.proposal, self.bundle, mutated)
        self.assertTrue(any("collision policy" in error for error in errors))

    def test_product_set_mutation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["assets"].pop()
        errors = MODULE.validate_packet(self.plan, self.proposal, self.bundle, mutated)
        self.assertTrue(any("exactly eight assets" in error for error in errors))

    def test_path_traversal_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["assets"][0]["destination_relative_path"] = "../escape.zip"
        errors = MODULE.validate_packet(self.plan, self.proposal, self.bundle, mutated)
        self.assertTrue(any("unsafe" in error for error in errors))

    def test_authority_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.proposal)
        mutated["status"] = "active"
        mutated["authority"]["mode"] = "inherited"
        errors = MODULE.validate_packet(self.plan, mutated, self.bundle, self.contract)
        self.assertTrue(any("not_granted" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
