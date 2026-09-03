import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "acquire_m2_dem_tile.py"
SPEC = importlib.util.spec_from_file_location("acquire_m2_dem_tile", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.path.insert(0, str(ROOT / "scripts"))
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class M2DemTransferTests(unittest.TestCase):
    def setUp(self):
        self.intake = load("contracts/m2-dem-intake.json")
        self.asset = self.intake["assets"][0]

    def headers(self):
        return {
            "content-length": str(self.asset["expected"]["size_bytes"]),
            "content-type": "image/tiff",
            "etag": f'"{self.asset["extensions"]["remote_etag_metadata"]}"',
            "last-modified": self.asset["extensions"]["remote_last_modified_metadata"],
            "accept-ranges": "bytes",
        }

    def test_active_intake_has_exact_four_fresh_assets(self):
        self.assertEqual([asset["extensions"]["source_id"] for asset in self.intake["assets"]], MODULE.EXPECTED_SOURCE_IDS)
        self.assertTrue(all(asset["state"] == "authorized" and asset["attempts"] == [] for asset in self.intake["assets"]))
        self.assertEqual(self.intake["extensions"]["status"], "active_authorized_preflight_passed_custody_initialized")

    def test_exact_remote_identity_passes(self):
        checks = MODULE.remote_identity_checks(self.asset, status=200, resolved_url=self.asset["source"]["uri"], headers=self.headers(), body_size=0)
        self.assertTrue(all(checks.values()))

    def test_remote_drift_redirect_and_charge_fail(self):
        headers = self.headers()
        headers["content-length"] = "1"
        headers["x-amz-request-charged"] = "requester"
        checks = MODULE.remote_identity_checks(self.asset, status=200, resolved_url="https://example.invalid/redirect", headers=headers, body_size=1)
        self.assertFalse(checks["exact_url_no_redirect"])
        self.assertFalse(checks["content_length_match"])
        self.assertFalse(checks["head_body_empty"])
        self.assertFalse(checks["no_requester_charge"])

    def test_stream_hashes_exact_bytes_to_exclusive_staging(self):
        payload = b"dem-fixture" * 1000
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "tile.tif.part"
            result = MODULE.stream_sha256_to_exclusive_staging(io.BytesIO(payload), target, expected_size=len(payload), chunk_size=17)
            self.assertEqual(result, {"size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
            self.assertEqual(target.read_bytes(), payload)

    def test_size_mismatch_is_retained(self):
        payload = b"partial-dem"
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "tile.tif.part"
            with self.assertRaisesRegex(MODULE.TransferControlError, "transferred_size_mismatch"):
                MODULE.stream_sha256_to_exclusive_staging(io.BytesIO(payload), target, expected_size=len(payload) + 1)
            self.assertEqual(target.read_bytes(), payload)

    def test_staging_collision_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "tile.tif.part"
            target.write_bytes(b"existing")
            with self.assertRaisesRegex(MODULE.TransferControlError, "staging_collision"):
                MODULE.stream_sha256_to_exclusive_staging(io.BytesIO(b"new"), target, expected_size=3)
            self.assertEqual(target.read_bytes(), b"existing")

    def test_runner_has_no_credential_or_authorization_header(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"Authorization"', text)
        self.assertNotIn("ACCESS_TOKEN", text)
        self.assertIn("NoRedirectHandler", text)
        self.assertIn("credential_or_account_used", text)


if __name__ == "__main__":
    unittest.main()
