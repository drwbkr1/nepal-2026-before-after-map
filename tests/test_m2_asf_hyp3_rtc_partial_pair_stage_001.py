"""Synthetic fail-closed and terminal tests for the exact ASF pair stage."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_asf_hyp3_rtc_partial_pair_stage_001 as route  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _aoi_rows() -> list[dict]:
    return [{"aoi_id": key, "status": "defer",
             "unknown_provider_mask_value_present": False,
             "valid_area_m2": 21., "aoi_area_m2": 100.}
            for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")]


class PartialPairStageTests(unittest.TestCase):
    def test_complete_synthetic_release_binds_every_gate(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary)

            def write(ref, value):
                path = root / ref
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
                return _sha(path.read_bytes())

            before_bytes, after_bytes = b"before", b"after"
            before_sha, after_sha = _sha(before_bytes), _sha(after_bytes)
            before_archive = root / route.BEFORE_ARCHIVE_REF
            after_archive = root / "m2-asf-hyp3-rtc-products-after-partial-001" / "after.zip"
            for path, payload in ((before_archive, before_bytes),
                                  (after_archive, after_bytes)):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            for name, value in (("BEFORE_ARCHIVE_SIZE", len(before_bytes)),
                                ("BEFORE_ARCHIVE_SHA", before_sha),
                                ("IMPLEMENTATION_FILES", ())):
                stack.enter_context(mock.patch.object(route, name, value))
            aoi_sha = write(route.AOI_REF, {})
            contract_sha = write(route.CONTRACT_REF, {})
            stack.enter_context(mock.patch.object(route, "AOI_SHA256", aoi_sha))
            stack.enter_context(mock.patch.object(route, "CONTRACT_SHA256", contract_sha))
            approval_sha = write(route.APPROVAL_REF, {
                "decision": "approve", "authority": {
                    "conditional_local_EPSG_32645_partial_pair_panel_and_fresh_process_export": True}})
            source_gate_sha = write(route.SOURCE_GATE_REF,
                                    {"decision": {"status": "ready"}})
            stack.enter_context(mock.patch.object(route, "APPROVAL_SHA", approval_sha))
            stack.enter_context(mock.patch.object(route, "SOURCE_GATE_SHA", source_gate_sha))
            job = "00000000-0000-4000-8000-000000000001"
            submission_sha = write(route.SUBMISSION_REF, {
                "status": "submitted_product_unverified", "source_id": route.AFTER_SOURCE,
                "job_id": job, "credit_cost": 60,
                "credentials_recorded": False, "product_bytes_verified": False,
                "pixel_qa_pass": False})
            before_acq_sha = write(route.BEFORE_ACQUISITION_REF, {
                "status": "pass_local_zip_promoted_no_replace",
                "source_id": route.BEFORE_SOURCE, "job_id": route.BEFORE_JOB,
                "archive_sha256": before_sha,
                "archive_size_bytes": len(before_bytes)})
            after_acq_sha = write(route.AFTER_ACQUISITION_REF, {
                "status": "pass_local_zip_promoted_no_replace",
                "source_id": route.AFTER_SOURCE, "job_id": job,
                "product_filename": after_archive.name,
                "archive_integrity_verified": True,
                "archive_sha256": after_sha,
                "archive_size_bytes": len(after_bytes)})
            before_review_sha = write(route.BEFORE_REVIEW_REF, {
                "status": "pass_product_metadata_for_separate_local_header_and_pixel_qa_only",
                "source_id": route.BEFORE_SOURCE, "job_id": route.BEFORE_JOB,
                "bindings": {"archive_sha256": before_sha}})
            after_review_sha = write(route.AFTER_REVIEW_REF, {
                "status": "pass_after_metadata_for_header_and_pixel_qa_only",
                "source_id": route.AFTER_SOURCE, "job_id": job,
                "bindings": {"archive_sha256": after_sha}})
            before_header_sha = write(route.BEFORE_HEADER_REF, {
                "status": "pass_actual_headers_for_local_pixel_qa_only",
                "source_id": route.BEFORE_SOURCE, "job_id": route.BEFORE_JOB,
                "archive_sha256_verified_current": True})
            after_header_sha = write(route.AFTER_HEADER_REF, {
                "status": "pass_after_headers_for_local_pixel_qa_only",
                "source_id": route.AFTER_SOURCE, "job_id": job,
                "archive_sha256_verified_current": True})
            before_pixel_sha = write(route.BEFORE_PIXEL_REF, {
                "source_id": route.BEFORE_SOURCE, "job_id": route.BEFORE_JOB,
                "status": "stop_source_event_aoi_pixel_qa_no_next_date",
                "archive_sha256_verified_current": True,
                "VV_VH_layover_shadow_AOI_pixels_read": True,
                "aoi_results": _aoi_rows()})
            after_pixel_sha = write(route.AFTER_PIXEL_REF, {
                "source_id": route.AFTER_SOURCE, "job_id": job,
                "archive_sha256_verified_current": True,
                "VV_VH_layover_shadow_AOI_pixels_read": True,
                "disposition": {
                    "partial_pair_candidate_pending_same_cell_overlap": True},
                "aoi_results": _aoi_rows()})
            rights_sha = write(route.RIGHTS_REF, {
                "status": "pass_local_rtc_vv_visual_display_only",
                "bindings": {"before_review_sha256": before_review_sha,
                             "after_review_sha256": after_review_sha},
                "local_VV_display": True,
                "DEM_display_or_export": False,
                "public_derived_pixels": False})
            bindings = {
                "approval_sha256": approval_sha,
                "rights_review_sha256": rights_sha,
                "submission_sha256": submission_sha,
                "before_review_sha256": before_review_sha,
                "after_review_sha256": after_review_sha,
                "before_acquisition_sha256": before_acq_sha,
                "before_header_sha256": before_header_sha,
                "before_pixel_sha256": before_pixel_sha,
                "after_acquisition_sha256": after_acq_sha,
                "after_header_sha256": after_header_sha,
                "after_pixel_sha256": after_pixel_sha,
                "aoi_sha256": aoi_sha, "contract_sha256": contract_sha,
                "implementation_file_sha256": {},
            }
            gate_sha = write(route.GATE_REF, {
                "status": "pass_partial_pair_stage_implementation_public_ci_only",
                "public_ci": {"conclusion": "success"}, "bindings": bindings})
            write(route.PREFLIGHT_REF, {
                "status": "pass_partial_pair_stage_no_content",
                "bindings": {"implementation_gate_sha256": gate_sha,
                             "before_acquisition_sha256": before_acq_sha,
                             "after_acquisition_sha256": after_acq_sha},
                "assertions": {"attempt_absent": True,
                               "no_pair_pixel_read": True}})
            attempt = root / "m2-asf-hyp3-rtc-partial-pair-stage-001" / "attempt-001"
            released = route.require_release(root, root, attempt)
            self.assertEqual(released[0]["job_id"], job)
            self.assertEqual(released[1:3], (before_archive, after_archive))
            rights = json.loads((root / route.RIGHTS_REF).read_text())
            rights["local_VV_display"] = False
            write(route.RIGHTS_REF, rights)
            with self.assertRaises(RouteStop) as caught:
                route.require_release(root, root, attempt)
            self.assertEqual(caught.exception.code, "partial_pair_stage_not_released")

    def test_no_content_release_stops_without_future_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(RouteStop) as caught:
                route.require_release(root, root,
                                      root / "m2-asf-hyp3-rtc-partial-pair-stage-001"
                                      / "attempt-001")
        self.assertEqual(caught.exception.code,
                         "partial_pair_stage_required_path_invalid")

    def test_individual_pixel_screen_is_not_pair_admission(self):
        before = {"source_id": route.BEFORE_SOURCE,
                  "job_id": route.BEFORE_JOB,
                  "status": "stop_source_event_aoi_pixel_qa_no_next_date",
                  "archive_sha256_verified_current": True,
                  "VV_VH_layover_shadow_AOI_pixels_read": True,
                  "aoi_results": _aoi_rows()}
        after = {"source_id": route.AFTER_SOURCE,
                 "archive_sha256_verified_current": True,
                 "VV_VH_layover_shadow_AOI_pixels_read": True,
                 "disposition": {
                     "partial_pair_candidate_pending_same_cell_overlap": True},
                 "aoi_results": _aoi_rows()}
        self.assertTrue(route._source_pixel_ready(before, after))
        after["aoi_results"][0]["unknown_provider_mask_value_present"] = True
        self.assertFalse(route._source_pixel_ready(before, after))
        after["aoi_results"][0]["unknown_provider_mask_value_present"] = False
        after["aoi_results"][0]["valid_area_m2"] = 19.
        self.assertFalse(route._source_pixel_ready(before, after))

    def test_one_attempt_success_and_collision_keep_non_git_receipts(self):
        before_bytes, after_bytes = b"before-zip", b"after-zip"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before, after = root / "before.zip", root / "after.zip"
            before.write_bytes(before_bytes)
            after.write_bytes(after_bytes)
            attempt = root / "m2-asf-hyp3-rtc-partial-pair-stage-001" / "attempt-001"
            acquisition = {"product_filename": after.name,
                           "archive_size_bytes": len(after_bytes),
                           "archive_sha256": _sha(after_bytes),
                           "job_id": "synthetic-after-job"}

            def stage(_before, _after, _before_header, _after_header, output, _root):
                output.mkdir()
                (output / "before_common_valid_vv_db.tif").write_bytes(b"test")
                return {"status": "pass_common_valid_for_local_partial_visual_only",
                        "display_rasters": ["disposable"],
                        "scientific_admission_authorized": False}

            with mock.patch.object(route, "BEFORE_ARCHIVE_SIZE", len(before_bytes)), \
                 mock.patch.object(route, "BEFORE_ARCHIVE_SHA", _sha(before_bytes)):
                terminal = route.process_once(
                    acquisition, before, after, {}, {}, attempt,
                    controlled_root=root, stage=stage, root=root,
                )
                self.assertEqual(terminal["status"],
                                 "pass_common_valid_for_local_partial_visual_only")
                self.assertTrue((attempt / "started.json").is_file())
                self.assertEqual(json.loads((attempt / "terminal.json").read_text())["status"],
                                 terminal["status"])
                self.assertFalse(terminal["map_or_export_created"])
                with self.assertRaises(RouteStop) as caught:
                    route.process_once(acquisition, before, after, {}, {}, attempt,
                                       controlled_root=root, stage=stage, root=root)
                self.assertEqual(caught.exception.code, "partial_pair_stage_attempt_collision")

    def test_failure_is_terminal_with_no_retry(self):
        before_bytes, after_bytes = b"before-zip", b"after-zip"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before, after = root / "before.zip", root / "after.zip"
            before.write_bytes(before_bytes)
            after.write_bytes(after_bytes)
            attempt = root / "m2-asf-hyp3-rtc-partial-pair-stage-001" / "attempt-001"
            acquisition = {"product_filename": after.name,
                           "archive_size_bytes": len(after_bytes),
                           "archive_sha256": _sha(after_bytes)}

            def interrupted(*_args):
                raise RuntimeError("synthetic failure text must not persist")

            with mock.patch.object(route, "BEFORE_ARCHIVE_SIZE", len(before_bytes)), \
                 mock.patch.object(route, "BEFORE_ARCHIVE_SHA", _sha(before_bytes)):
                terminal = route.process_once(acquisition, before, after,
                                              {}, {}, attempt,
                                              controlled_root=root,
                                              stage=interrupted, root=root)
            self.assertEqual(terminal["status"],
                             "stopped_partial_pair_stage_no_automatic_retry")
            self.assertEqual(terminal["code"], "partial_pair_stage_unexpected_failure")
            self.assertNotIn("synthetic failure text", (attempt / "terminal.json").read_text())


if __name__ == "__main__":
    unittest.main()
