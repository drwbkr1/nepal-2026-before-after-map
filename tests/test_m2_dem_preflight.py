import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_m2_dem_preflight.py"
SPEC = importlib.util.spec_from_file_location("run_m2_dem_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class M2DemPreflightTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load("records/source-gates/m2-dem-candidate-manifest.json")
        self.record = self.manifest["records"][0]

    def synthetic_stac(self):
        record = self.record
        return {
            "id": record["item_id"],
            "collection": record["collection"],
            "bbox": record["bbox_wgs84"],
            "properties": {
                "grid:code": record["grid_code"],
                "gsd": record["gsd_m"],
                "proj:code": record["source_crs"],
            },
            "assets": {
                "data": {
                    "proj:shape": record["shape"],
                    "proj:transform": record["transform"],
                    "data_type": record["data_type"],
                    "type": record["media_type"],
                    "href": record["cdse_s3_href"],
                }
            },
        }

    def synthetic_headers(self):
        head = self.record["anonymous_head"]
        return {
            "content-length": str(head["content_length_bytes"]),
            "content-type": "image/tiff",
            "etag": f'"{head["etag"]}"',
            "last-modified": head["last_modified"],
            "accept-ranges": "bytes",
        }

    def test_exact_active_controls_advanced_to_acquisition(self):
        approval = load(MODULE.APPROVAL_REF)
        milestone = load(MODULE.MILESTONE_REF)
        profile = load(MODULE.PROFILE_REF)
        intake = load(MODULE.INTAKE_REF)
        self.assertEqual(approval["authorized_source_ids"], [f"M2-DEM-{index:03d}" for index in range(1, 5)])
        units = {unit["id"]: unit for unit in milestone["units"]}
        self.assertEqual(units["M2-DEM-PREFLIGHT"]["status"], "complete")
        self.assertEqual(units["M2-DEM-ACQUIRE"]["status"], "ready")
        self.assertIn("M2-DEM-ACQUISITION", {item["checkpoint_id"] for item in profile["parallel_checkpoints"]})
        self.assertEqual(
            [asset["extensions"]["source_id"] for asset in intake["assets"]],
            [f"M2-DEM-{index:03d}" for index in range(1, 5)],
        )
        self.assertTrue(all(asset["state"] in {"authorized", "promoted", "failed"} for asset in intake["assets"]))
        self.assertFalse(any(asset["state"] == "staging" for asset in intake["assets"]))

    def test_live_preflight_preserves_no_payload_boundary(self):
        source_gate = load("records/source-gates/m2-dem-live-source-gate.json")
        preflight = load("records/acquisition/dem-preflight.json")
        self.assertEqual(source_gate["decision"]["status"], "ready")
        self.assertEqual(len(source_gate["sources"]), 4)
        self.assertTrue(all(criterion["status"] == "pass" for source in source_gate["sources"] for criterion in source["criteria"]))
        self.assertEqual(preflight["status"], "pass_no_payload_no_external_mutation")
        self.assertEqual(preflight["license_check"]["sha256"], MODULE.LICENSE_SHA256)
        self.assertTrue(all(preflight["license_check"]["checks"].values()))
        self.assertEqual(len(preflight["tile_checks"]), 4)
        self.assertTrue(all(all(tile["stac_checks"].values()) and all(tile["head_checks"].values()) for tile in preflight["tile_checks"]))
        self.assertEqual(preflight["mutations_performed"]["dem_payload_bytes_received"], 0)
        self.assertFalse(preflight["mutations_performed"]["dem_payload_requested"])

    def test_empty_custody_receipt_remains_historical_and_active_bindings_match(self):
        receipt = load("records/acquisition/dem-custody-initialization.json")
        intake = load(MODULE.INTAKE_REF)
        verification = load("contracts/m2-dem-offline-verification.json")
        self.assertEqual(receipt["status"], "created_and_verified_empty")
        self.assertEqual(receipt["verification"]["files_downloaded"], 0)
        self.assertEqual(receipt["verification"]["dem_payload_bytes_present"], 0)
        self.assertEqual(intake["extensions"]["preflight_sha256"], MODULE.sha256_file(MODULE.PREFLIGHT_REF))
        self.assertEqual(verification["inputs"]["intake_contract_sha256"], MODULE.sha256_file(MODULE.INTAKE_REF))

    def test_evidence_0032_preserves_historical_preflight_state(self):
        ledger = [json.loads(line) for line in (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        evidence = next(item for item in ledger if item.get("record_id") == "EVID-0032")
        expected_hashes = {
            "source_gate_sha256": "5baac05a9e1ede4fa3ada02e4e2cd3bac9c3032164d280ef6886e0d519ae603e",
            "preflight_sha256": "18ca15363d92f6f04d672ddb3e97fef33524c94bcb54915d83c82dae77af38f1",
            "custody_initialization_sha256": "31d1b814d8da753dd2335f3110a49107df3f7a6c75875154a0fff0338b7e80a0",
            "active_intake_sha256": "2ae511c70303f15de590daf3eef4aac1e9dab1b7e0f85544c049ef69a60caa36",
            "active_verification_sha256": "6d7ee4aa05a6ead58d56ebc11d60f4aeb71489e02201f8b0462247b63f3cd27a",
            "completion_script_sha256": "9f83e8bf33373e665fdf50cce3e37a2e4bdf4d839338df07a0e31d6aef1c1767",
            "preflight_script_sha256": "c837997f9ec37daff6644089dae234a7bfdecf11401fb7f5cb9745993c91cfc2",
        }
        for hash_key, expected in expected_hashes.items():
            self.assertEqual(evidence[hash_key], expected)
        self.assertFalse(evidence["assertions"]["dem_payload_bytes_requested"])
        self.assertEqual(evidence["assertions"]["dem_payload_bytes_present"], 0)

    def test_exact_stac_metadata_passes(self):
        self.assertTrue(all(MODULE.validate_stac(self.record, self.synthetic_stac()).values()))

    def test_stac_identity_or_grid_drift_fails(self):
        item = self.synthetic_stac()
        item["id"] = "different"
        item["assets"]["data"]["proj:shape"] = [1, 1]
        checks = MODULE.validate_stac(self.record, item)
        self.assertFalse(checks["item_id_match"])
        self.assertFalse(checks["shape_match"])

    def test_exact_anonymous_head_passes_without_body(self):
        checks = MODULE.validate_head(
            self.record,
            self.synthetic_headers(),
            200,
            self.record["anonymous_https_url"],
            b"",
        )
        self.assertTrue(all(checks.values()))

    def test_redirect_charge_or_remote_drift_fails(self):
        headers = self.synthetic_headers()
        headers["content-length"] = "1"
        headers["x-amz-request-charged"] = "requester"
        checks = MODULE.validate_head(self.record, headers, 200, "https://example.invalid/redirect", b"x")
        self.assertFalse(checks["exact_url_no_redirect"])
        self.assertFalse(checks["zero_response_body_bytes"])
        self.assertFalse(checks["content_length_match"])
        self.assertFalse(checks["anonymous_no_requester_charge"])

    def test_redirect_handler_never_follows(self):
        handler = MODULE.RefuseRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://example.invalid"))


if __name__ == "__main__":
    unittest.main()
