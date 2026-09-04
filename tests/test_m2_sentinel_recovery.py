from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from m2_sentinel_recovery_core import (  # noqa: E402
    EXPECTED_ASSET_ID,
    EXPECTED_DESTINATION,
    EXPECTED_FAILED_ATTEMPT_ID,
    EXPECTED_PARTIAL_BYTES,
    EXPECTED_PARTIAL_SHA256,
    EXPECTED_RECOVERY_STAGING,
    RecoveryControlError,
    require_exact_recovery_contract,
    require_fresh_authorized_attempt,
    require_original_failure,
    set_attempt_terminal,
)


def recovery_contract() -> dict:
    return {
        "intake_id": "nepal-m2-sentinel-recovery-001",
        "collision_policy": "fail",
        "promotion_mode": "atomic-no-replace",
        "secret_policy": "references-only",
        "custody_root": "nepal-2026-before-after-map-data/custody",
        "staging_root": "nepal-2026-before-after-map-data/.intake-staging/nepal-m2-sentinel-recovery-001",
        "assets": [{
            "asset_id": EXPECTED_ASSET_ID,
            "destination_relative_path": EXPECTED_DESTINATION,
            "staging_relative_path": EXPECTED_RECOVERY_STAGING,
            "state": "authorized",
            "attempts": [],
            "failure": None,
            "extensions": {"source_id": "M1-SRC-004"},
        }],
        "extensions": {
            "restart_offset_bytes": 0,
            "resume_partial": False,
            "delete_or_modify_failed_partial": False,
            "reuse_failed_staging_path": False,
            "maximum_real_transfer_attempts": 1,
        },
    }


def original_intake() -> dict:
    return {
        "assets": [{
            "asset_id": "m1-src-004",
            "state": "failed",
            "attempts": [{"attempt_id": EXPECTED_FAILED_ATTEMPT_ID, "outcome": "failed"}],
            "failure": {"code": "transferred_size_mismatch"},
            "extensions": {"source_id": "M1-SRC-004"},
        }]
    }


def failed_receipt() -> dict:
    return {
        "event": "transfer_failed",
        "attempt_id": EXPECTED_FAILED_ATTEMPT_ID,
        "failure_code": "transferred_size_mismatch",
        "partial_bytes_preserved": EXPECTED_PARTIAL_BYTES,
        "retry_automatically_authorized": False,
    }


class SentinelRecoveryCoreTests(unittest.TestCase):
    def test_exact_contract_accepts_distinct_byte_zero_recovery(self) -> None:
        asset = require_exact_recovery_contract(recovery_contract())
        require_fresh_authorized_attempt(asset)
        self.assertEqual(asset["asset_id"], EXPECTED_ASSET_ID)

    def test_original_terminal_failure_and_partial_are_required(self) -> None:
        asset = require_original_failure(
            original_intake(),
            failed_receipt(),
            partial_size=EXPECTED_PARTIAL_BYTES,
            partial_sha256=EXPECTED_PARTIAL_SHA256,
        )
        self.assertEqual(asset["state"], "failed")

    def test_recovery_must_not_resume_partial(self) -> None:
        contract = recovery_contract()
        contract["extensions"]["resume_partial"] = True
        with self.assertRaisesRegex(RecoveryControlError, "recovery_method_boundary_drift"):
            require_exact_recovery_contract(contract)

    def test_recovery_must_use_distinct_staging_identity(self) -> None:
        contract = recovery_contract()
        contract["assets"][0]["staging_relative_path"] = EXPECTED_DESTINATION + ".part"
        with self.assertRaisesRegex(RecoveryControlError, "recovery_asset_identity_or_path_drift"):
            require_exact_recovery_contract(contract)

    def test_partial_hash_drift_blocks(self) -> None:
        with self.assertRaisesRegex(RecoveryControlError, "retained_partial_identity_drift"):
            require_original_failure(
                original_intake(),
                failed_receipt(),
                partial_size=EXPECTED_PARTIAL_BYTES,
                partial_sha256="0" * 64,
            )

    def test_original_failure_remains_terminal(self) -> None:
        intake = original_intake()
        intake["assets"][0]["state"] = "authorized"
        with self.assertRaisesRegex(RecoveryControlError, "original_failed_asset_history_drift"):
            require_original_failure(
                intake,
                failed_receipt(),
                partial_size=EXPECTED_PARTIAL_BYTES,
                partial_sha256=EXPECTED_PARTIAL_SHA256,
            )

    def test_only_one_fresh_recovery_attempt_is_allowed(self) -> None:
        asset = recovery_contract()["assets"][0]
        asset["attempts"].append({"attempt_id": "already-attempted"})
        with self.assertRaisesRegex(RecoveryControlError, "recovery_asset_not_fresh_authorized"):
            require_fresh_authorized_attempt(asset)

    def test_success_updates_only_recovery_asset(self) -> None:
        contract = recovery_contract()
        original = original_intake()
        contract["assets"][0]["state"] = "staging"
        contract["assets"][0]["attempts"] = [{
            "attempt_id": "m1-src-004-recovery-001-20260904t200000z-abcd1234",
            "started_at": "2026-09-04T20:00:00Z",
            "completed_at": None,
            "outcome": "started",
        }]
        snapshot = deepcopy(original)
        asset = set_attempt_terminal(
            contract,
            "m1-src-004-recovery-001-20260904t200000z-abcd1234",
            "2026-09-04T20:05:00Z",
            outcome="succeeded",
            failure_code=None,
        )
        self.assertEqual(asset["state"], "promoted")
        self.assertEqual(original, snapshot)

    def test_missing_token_stops_before_control_or_network_access(self) -> None:
        env = os.environ.copy()
        env.pop("CDSE_ACCESS_TOKEN", None)
        run = subprocess.run(
            [sys.executable, str(SCRIPTS / "acquire_m2_sentinel_recovery.py"), "--source-id", "M1-SRC-004"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(run.returncode, 12, run.stdout + run.stderr)
        payload = json.loads(run.stdout)
        self.assertEqual(payload["code"], "secret_safe_access_reference_missing")
        self.assertFalse(payload["mutations_performed"])

    def test_unapproved_source_stops_before_token_lookup(self) -> None:
        env = os.environ.copy()
        env["CDSE_ACCESS_TOKEN"] = "test-only-nonsecret-literal"
        run = subprocess.run(
            [sys.executable, str(SCRIPTS / "acquire_m2_sentinel_recovery.py"), "--source-id", "M1-SRC-005"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(run.returncode, 12, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["code"], "recovery_source_outside_exact_approval")


if __name__ == "__main__":
    unittest.main()
