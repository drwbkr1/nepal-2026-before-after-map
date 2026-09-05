from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_m2_acquisition_progress import (  # noqa: E402
    INITIAL_ACTIVE_INTAKE_SHA256,
    sha256_path,
    validate_progress,
)


BASELINE = json.loads((ROOT / "records/acquisition/active-intake-initial-snapshot.json").read_text(encoding="utf-8"))
PLAN = json.loads((ROOT / "records/acquisition-plan.json").read_text(encoding="utf-8"))


def started_asset(current: dict, *, state: str) -> tuple[dict, str]:
    asset = current["assets"][0]
    attempt_id = f"{asset['asset_id']}-20260903T200000Z-1234abcd"
    asset["state"] = state
    asset["attempts"] = [
        {
            "attempt_id": attempt_id,
            "started_at": "2026-09-03T20:00:00Z",
            "completed_at": None if state == "staging" else "2026-09-03T20:05:00Z",
            "outcome": {"staging": "started", "failed": "failed", "promoted": "succeeded"}[state],
            "extensions": {
                "source_id": asset["extensions"]["source_id"],
                "catalog_response_sha256": "c" * 64,
                "external_started_event": str(
                    Path("C:/controlled/attempt-events") / asset["asset_id"] / f"{attempt_id}-started.json"
                ),
                "credential_reference": "CDSE_ACCESS_TOKEN",
                "credential_value_recorded": False,
                "resume": False,
            },
        }
    ]
    return asset, attempt_id


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


class M2AcquisitionProgressTests(unittest.TestCase):
    def test_initial_snapshot_has_the_activation_time_identity(self) -> None:
        self.assertEqual(
            sha256_path(ROOT / "records/acquisition/active-intake-initial-snapshot.json"),
            INITIAL_ACTIVE_INTAKE_SHA256,
        )

    def test_current_authorized_state_passes_without_external_access(self) -> None:
        result = validate_progress(copy.deepcopy(BASELINE), BASELINE, PLAN, root=ROOT)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["state_counts"], {"authorized": 8})
        self.assertFalse(result["external_state_verified"])

    def test_current_recovery_002_reconciliation_state_passes(self) -> None:
        current = json.loads((ROOT / "contracts/m2-intake.json").read_text(encoding="utf-8"))
        result = validate_progress(current, BASELINE, PLAN, root=ROOT)
        self.assertEqual(result["status"], "pass", result["errors"])
        self.assertEqual(result["state_counts"], {"authorized": 4, "promoted": 4})
        self.assertEqual(result["attempt_count"], 5)

    def test_immutable_product_identity_drift_fails(self) -> None:
        current = copy.deepcopy(BASELINE)
        current["assets"][0]["extensions"]["provider_product_id"] = "different"
        result = validate_progress(current, BASELINE, PLAN, root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("immutable extension provider_product_id differs" in item for item in result["errors"]))

    def test_valid_staging_state_is_representable(self) -> None:
        current = copy.deepcopy(BASELINE)
        started_asset(current, state="staging")
        result = validate_progress(current, BASELINE, PLAN, root=ROOT)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["state_counts"], {"authorized": 7, "staging": 1})

    def test_windows_started_event_reference_is_portable(self) -> None:
        current = copy.deepcopy(BASELINE)
        asset, attempt_id = started_asset(current, state="staging")
        asset["attempts"][0]["extensions"]["external_started_event"] = (
            rf"C:\controlled\attempt-events\{asset['asset_id']}\{attempt_id}-started.json"
        )
        result = validate_progress(current, BASELINE, PLAN, root=ROOT)
        self.assertEqual(result["status"], "pass", result["errors"])

    def test_valid_failed_state_preserves_terminal_receipt(self) -> None:
        current = copy.deepcopy(BASELINE)
        asset, attempt_id = started_asset(current, state="failed")
        asset["failure"] = {"code": "provider_transport_failure", "recorded_at": "2026-09-03T20:05:00Z"}
        receipt = {
            "event": "transfer_failed",
            "attempt_id": attempt_id,
            "source_id": asset["extensions"]["source_id"],
            "completed_at": "2026-09-03T20:05:00Z",
            "failure_code": "provider_transport_failure",
            "partial_bytes_preserved": 0,
            "credential_value_recorded": False,
            "retry_automatically_authorized": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            test_root = Path(temporary)
            write_json(test_root / "records/acquisition/attempts" / f"{attempt_id}.json", receipt)
            result = validate_progress(current, BASELINE, PLAN, root=test_root)
        self.assertEqual(result["status"], "pass")

    def test_valid_promoted_state_binds_receipt_and_byte_identity(self) -> None:
        current = copy.deepcopy(BASELINE)
        asset, attempt_id = started_asset(current, state="promoted")
        local_sha256 = "a" * 64
        size = asset["extensions"]["catalog_content_length_bytes"]
        asset["observed"] = {
            "staged_sha256": local_sha256,
            "staged_size_bytes": size,
            "promoted_sha256": local_sha256,
            "promoted_size_bytes": size,
        }
        providers = {item["Algorithm"]: item["Value"] for item in asset["extensions"]["provider_checksums"]}
        receipt_ref = f"records/acquisition/attempts/{attempt_id}.json"
        receipt = {
            "event": "transfer_succeeded",
            "attempt_id": attempt_id,
            "source_id": asset["extensions"]["source_id"],
            "completed_at": "2026-09-03T20:05:00Z",
            "local_sha256": local_sha256,
            "local_size_bytes": size,
            "provider_md5": providers["MD5"],
            "provider_md5_match": True,
            "provider_blake3_metadata": providers["BLAKE3"],
            "provider_blake3_locally_verified": False,
            "credential_value_recorded": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            test_root = Path(temporary)
            receipt_path = test_root / Path(*Path(receipt_ref).parts)
            write_json(receipt_path, receipt)
            asset["extensions"].update(
                {
                    "successful_attempt_receipt": receipt_ref,
                    "successful_attempt_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    "provider_md5_verified": True,
                    "provider_blake3_locally_verified": False,
                }
            )
            result = validate_progress(current, BASELINE, PLAN, root=test_root)
        self.assertEqual(result["status"], "pass")

    def test_missing_terminal_receipt_fails(self) -> None:
        current = copy.deepcopy(BASELINE)
        asset, _ = started_asset(current, state="failed")
        asset["failure"] = {"code": "provider_transport_failure", "recorded_at": "2026-09-03T20:05:00Z"}
        with tempfile.TemporaryDirectory() as temporary:
            result = validate_progress(current, BASELINE, PLAN, root=Path(temporary))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("terminal receipt is missing" in item for item in result["errors"]))

    def test_secret_bearing_key_is_rejected(self) -> None:
        current = copy.deepcopy(BASELINE)
        current["cdse_access_token"] = "must-never-be-recorded"
        result = validate_progress(current, BASELINE, PLAN, root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("forbidden secret-bearing key" in item for item in result["errors"]))

    def test_empty_initialized_external_roots_match_authorized_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            test_root = parent / "repository"
            test_root.mkdir()
            data_root = parent / "repository-data"
            (data_root / "custody").mkdir(parents=True)
            (data_root / ".intake-staging" / BASELINE["intake_id"]).mkdir(parents=True)
            result = validate_progress(
                copy.deepcopy(BASELINE),
                BASELINE,
                PLAN,
                root=test_root,
                verify_external=True,
            )
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["external_state_verified"])


if __name__ == "__main__":
    unittest.main()
