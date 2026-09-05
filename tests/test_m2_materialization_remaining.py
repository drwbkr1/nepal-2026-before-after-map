from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("m2_materialization_remaining_core", ROOT / "scripts/m2_materialization_remaining_core.py")
assert SPEC and SPEC.loader
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)
sys.path.insert(0, str(ROOT / "scripts"))
RUN_SPEC = importlib.util.spec_from_file_location("run_m2_materialization_remaining", ROOT / "scripts/run_m2_materialization_remaining.py")
assert RUN_SPEC and RUN_SPEC.loader
RUNNER = importlib.util.module_from_spec(RUN_SPEC)
RUN_SPEC.loader.exec_module(RUNNER)


class MaterializationRemainingTests(unittest.TestCase):
    def test_exact_order_and_attempt_ids_are_frozen(self):
        self.assertEqual(CORE.SOURCE_ORDER, ["M1-SRC-004", "M1-SRC-005", "M1-SRC-006", "M1-SRC-010", "M1-SRC-008"])
        self.assertEqual([CORE.ATTEMPT_IDS[item] for item in CORE.SOURCE_ORDER], [
            "m1-src-004-materialization-001",
            "m1-src-005-materialization-001",
            "m1-src-006-materialization-001",
            "m1-src-010-materialization-001",
            "m1-src-008-materialization-001",
        ])

    def test_approval_is_exact_and_non_scientific(self):
        approval = json.loads((ROOT / CORE.APPROVAL_REF).read_text(encoding="utf-8"))
        self.assertEqual(approval["review_bundle_manifest_sha256"], CORE.BUNDLE_SHA256)
        self.assertEqual(approval["proposal_sha256"], CORE.PROPOSAL_SHA256)
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertFalse(approval["human_decisions_fabricated"])
        self.assertTrue(any("scientific publication" in item for item in approval["does_not_authorize"]))

    def test_activation_releases_no_real_work_before_publication(self):
        activation = json.loads((ROOT / CORE.ACTIVATION_REF).read_text(encoding="utf-8"))
        released = activation["released_now"]
        self.assertTrue(released["stage_1_control_implementation"])
        self.assertFalse(released["real_materialization_before_public_ci_and_final_preflight"])
        self.assertFalse(released["real_header_inspection"])
        self.assertFalse(released["optical_pixel_readiness"])
        self.assertFalse(released["radar_measurement_pixels"])

    def test_static_authority_accepts_exact_unpublished_activation(self):
        proposal, approval = CORE.validate_static_authority(require_publication_gate=False)
        self.assertEqual(proposal["stage_1_exact_materialization"]["source_order"], CORE.SOURCE_ORDER)
        self.assertEqual(approval["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})

    def test_preflight_validator_rejects_reordered_sources(self):
        with mock.patch.object(CORE, "repository_sha", return_value="same"):
            record = {
                "status": "pass_exact_five_ready_no_mutation_publication_verified",
                "source_order": list(reversed(CORE.SOURCE_ORDER)),
                "planned_sources": [{"planned_attempt_id": CORE.ATTEMPT_IDS[item]} for item in reversed(CORE.SOURCE_ORDER)],
                "assertions": {"planned_paths_absent": True, "external_files_mutated": False, "measurement_pixels_read": False},
                "bindings": {"approval_sha256": "same", "publication_gate_sha256": "same"},
            }
            with self.assertRaises(CORE.BoundaryError):
                CORE.validate_preflight(record)

    def test_preflight_validator_rejects_any_mutation_claim(self):
        with mock.patch.object(CORE, "repository_sha", return_value="same"):
            record = {
                "status": "pass_exact_five_ready_no_mutation_publication_verified",
                "source_order": CORE.SOURCE_ORDER,
                "planned_sources": [{"planned_attempt_id": CORE.ATTEMPT_IDS[item]} for item in CORE.SOURCE_ORDER],
                "assertions": {"planned_paths_absent": True, "external_files_mutated": True, "measurement_pixels_read": False},
                "bindings": {"approval_sha256": "same", "publication_gate_sha256": "same"},
            }
            with self.assertRaises(CORE.BoundaryError):
                CORE.validate_preflight(record)

    def test_runner_requires_explicit_execute_switch(self):
        text = (ROOT / "scripts/run_m2_materialization_remaining.py").read_text(encoding="utf-8")
        self.assertIn('if not args.execute:', text)
        self.assertIn('subprocess.run(command', text)
        self.assertIn('return completed.returncode or 20', text)

    def test_runner_stops_on_first_failed_source(self):
        preflight = {
            "planned_sources": [{"archive_sha256": item} for item in range(5)],
        }
        failed = mock.Mock(returncode=20)
        with (
            mock.patch.object(sys, "argv", ["runner", "--execute"]),
            mock.patch.object(RUNNER, "validate_static_authority"),
            mock.patch.object(RUNNER, "load", return_value=preflight),
            mock.patch.object(RUNNER, "validate_preflight"),
            mock.patch.object(RUNNER, "observe_preflight", return_value=preflight),
            mock.patch.object(RUNNER, "ROOT", Path("Z:/absent-repository")),
            mock.patch.object(RUNNER, "attempt_root", return_value=Path("Z:/absent")),
            mock.patch.object(RUNNER.subprocess, "run", return_value=failed) as invoked,
        ):
            self.assertEqual(RUNNER.main(), 20)
        self.assertEqual(invoked.call_count, 1)
        self.assertIn("M1-SRC-004", invoked.call_args.args[0])

    def test_runner_invokes_each_exact_source_once_in_order(self):
        preflight = {"planned_sources": [{"archive_sha256": item} for item in range(5)]}
        seen_receipts = []

        def fake_load(ref):
            if ref == CORE.FINAL_PREFLIGHT_REF:
                return preflight
            source_id = next(source for source in CORE.SOURCE_ORDER if source.casefold() in ref)
            seen_receipts.append(source_id)
            return {"status": "pass_materialization_only", "source_id": source_id, "attempt_id": CORE.ATTEMPT_IDS[source_id]}

        completed = mock.Mock(returncode=0)
        with (
            mock.patch.object(sys, "argv", ["runner", "--execute"]),
            mock.patch.object(RUNNER, "validate_static_authority"),
            mock.patch.object(RUNNER, "load", side_effect=fake_load),
            mock.patch.object(RUNNER, "validate_preflight"),
            mock.patch.object(RUNNER, "observe_preflight", return_value=preflight),
            mock.patch.object(RUNNER, "ROOT", Path("Z:/absent-repository")),
            mock.patch.object(RUNNER, "attempt_root", return_value=Path("Z:/absent")),
            mock.patch.object(RUNNER.subprocess, "run", return_value=completed) as invoked,
        ):
            self.assertEqual(RUNNER.main(), 0)
        self.assertEqual(seen_receipts, CORE.SOURCE_ORDER)
        self.assertEqual(invoked.call_count, 5)
        self.assertEqual([call.args[0][call.args[0].index("--source-id") + 1] for call in invoked.call_args_list], CORE.SOURCE_ORDER)

    def test_reconciler_rehashes_every_manifest_member(self):
        text = (ROOT / "scripts/reconcile_m2_materialization_remaining.py").read_text(encoding="utf-8")
        self.assertIn('for item in manifest.get("files", [])', text)
        self.assertIn('sha256_file(path) != item["sha256"]', text)
        self.assertIn('"measurement_pixels_decoded": False', text)

    def test_attempt_path_is_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(CORE, "DATA_ROOT", Path(temp)):
                path = CORE.attempt_root("M1-SRC-004")
                self.assertFalse(str(path).startswith(str(ROOT)))
                self.assertEqual(path.name, "m1-src-004-materialization-001")


if __name__ == "__main__":
    unittest.main()
