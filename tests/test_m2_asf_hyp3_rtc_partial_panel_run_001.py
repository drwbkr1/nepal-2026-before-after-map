"""Portable no-content and one-attempt controls for the ASF local panel."""

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
import m2_asf_hyp3_rtc_partial_panel_run_001 as route  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop  # noqa: E402


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fixture(root: Path):
    display = root / "stage" / "display"
    display.mkdir(parents=True)
    rasters = tuple(display / name for name in route.DISPLAY_NAMES)
    for path, payload in zip(rasters, (b"synthetic-before", b"synthetic-after"), strict=True):
        path.write_bytes(payload)
    rows = [{"aoi_id": key,
             "status": "pass_common_valid_for_local_partial_visual_only",
             "common_valid_fraction_of_aoi": .55 if key == "AOI-SOURCE" else .74,
             "unknown_mask_cells_either_date": 0}
            for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")]
    stage = {
        "status": "pass_common_valid_for_local_partial_visual_only",
        "source_ids": [route.BEFORE_SOURCE, route.AFTER_SOURCE],
        "after_job_id": "synthetic-job",
        "provider_zip_mutated": False,
        "registration_measured": False,
        "scientific_admission": False,
        "map_or_export_created": False,
        "pair_stage_result": {
            "status": "pass_common_valid_for_local_partial_visual_only",
            "wkid": 32645, "display_polarization": "VV",
            "display_units": "gamma0 dB", "resampling_performed": False,
            "registration_measured": False,
            "scientific_admission_authorized": False,
            "aoi_results": rows,
            "display_rasters": [{"name": path.name, "size_bytes": path.stat().st_size,
                                 "sha256": _sha(path.read_bytes())} for path in rasters],
        },
    }
    rights = {"local_panel_credit_line":
              "ASF DAAC HyP3 | ESA | https://doi.org/10.5281/zenodo.3962581 | "
              "https://doi.org/10.5281/zenodo.3962936"}
    coverage = {row["aoi_id"]: row["common_valid_fraction_of_aoi"] for row in rows}
    return stage, rights, rasters, coverage


class PartialPanelRunTests(unittest.TestCase):
    def test_complete_synthetic_release_binds_rasters_and_rights(self):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary)

            def write(ref, value):
                path = root / ref
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
                return _sha(path.read_bytes())

            stage, rights, staged_rasters, _ = _fixture(root)
            job = "00000000-0000-4000-8000-000000000001"
            stage["after_job_id"] = job
            display = root / route.STAGE_DISPLAY_REF
            display.mkdir(parents=True)
            for source in staged_rasters:
                (display / source.name).write_bytes(source.read_bytes())
            stage_sha = write(route.STAGE_REF, stage)
            stage_rights_sha = write(route.STAGE_RIGHTS_REF, {
                "status": "pass_local_rtc_vv_visual_display_only",
                "local_VV_display": True,
                "DEM_display_or_export": False,
                "public_derived_pixels": False})
            aoi_sha = write(route.AOI_REF, {})
            contract_sha = write(route.CONTRACT_REF, {})
            approval_sha = write(route.APPROVAL_REF, {
                "decision": "approve", "authority": {
                    "conditional_local_EPSG_32645_partial_pair_panel_and_fresh_process_export": True}})
            rights.update({"status": "pass_local_rtc_vv_visual_display_only",
                           "bindings": {"parent_rights_review_sha256": stage_rights_sha,
                                        "stage_terminal_sha256": stage_sha},
                           "local_VV_display": True,
                           "DEM_display_or_export": False,
                           "public_derived_pixels": False})
            rights_sha = write(route.RIGHTS_REF, rights)
            submission_sha = write(route.SUBMISSION_REF, {
                "status": "submitted_product_unverified", "source_id": route.AFTER_SOURCE,
                "job_id": job, "credit_cost": 60,
                "credentials_recorded": False, "product_bytes_verified": False,
                "pixel_qa_pass": False})
            for name, value in (("AOI_SHA256", aoi_sha),
                                ("CONTRACT_SHA256", contract_sha),
                                ("APPROVAL_SHA", approval_sha),
                                ("IMPLEMENTATION_FILES", ())):
                stack.enter_context(mock.patch.object(route, name, value))
            gate_sha = write(route.GATE_REF, {
                "status": "pass_partial_panel_implementation_public_ci_only",
                "public_ci": {"conclusion": "success"},
                "bindings": {"approval_sha256": approval_sha,
                             "rights_review_sha256": rights_sha,
                             "stage_terminal_sha256": stage_sha,
                             "submission_sha256": submission_sha,
                             "aoi_sha256": aoi_sha,
                             "contract_sha256": contract_sha,
                             "implementation_file_sha256": {}}})
            write(route.PREFLIGHT_REF, {
                "status": "pass_partial_panel_no_content",
                "bindings": {"implementation_gate_sha256": gate_sha,
                             "stage_terminal_sha256": stage_sha},
                "assertions": {"attempt_absent": True,
                               "no_map_or_export_created": True}})
            attempt = root / "m2-asf-hyp3-rtc-partial-panel-001" / "attempt-001"
            released = route.require_release(root, root, attempt)
            self.assertEqual(released[2], tuple(display / name for name in route.DISPLAY_NAMES))
            self.assertEqual(released[3]["AOI-SOURCE"], .55)
            write(route.STAGE_RIGHTS_REF, {"status": "changed"})
            with self.assertRaises(RouteStop) as caught:
                route.require_release(root, root, attempt)
            self.assertEqual(caught.exception.code, "partial_panel_not_released")
            write(route.STAGE_RIGHTS_REF, {
                "status": "pass_local_rtc_vv_visual_display_only",
                "local_VV_display": True,
                "DEM_display_or_export": False,
                "public_derived_pixels": False})
            (display / route.DISPLAY_NAMES[0]).write_bytes(b"changed")
            with self.assertRaises(RouteStop) as caught:
                route.require_release(root, root, attempt)
            self.assertEqual(caught.exception.code, "partial_panel_not_released")

    def test_missing_real_gates_stop_before_arcgis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(RouteStop) as caught:
                route.require_release(root, root,
                                      root / "m2-asf-hyp3-rtc-partial-panel-001"
                                      / "attempt-001")
        self.assertEqual(caught.exception.code, "partial_panel_required_path_invalid")

    def test_partial_overlap_or_label_drift_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage, _, _, _ = _fixture(Path(temporary))
            result, fractions = route._stage_view(stage)
            self.assertEqual(fractions["AOI-SOURCE"], .55)
            self.assertEqual(result["display_polarization"], "VV")
            stage["pair_stage_result"]["aoi_results"][0][
                "common_valid_fraction_of_aoi"] = .19
            with self.assertRaises(RouteStop) as caught:
                route._stage_view(stage)
            self.assertEqual(caught.exception.code, "partial_panel_stage_overlap_invalid")
            stage["pair_stage_result"]["aoi_results"][0][
                "common_valid_fraction_of_aoi"] = .55
            stage["pair_stage_result"]["display_polarization"] = "VH"
            with self.assertRaises(RouteStop) as caught:
                route._stage_view(stage)
            self.assertEqual(caught.exception.code, "partial_panel_stage_result_invalid")

    def test_single_attempt_pass_then_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, rights, rasters, coverage = _fixture(root)
            attempt = root / "m2-asf-hyp3-rtc-partial-panel-001" / "attempt-001"
            calls = []

            def build(before, after, output, *, common_valid_by_aoi, credits_and_dois):
                calls.append("build")
                self.assertEqual((before, after), rasters)
                self.assertEqual(common_valid_by_aoi, coverage)
                self.assertIn("ASF", credits_and_dois)
                output.mkdir()
                return {"status": "built_local_partial_visual_pending_fresh_reopen"}

            def reopen(output, _root):
                calls.append("reopen")
                self.assertTrue(output.is_dir())
                return {"status": "pass_local_partial_panel_fresh_reopen_and_audit",
                        "audit": {"status": "pass_local_partial_panel_artifact_audit_only"}}

            terminal = route.run_once(stage, rights, rasters, coverage, attempt,
                                      controlled_root=root, build=build,
                                      reopen=reopen, root=root)
            self.assertEqual(calls, ["build", "reopen"])
            self.assertEqual(terminal["status"],
                             "pass_local_partial_panel_verified_visual_only")
            self.assertFalse(terminal["scientific_admission"])
            self.assertEqual(json.loads((attempt / "terminal.json").read_text())["status"],
                             terminal["status"])
            with self.assertRaises(RouteStop) as caught:
                route.run_once(stage, rights, rasters, coverage, attempt,
                               controlled_root=root, build=build,
                               reopen=reopen, root=root)
            self.assertEqual(caught.exception.code, "partial_panel_attempt_collision")

    def test_reopen_failure_retains_terminal_and_no_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, rights, rasters, coverage = _fixture(root)
            attempt = root / "m2-asf-hyp3-rtc-partial-panel-001" / "attempt-001"

            def build(_before, _after, output, **_kwargs):
                output.mkdir()
                return {"status": "built_local_partial_visual_pending_fresh_reopen"}

            def reopen(_output, _root):
                raise RuntimeError("synthetic private error must not persist")

            terminal = route.run_once(stage, rights, rasters, coverage, attempt,
                                      controlled_root=root, build=build,
                                      reopen=reopen, root=root)
            self.assertEqual(terminal["status"],
                             "stopped_partial_panel_no_automatic_retry")
            self.assertTrue((attempt / "panel").is_dir())
            self.assertNotIn("synthetic private error", (attempt / "terminal.json").read_text())


if __name__ == "__main__":
    unittest.main()
