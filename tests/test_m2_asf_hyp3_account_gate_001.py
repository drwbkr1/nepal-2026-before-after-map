"""Bind the limited account gate without promoting job or product rights."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_GATE = "records/readiness/m2-asf-hyp3-rtc-map-route-001-implementation-publication-gate.json"
SUCCESSOR_GATE = "records/readiness/m2-asf-hyp3-rtc-account-handoff-implementation-gate-002.json"
SOURCE_GATE = "records/source-gates/m2-asf-hyp3-rtc-live-source-gate-001.json"
APPROVAL = "records/source-gates/m2-asf-hyp3-rtc-map-route-001-approval.json"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class HyP3AccountGateTests(unittest.TestCase):
    def test_exact_public_implementation_and_limited_source_gate(self) -> None:
        gate = load(IMPLEMENTATION_GATE)
        source = load(SOURCE_GATE)
        self.assertEqual(gate["status"], "pass_account_probe_implementation_public_ci_only")
        self.assertEqual(gate["bindings"]["approval_sha256"], sha(APPROVAL))
        self.assertEqual(gate["public_ci"]["head_sha"], gate["bindings"]["implementation_commit_sha"])
        self.assertEqual(gate["public_ci"]["conclusion"], "success")
        for digest in gate["bindings"]["implementation_file_sha256"].values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertFalse(gate["assertions"]["account_or_job_request_performed"])
        self.assertFalse(gate["assertions"]["full_rtc_job_or_product_implementation_complete"])
        self.assertEqual(source["decision"]["status"], "ready")
        self.assertEqual(source["decision"]["approved_actions"], ["read_own_basic_account_capacity"])
        self.assertEqual(source["bindings"]["approval_sha256"], sha(APPROVAL))
        self.assertFalse(source["terms"]["job_and_product_rights_released"])
        self.assertTrue(source["terms"]["exact_accepted_agreement_document_not_retrieved"])

    def test_successor_gate_binds_current_credential_handoff_only_after_publication(self) -> None:
        if not (ROOT / SUCCESSOR_GATE).exists():
            self.skipTest("successor implementation gate not yet published")
        gate = load(SUCCESSOR_GATE)
        self.assertEqual(gate["status"], "pass_account_probe_implementation_public_ci_only")
        self.assertEqual(gate["bindings"]["approval_sha256"], sha(APPROVAL))
        self.assertEqual(gate["public_ci"]["conclusion"], "success")
        for ref, digest in gate["bindings"]["implementation_file_sha256"].items():
            self.assertEqual(sha(ref), digest, ref)
        self.assertFalse(gate["assertions"]["account_or_job_request_performed"])


if __name__ == "__main__":
    unittest.main()
