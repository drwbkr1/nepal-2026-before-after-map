from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class M2ActiveVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.active_path = ROOT / "contracts" / "m2-offline-verification.json"
        cls.active = json.loads(cls.active_path.read_text(encoding="utf-8"))
        cls.candidate_path = ROOT / "contracts" / "m2-offline-verification-candidate.json"
        cls.candidate = json.loads(cls.candidate_path.read_text(encoding="utf-8"))

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_active_contract_inherits_exact_m2_authority(self) -> None:
        self.assertEqual(self.active["status"], "active_authorized_offline_verification")
        self.assertEqual(self.active["authority"]["mode"], "inherited")
        self.assertEqual(
            self.active["authority"]["authority_ref"],
            "records/source-gates/m2-activation-approval.json",
        )
        self.assertTrue(self.active["authority"]["offline_verification_authorized"])
        self.assertFalse(self.active["authority"]["this_contract_creates_authority"])

    def test_active_contract_preserves_exact_candidate_assets(self) -> None:
        self.assertEqual(self.active["assets"], self.candidate["assets"])
        self.assertEqual(len(self.active["assets"]), 8)
        self.assertEqual(
            self.active["inputs"]["candidate_contract_sha256"],
            self.digest(self.candidate_path),
        )

    def test_active_contract_binds_current_gate_and_custody_evidence(self) -> None:
        bindings = self.active["inputs"]
        for key, relative in (
            ("activation_approval_sha256", "records/source-gates/m2-activation-approval.json"),
            ("source_gate_sha256", "records/source-gates/m2-live-source-gate.json"),
            ("custody_initialization_sha256", "records/acquisition/custody-initialization.json"),
        ):
            self.assertEqual(bindings[key], self.digest(ROOT / relative))

    def test_active_verification_is_offline_read_only_and_non_scientific(self) -> None:
        boundary = self.active["execution_boundary"]
        self.assertEqual(boundary["network_requests"], "prohibited")
        self.assertEqual(boundary["archive_extraction"], "prohibited")
        self.assertEqual(boundary["source_archive_mutation"], "prohibited")
        self.assertFalse(self.active["authority"]["pixel_use_authorized_by_this_contract"])
        self.assertEqual(self.active["activation_boundary"]["product_bytes_read"], 0)

    def test_wrapper_stops_before_custody_read_when_asset_is_not_promoted(self) -> None:
        intake = ROOT / "contracts" / "m2-intake.json"
        before = self.digest(intake)
        output_root = ROOT / "records" / "acquisition" / "container-verification"
        before_outputs = sorted(path.name for path in output_root.glob("*.json")) if output_root.exists() else []
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "verify_m2_product_container.py"),
                "--source-id",
                "M1-SRC-001",
                "--scanned-at-utc",
                "2026-09-03T18:00:00Z",
            ],
            cwd=ROOT,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 12)
        self.assertEqual(json.loads(result.stdout)["code"], "asset_not_promoted")
        self.assertEqual(self.digest(intake), before)
        after_outputs = sorted(path.name for path in output_root.glob("*.json")) if output_root.exists() else []
        self.assertEqual(after_outputs, before_outputs)


if __name__ == "__main__":
    unittest.main()
