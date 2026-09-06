from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reconcile_m2_orbit_recovery_003_terminal_failure as terminal_reconcile  # noqa: E402


class OrbitRecovery003TerminalReconciliationTests(unittest.TestCase):
    def test_finalizes_only_exact_started_attempt(self) -> None:
        intake = {
            "status": "active",
            "assets": [{
                "asset_id": "m2-orb-001",
                "state": "staging",
                "attempts": [
                    {"attempt_id": terminal_reconcile.ORIGINAL_ATTEMPT_ID, "outcome": "failed"},
                    {
                        "attempt_id": terminal_reconcile.ATTEMPT_ID,
                        "completed_at": None,
                        "outcome": "started",
                        "extensions": {
                            "credential_reference": terminal_reconcile.SECRET_REFERENCE,
                            "credential_value_recorded": False,
                        },
                    },
                ],
                "failure": {"code": "retained_old_failure", "recorded_at": "2026-09-04T05:09:38Z"},
                "extensions": {"source_id": terminal_reconcile.EXPECTED_SOURCE_ID},
            }],
        }
        finalized = terminal_reconcile.finalize_failed_intake(intake, r"C:\evidence\failed.json")
        self.assertEqual(intake["assets"][0]["state"], "staging")
        asset = finalized["assets"][0]
        self.assertEqual(asset["state"], "failed")
        self.assertEqual(asset["failure"], {"code": terminal_reconcile.FAILURE_CODE, "recorded_at": terminal_reconcile.COMPLETED_AT})
        self.assertEqual(asset["attempts"][1]["outcome"], "failed")
        self.assertEqual(asset["attempts"][1]["completed_at"], terminal_reconcile.COMPLETED_AT)
        terminal_reconcile.validate_finalized_intake(finalized, r"C:\evidence\failed.json")

    def test_rejects_nonstarted_projection(self) -> None:
        intake = {
            "status": "active",
            "assets": [{
                "asset_id": "m2-orb-001",
                "state": "promoted",
                "attempts": [
                    {"attempt_id": terminal_reconcile.ORIGINAL_ATTEMPT_ID, "outcome": "failed"},
                    {
                        "attempt_id": terminal_reconcile.ATTEMPT_ID,
                        "completed_at": terminal_reconcile.COMPLETED_AT,
                        "outcome": "succeeded",
                        "extensions": {
                            "credential_reference": terminal_reconcile.SECRET_REFERENCE,
                            "credential_value_recorded": False,
                        },
                    },
                ],
                "extensions": {"source_id": terminal_reconcile.EXPECTED_SOURCE_ID},
            }],
        }
        with self.assertRaisesRegex(ValueError, "active_intake_is_not_exact_stale_terminal_projection"):
            terminal_reconcile.finalize_failed_intake(intake, r"C:\evidence\failed.json")


if __name__ == "__main__":
    unittest.main()
