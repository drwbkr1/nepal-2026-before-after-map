"""Exact-source and one-use limits for the approved optical pair pilot."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_optical_pair_pilot_001_core import (  # noqa: E402
    PilotControlError,
    classify_terminal_exception,
    exact_catalog_url,
    exact_download_url,
    load_contract,
    may_make_second_request,
    require_execution_release,
    source_for_id,
    validate_catalog_product,
    validate_catalog_footprint,
    validate_contract,
)


class OpticalPairPilotCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()

    def test_exact_source_order_and_urls(self) -> None:
        self.assertEqual([item["source_id"] for item in self.contract["sources_in_order"]], ["M2-OPT-001", "M2-OPT-002"])
        for source in self.contract["sources_in_order"]:
            self.assertEqual(source_for_id(self.contract, source["source_id"]), source)
            self.assertEqual(exact_catalog_url(source).split("(")[1].split(")")[0], source["provider_product_id"])
            self.assertEqual(exact_download_url(source).split("(")[1].split(")")[0], source["provider_product_id"])
        with self.assertRaises(PilotControlError):
            source_for_id(self.contract, "M1-SRC-010")

    def test_authority_and_frozen_rules_fail_closed(self) -> None:
        altered = copy.deepcopy(self.contract)
        altered["frozen_scientific_bindings"]["minimum_usable_aoi_fraction"] = 0.5
        with self.assertRaisesRegex(PilotControlError, "pilot_frozen_predicate_drift"):
            validate_contract(altered)
        altered = copy.deepcopy(self.contract)
        altered["execution_boundary"]["maximum_requests_per_product"] = 3
        with self.assertRaisesRegex(PilotControlError, "pilot_execution_boundary_drift"):
            validate_contract(altered)
        altered = copy.deepcopy(self.contract)
        altered["sources_in_order"].reverse()
        with self.assertRaisesRegex(PilotControlError, "pilot_source_identity_drift"):
            validate_contract(altered)

    def test_real_execution_remains_blocked_before_public_gate_and_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with patch("m2_optical_pair_pilot_001_core.load_contract", return_value=self.contract), patch("m2_optical_pair_pilot_001_core.validate_implementation_manifest", return_value="0" * 64):
                with self.assertRaisesRegex(PilotControlError, "pilot_execution_gate_or_preflight_missing"):
                    require_execution_release(root=Path(folder))

    def test_catalog_match_and_drift(self) -> None:
        for source in self.contract["sources_in_order"]:
            product = {
                "Id": source["provider_product_id"],
                "Name": source["exact_product_name"],
                "ContentLength": source["content_length_bytes"],
                "Online": True,
                "Checksum": [
                    {"Algorithm": "MD5", "Value": source["provider_md5"]},
                    {"Algorithm": "BLAKE3", "Value": source["provider_blake3"]},
                ],
            }
            validate_catalog_product(source, product)
            product["Checksum"][1]["Value"] = "f" * 64
            with self.assertRaises(PilotControlError):
                validate_catalog_product(source, product)

    def test_captured_footprints_cover_target_aois_only(self) -> None:
        captured = json.loads((ROOT / "records/observations/m2-map-route-feasibility-001-optical-fallback-catalog.json").read_text(encoding="utf-8"))
        for source in self.contract["sources_in_order"]:
            row = next(item for item in captured["rows"] if item["provider_product_id"] == source["provider_product_id"])
            validate_catalog_footprint(source, {"GeoFootprint": row["footprint"]})
            with self.assertRaisesRegex(PilotControlError, "pilot_catalog_footprint_drift"):
                validate_catalog_footprint(source, {"GeoFootprint": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}})

    def test_second_request_only_after_transport_interruption(self) -> None:
        self.assertTrue(may_make_second_request(None, 0))
        self.assertTrue(may_make_second_request("transport_interrupted", 1))
        for state in ("checksum_mismatch", "rights_drift", "container_failure", "succeeded", None):
            self.assertFalse(may_make_second_request(state, 1))
        self.assertFalse(may_make_second_request("transport_interrupted", 2))

    def test_exception_text_is_never_persisted(self) -> None:
        secret = "fake-secret-never-log"
        self.assertEqual(classify_terminal_exception(TimeoutError(secret)), "transport_interrupted")
        self.assertEqual(classify_terminal_exception(ValueError(secret)), "unexpected_failure")
        self.assertNotIn(secret, json.dumps(classify_terminal_exception(ValueError(secret))))
        self.assertEqual(
            classify_terminal_exception(urllib.error.HTTPError("https://example.invalid/secret", 401, secret, {}, None)),
            "pilot_http_failure_nonretryable",
        )


if __name__ == "__main__":
    unittest.main()
