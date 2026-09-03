from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import candidate_controls, derive_checkpoint  # noqa: E402


class M2CheckpointReconciliationTests(unittest.TestCase):
    def test_all_authorized_waits_for_secret_safe_reference(self) -> None:
        result = derive_checkpoint({"authorized": 8})
        self.assertEqual(result["checkpoint_id"], "M2-AUTHENTICATION-REFERENCE")

    def test_partial_terminal_progress_continues_acquisition(self) -> None:
        result = derive_checkpoint({"authorized": 7, "promoted": 1})
        self.assertEqual(result["checkpoint_id"], "M2-ACQUISITION-IN-PROGRESS")

    def test_live_staging_is_acquisition_in_progress(self) -> None:
        result = derive_checkpoint({"authorized": 7, "staging": 1})
        self.assertEqual(result["checkpoint_id"], "M2-ACQUISITION-IN-PROGRESS")

    def test_any_failed_attempt_requires_review(self) -> None:
        result = derive_checkpoint({"authorized": 7, "failed": 1})
        self.assertEqual(result["checkpoint_id"], "M2-ACQUISITION-REVIEW")

    def test_all_promoted_advance_to_container_verification(self) -> None:
        result = derive_checkpoint({"promoted": 8})
        self.assertEqual(result["checkpoint_id"], "M2-CONTAINER-VERIFICATION")

    def test_incomplete_or_unsupported_counts_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly eight"):
            derive_checkpoint({"authorized": 7})
        with self.assertRaisesRegex(ValueError, "cannot determine"):
            derive_checkpoint({"unsupported": 8})

    def test_candidate_controls_do_not_mutate_sources(self) -> None:
        profile = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))
        goal = json.loads((ROOT / "records/long-term-goal.json").read_text(encoding="utf-8"))
        original_profile = copy.deepcopy(profile)
        original_goal = copy.deepcopy(goal)
        checkpoint = derive_checkpoint({"authorized": 7, "promoted": 1})
        candidate_profile, candidate_goal = candidate_controls(profile, goal, checkpoint)
        self.assertEqual(profile, original_profile)
        self.assertEqual(goal, original_goal)
        self.assertEqual(candidate_profile["current_checkpoint"]["checkpoint_id"], "M2-ACQUISITION-IN-PROGRESS")
        self.assertEqual(candidate_goal["current_checkpoint"], "M2-ACQUISITION-IN-PROGRESS")

    def test_current_repository_checkpoint_is_reconciled_read_only(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/derive_m2_acquisition_checkpoint.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertTrue(payload["current_controls_match"])
        self.assertFalse(payload["credential_values_read"])
        self.assertFalse(payload["tracked_files_mutated"])

    def test_candidate_output_is_scratch_only_and_no_replace(self) -> None:
        scratch = ROOT / "scratch"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            output = Path(temporary) / "checkpoint-candidate"
            command = [
                sys.executable,
                str(ROOT / "scripts/derive_m2_acquisition_checkpoint.py"),
                "--candidate-output-root",
                str(output),
            ]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 12)
            self.assertEqual(json.loads(second.stdout)["code"], "candidate_output_collision")


if __name__ == "__main__":
    unittest.main()
