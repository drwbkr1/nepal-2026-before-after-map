"""Portable no-payload tests for the seven-tile event-pair intake controls."""

from __future__ import annotations

import sys
import tempfile
import unittest
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_radar_event_pair_dem_intake_001 as route


class FakeResponse:
    def __init__(self, asset, *, etag=None, url=None):
        self.asset = asset
        self.status = 200
        self.headers = {
            "Content-Length": str(asset["observed_head_content_length_bytes"]),
            "ETag": asset["observed_head_etag"] if etag is None else etag,
            "Content-Type": "image/tiff",
        }
        self.url = asset["anonymous_https_url"] if url is None else url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b""

    def geturl(self):
        return self.url


class FakeOpener:
    def __init__(self, asset, *, etag=None, url=None):
        self.asset = asset
        self.etag = etag
        self.url = url
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        if request.get_method() != "HEAD" or request.full_url != self.asset["anonymous_https_url"] or timeout != 60:
            raise AssertionError("unexpected network request")
        return FakeResponse(self.asset, etag=self.etag, url=self.url)


class EventPairIntakeTests(unittest.TestCase):
    def test_exact_approved_assets_are_fixed_order(self):
        assets = route.exact_assets()
        self.assertEqual([item["item_id"] for item in assets], list(route.ITEMS))
        self.assertEqual(sum(item["observed_head_content_length_bytes"] for item in assets), 273055703)

    def test_exact_head_identity_is_accepted(self):
        asset = route.exact_assets()[0]
        opener = FakeOpener(asset)
        self.assertEqual(route.check_head(asset, opener=opener)["content_length"], asset["observed_head_content_length_bytes"])
        self.assertEqual(opener.calls, 1)

    def test_changed_etag_stops(self):
        asset = route.exact_assets()[0]
        with self.assertRaisesRegex(route.IntakeError, "source_head_identity_drift"):
            route.check_head(asset, opener=FakeOpener(asset, etag='"drift"'))

    def test_redirected_url_stops(self):
        asset = route.exact_assets()[0]
        with self.assertRaisesRegex(route.IntakeError, "source_head_identity_drift"):
            route.check_head(asset, opener=FakeOpener(asset, url="https://other.example/file.tif"))

    def test_exact_license_bytes_and_redirect_guard(self):
        body = b"%PDF-1.7\nsynthetic license"

        class LicenseResponse:
            status = 200
            headers = {"Content-Type": "application/pdf"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return body

            def geturl(self):
                return route.LICENSE_URL

        class Opener:
            def open(self, request, timeout):
                self.request_method = request.get_method()
                self.request_url = request.full_url
                self.timeout = timeout
                return LicenseResponse()

        opener = Opener()
        with patch.object(route, "LICENSE_SHA", hashlib.sha256(body).hexdigest()):
            self.assertEqual(route.check_license(opener=opener)["size_bytes"], len(body))
            self.assertEqual((opener.request_method, opener.request_url, opener.timeout), ("GET", route.LICENSE_URL, 60))
        with self.assertRaisesRegex(route.IntakeError, "exact_license_document_drift"):
            route.check_license(opener=opener)

    def test_stac_item_identity_is_exact(self):
        asset = route.exact_assets()[0]
        item = {"id": asset["item_id"], "collection": "cop-dem-glo-30-dged-cog", "bbox": asset["cell_wgs84"], "assets": {"data": {"href": "https://example.invalid/data"}}}

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return json.dumps(item).encode("utf-8")

            def geturl(self):
                return asset["stac_item_url"]

        class Opener:
            def open(self, request, timeout):
                self.method = request.get_method()
                return Response()

        opener = Opener()
        self.assertEqual(route.check_stac(asset, opener=opener)["item_id"], asset["item_id"])
        self.assertEqual(opener.method, "GET")
        item["id"] = "substituted"
        with self.assertRaisesRegex(route.IntakeError, "stac_item_identity_drift"):
            route.check_stac(asset, opener=opener)

    def test_attempt_number_is_bounded(self):
        with self.assertRaisesRegex(route.IntakeError, "unapproved_item_or_attempt"):
            route.paths_for(route.ITEMS[0], 3)
        with self.assertRaisesRegex(route.IntakeError, "unapproved_item_or_attempt"):
            route.paths_for("other", 1)

    def test_scope_drift_blocks_before_network(self):
        approval = route.load(route.APPROVAL_REF)
        approval["authority"]["baseline_admission_or_change_analysis"] = True
        original = route.load
        with patch.object(route, "load", side_effect=lambda ref: approval if ref == route.APPROVAL_REF else original(ref)):
            with self.assertRaisesRegex(route.IntakeError, "approval_scope_drift"):
                route.exact_assets()

    def test_single_byte_zero_success_creates_durable_receipts(self):
        payload = b"synthetic-tiff-bytes"
        asset = dict(route.exact_assets()[0])
        asset["observed_head_content_length_bytes"] = len(payload)
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)

            class Response(FakeResponse):
                def __init__(self, item):
                    super().__init__(item)
                    self.remaining = payload

                def read(self, _size=None):
                    value, self.remaining = self.remaining, b""
                    return value

            class Opener(FakeOpener):
                def open(self, request, timeout):
                    self.calls += 1
                    return FakeResponse(asset) if request.get_method() == "HEAD" else Response(asset)

            with (
                patch.object(route, "DATA_ROOT", data_root),
                patch.object(route, "exact_assets", return_value=[asset]),
                patch.object(route, "require_execution_gates"),
                patch.object(route, "verify_geotiff", return_value={"valid_pixels": 1}),
                patch.object(route, "MIN_FREE_BYTES", 1),
            ):
                result = route.acquire_one(0, opener=Opener(asset))
                paths = route.paths_for(asset["item_id"])
                self.assertEqual(result["status"], "pass_verified_and_promoted")
                self.assertEqual(paths["destination"].read_bytes(), payload)
                self.assertGreater(paths["terminal"].stat().st_size, 0)
                self.assertGreater(paths["cleanup"].stat().st_size, 0)
                self.assertEqual(paths["error"].stat().st_size, 0)
                with self.assertRaisesRegex(route.IntakeError, "fresh_attempt_or_destination_collision"):
                    route.acquire_one(0, opener=Opener(asset))

    def test_interrupted_transfer_is_terminal_and_partial_is_preserved(self):
        payload = b"partial"
        asset = dict(route.exact_assets()[0])
        asset["observed_head_content_length_bytes"] = len(payload) + 10
        with tempfile.TemporaryDirectory() as directory:
            class PartialResponse(FakeResponse):
                def __init__(self, item):
                    super().__init__(item)
                    self.remaining = payload

                def read(self, _size=None):
                    value, self.remaining = self.remaining, b""
                    return value

            class Opener(FakeOpener):
                def open(self, request, timeout):
                    self.calls += 1
                    return FakeResponse(asset) if request.get_method() == "HEAD" else PartialResponse(asset)

            with (
                patch.object(route, "DATA_ROOT", Path(directory)),
                patch.object(route, "exact_assets", return_value=[asset]),
                patch.object(route, "require_execution_gates"),
                patch.object(route, "MIN_FREE_BYTES", 1),
            ):
                result = route.acquire_one(0, opener=Opener(asset))
                paths = route.paths_for(asset["item_id"])
                self.assertEqual(result["status"], "terminal_failure_no_retry")
                self.assertEqual(result["failure_code"], "transfer_length_mismatch")
                self.assertEqual(paths["staging"].read_bytes(), payload)
                self.assertGreater(paths["error"].stat().st_size, 0)
                self.assertFalse(paths["destination"].exists())


if __name__ == "__main__":
    unittest.main()
