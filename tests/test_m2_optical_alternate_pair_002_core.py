"""Generated-only PB 05.13 candidate checks; no external custody."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_optical_alternate_pair_002_core import (  # noqa: E402
    EXACT_PRODUCTS,
    decide_before_screen,
    inspect_product_metadata,
    single_date_usable_mask,
)
import m2_optical_alternate_pair_002_reader as reader  # noqa: E402
import m2_optical_alternate_pair_002_qa as qa  # noqa: E402
import m2_optical_alternate_pair_002_control as control  # noqa: E402
import m2_optical_alternate_pair_002_before_execute as before_execute  # noqa: E402
import m2_optical_alternate_pair_002_before_worker as before_worker  # noqa: E402
import m2_optical_alternate_pair_002_preflight as preflight  # noqa: E402
from m2_optical_alternate_pair_002_display import display_rgb  # noqa: E402
from m2_optical_gdal_recovery_002_adapter import TARGET_GRID  # noqa: E402
from optical_input_readiness_core import ROLE_PATTERNS  # noqa: E402


def metadata(baseline: str) -> str:
    return ("<Product><PROCESSING_BASELINE>" + baseline + "</PROCESSING_BASELINE>"
            "<SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT>"
            "<SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX>"
            "<BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>"
            + "".join(f'<BOA_ADD_OFFSET band_id="{i}">-1000</BOA_ADD_OFFSET>'
                      for i in range(13)) + "</Product>")


class CandidateMetadataTests(unittest.TestCase):
    def test_approval_binds_unchanged_reviewed_packet(self) -> None:
        approval = json.loads((ROOT / "records/source-gates/m2-optical-alternate-map-pair-002-approval.json").read_text())
        self.assertEqual(approval["decision"], "approve")
        for kind, ref in (("proposal", "contracts/milestone-002-optical-alternate-map-pair-002-proposal.json"),
                          ("review_bundle", "reviews/m2-optical-alternate-map-pair-002/review-bundle.json")):
            self.assertEqual(hashlib.sha256((ROOT / ref).read_bytes()).hexdigest(),
                             approval["bindings"][kind + "_sha256"])
        self.assertFalse(approval["authority"]["automatic_retry"])

    def test_each_product_uses_its_own_baseline_and_offsets(self) -> None:
        for source_id, (name, baseline) in EXACT_PRODUCTS.items():
            result = inspect_product_metadata(source_id, name, metadata(baseline))
            self.assertEqual(result["processing_baseline"], baseline)
            self.assertEqual(result["offsets_by_band"]["B11"], -1000)
            self.assertFalse(result["cross_baseline_harmonization"])

    def test_cross_baseline_or_identity_drift_blocks(self) -> None:
        name = EXACT_PRODUCTS["M2-OPT-003"][0]
        with self.assertRaisesRegex(ValueError, "baseline"):
            inspect_product_metadata("M2-OPT-003", name, metadata("05.12"))
        with self.assertRaisesRegex(ValueError, "identity"):
            inspect_product_metadata("M2-OPT-003", name.replace("T45RUM", "T45RUL"), metadata("05.13"))
        with self.assertRaisesRegex(ValueError, "scaling"):
            inspect_product_metadata("M2-OPT-003", name, "<Product><PROCESSING_BASELINE>05.13</PROCESSING_BASELINE></Product>")


class CandidateMaskTests(unittest.TestCase):
    def test_full_production_grid_shape_without_project_data(self) -> None:
        shape = (TARGET_GRID["rows"], TARGET_GRID["columns"])
        scl = np.broadcast_to(np.uint8(4), shape)
        quality = np.broadcast_to(np.uint8(0), (3, *shape))
        b11 = np.broadcast_to(np.uint16(200), shape)
        result = single_date_usable_mask(scl, quality, b11)
        self.assertEqual(result["usable"].shape, shape)
        self.assertEqual(int(np.count_nonzero(result["usable"])), 3950 * 4726)
        self.assertFalse(result["unknown_scl_present"])

    def test_scl_quality_nodata_and_dn_zero_remain_excluded(self) -> None:
        scl = np.array([[4, 5, 6, 3, 255, 12]], dtype=np.uint8)
        quality = np.zeros((3, 1, 6), dtype=np.uint8)
        quality[1, 0, 1] = 1
        b11 = np.array([[200, 200, 0, 200, 200, 200]], dtype=np.uint16)
        result = single_date_usable_mask(scl, quality, b11)
        self.assertEqual(result["usable"].tolist(), [[True, False, False, False, False, False]])
        self.assertTrue(result["unknown_scl_present"])

    def test_threshold_is_per_target_aoi_not_overview(self) -> None:
        scl = np.array([[4, 4, 4, 4, 4, 4, 4, 4, 3, 3]], dtype=np.uint8)
        quality = np.zeros((3, 1, 10), dtype=np.uint8)
        b11 = np.full((1, 10), 200, dtype=np.uint16)
        aoi = {"AOI-SOURCE": np.array([[1, 1, 1, 1, 1, 0, 0, 0, 0, 0]], dtype=bool),
               "AOI-UPPER-CORRIDOR": np.array([[0, 0, 0, 0, 0, 1, 1, 1, 1, 1]], dtype=bool)}
        mask = single_date_usable_mask(scl, quality, b11)
        result = decide_before_screen(mask, aoi)
        self.assertEqual(result["status"], "block")
        self.assertEqual(result["aoi_results"]["AOI-SOURCE"]["usable_fraction_of_aoi"], 1.0)
        self.assertEqual(result["aoi_results"]["AOI-UPPER-CORRIDOR"]["usable_fraction_of_aoi"], 0.6)
        scl[0, 8] = 4
        result = decide_before_screen(single_date_usable_mask(scl, quality, b11), aoi)
        self.assertEqual(result["status"], "pass_acquisition_prerequisite_only")
        self.assertFalse(result["pair_pixel_qa_or_scientific_admission"])

    def test_unknown_class_blocks_even_with_high_usable_fraction(self) -> None:
        scl = np.array([[4] * 19 + [12]], dtype=np.uint8)
        quality = np.zeros((3, 1, 20), dtype=np.uint8)
        b11 = np.full((1, 20), 200, dtype=np.uint16)
        aoi = {"AOI-SOURCE": np.array([[True] * 10 + [False] * 10]),
               "AOI-UPPER-CORRIDOR": np.array([[False] * 10 + [True] * 10])}
        self.assertEqual(decide_before_screen(single_date_usable_mask(scl, quality, b11), aoi)["status"], "block")


class CandidateReaderTests(unittest.TestCase):
    def test_generated_pb0513_members_checked_before_headers(self) -> None:
        source_id = "M2-OPT-003"
        product = EXACT_PRODUCTS[source_id][0]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "materialization-001"
            safe = base / product
            safe.mkdir(parents=True)
            files = []
            for role, pattern in ROLE_PATTERNS.items():
                relative = pattern.replace("*", "SYNTHETIC")
                path = safe / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                contents = (metadata("05.13").encode() if role == "metadata_product"
                            else b"generated-disposable-fixture")
                path.write_bytes(contents)
                files.append({"relative_path": relative, "size_bytes": len(contents),
                              "sha256": hashlib.sha256(contents).hexdigest()})
            (base / "materialization-manifest.json").write_text(
                json.dumps({"status": "complete", "files": files}), encoding="utf-8")
            with patch.object(reader, "describe", return_value={"format": "JP2"}) as described:
                observed, paths = reader.inspect_materialized(source_id, base)
            self.assertEqual(observed["metadata"]["processing_baseline"], "05.13")
            self.assertFalse(observed["raster_pixels_decoded"])
            self.assertEqual(described.call_count, 8)
            self.assertEqual(len(paths), 10)
            paths["SCL"].write_bytes(b"changed")
            with patch.object(reader, "describe", side_effect=AssertionError("header opened before identity")):
                with self.assertRaisesRegex(ValueError, "identity_drift"):
                    reader.inspect_materialized(source_id, base)

    def test_disposable_before_screen_uses_exact_roles_and_grid(self) -> None:
        scl = np.array([[4, 4, 4, 4, 4]], dtype=np.uint8)
        quality = np.zeros((3, 1, 5), dtype=np.uint8)
        b11 = np.full((1, 5), 200, dtype=np.uint16)
        aoi = {"spatialReference": {"wkid": 32645}, "features": [
            {"attributes": {"AOI_ID": identifier}} for identifier in
            ("AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR")
        ]}
        masks = iter([np.array([[True, True, False, False, False]]),
                      np.array([[False, False, True, True, True]])])
        def warp(_path, role, _grid):
            return {"SCL": scl, "quality_classification": quality, "B11": b11}[role]
        with patch.object(reader, "warp_target", side_effect=warp), \
                patch.object(reader, "rasterize_aoi", side_effect=lambda *_: next(masks)):
            result = reader.screen_before_arrays({
                "SCL": Path("generated-scl"), "quality_classification": Path("generated-quality"),
                "B11": Path("generated-b11"),
            }, aoi=aoi)
        self.assertEqual(result["status"], "pass_acquisition_prerequisite_only")
        self.assertFalse(result["new_source_requested"])


class CandidatePairQaTests(unittest.TestCase):
    def test_pair_qa_cannot_start_without_exact_passing_headers(self) -> None:
        with self.assertRaisesRegex(ValueError, "header_gate"):
            qa.evaluate_pair({}, {"status": "block", "source_order": list(qa.SOURCE_ORDER)})
        with self.assertRaisesRegex(ValueError, "header_gate"):
            qa.evaluate_pair({}, {"status": "pass_header_readability_only",
                                  "source_order": ["M2-OPT-001", "M2-OPT-002"]})

    def test_pair_qa_exposes_cross_baseline_uncertainty_without_change_metric(self) -> None:
        aoi = {"features": [{"attributes": {"AOI_ID": identifier}}
                            for identifier in ("AOI-OVERVIEW", *qa.TARGET_AOIS)]}
        header = {"status": "pass_header_readability_only", "source_order": list(qa.SOURCE_ORDER),
                  "products": {source_id: {"descriptions": {"B11": {}, "SCL": {}}}
                               for source_id in qa.SOURCE_ORDER}}
        paths = {source_id: {role: Path("generated-disposable")
                             for role in ("SCL", "B11", "quality_classification")}
                 for source_id in qa.SOURCE_ORDER}
        settings = json.loads((ROOT / "config/qa/optical-pixel-readiness-contract-001.json").read_text())
        classified = {"classes": np.ones((1, 2), dtype=np.int16),
                      "pair_valid": np.ones((1, 2), dtype=bool),
                      "unknown_scl_present": False}
        with patch.object(qa, "warp_target", side_effect=lambda _path, role, _grid:
                          np.zeros((3, 1, 2), dtype=np.uint8) if role == "quality_classification"
                          else np.full((1, 2), 4 if role == "SCL" else 200, dtype=np.uint16)), \
                patch.object(qa, "classify_pair_pixels", return_value=classified), \
                patch.object(qa, "tabulate_aoi", side_effect=lambda _c, feature, *_args:
                             {"aoi_id": feature["attributes"]["AOI_ID"], "status": "pass_qa_only"}), \
                patch.object(qa, "grid_from_description", return_value={}), \
                patch.object(qa, "evaluate_grid_pair", return_value={"status": "pass_qa_only"}), \
                patch.object(qa, "bbox", return_value=(0, 0, 1, 1)), \
                patch.object(qa, "measure_stable_registration", return_value={"status": "pass_qa_only"}):
            result = qa.evaluate_pair(paths, header, aoi=aoi, settings=settings,
                                      pixel_contract={})
        self.assertEqual(result["source_order"], list(qa.SOURCE_ORDER))
        self.assertEqual(result["processing_baselines"], ["05.12", "05.13"])
        self.assertFalse(result["cross_date_reflectance_or_index_change_computed"])
        self.assertFalse(result["baseline_admission_or_event_attribution"])
        self.assertIn("cast-shadow", result["method_uncertainty"])


class CandidateDisplayTests(unittest.TestCase):
    def test_per_product_offset_fixed_display_scale_and_mask(self) -> None:
        bands = {role: np.array([[0, 2000, 65535]], dtype=np.uint16)
                 for role in ("B04", "B03", "B02")}
        metadata = {"quantification_value": 10000,
                    "offsets_by_band": {role: -1000 for role in bands}}
        image = display_rgb(bands, metadata, np.array([[True, True, False]]))
        self.assertEqual(image.shape, (3, 1, 3))
        self.assertEqual(image[:, 0, 0].tolist(), [0, 0, 0])
        self.assertEqual(image[:, 0, 2].tolist(), [0, 0, 0])
        self.assertTrue(all(1 <= value <= 255 for value in image[:, 0, 1]))
        changed = {**metadata, "offsets_by_band": {role: -1500 for role in bands}}
        self.assertFalse(np.array_equal(image, display_rgb(bands, changed,
                                                            np.array([[True, True, False]]))))


class CandidateSupervisorTests(unittest.TestCase):
    def test_public_ci_missing_stops_before_any_external_custody_access(self) -> None:
        self.assertEqual(control.require_packet()["proposal_id"],
                         "NEPAL-M2-OPTICAL-ALTERNATE-MAP-PAIR-002")
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(control, "EXECUTION_GATE", Path(directory) / "missing-gate.json"):
                with self.assertRaisesRegex(control.PairControlError, "public_ci_gate_missing"):
                    control.require_public_ci()

    def test_public_ci_gate_must_be_committed(self) -> None:
        gate = {"status": "pass_public_default_branch_ci_pair_002_before_screen_gate",
                "proposal_sha256": control.PROPOSAL_SHA256,
                "bundle_sha256": control.BUNDLE_SHA256,
                "approval_sha256": control.APPROVAL_SHA256,
                "public_ci_conclusion": "success", "public_ci_run_id": 1,
                "implementation_commit": "synthetic", "public_ci_head_sha": "synthetic",
                "released_stage_after_final_no_content_preflight":
                "at_most_one_exact_M2-OPT-001_single_date_screen",
                "new_M2-OPT-003_acquisition_released_by_this_gate": False}
        with patch.object(control, "read_json", return_value=gate), \
                patch.object(control, "EXECUTION_GATE", control.APPROVAL), \
                patch.object(control, "subprocess") as process, \
                patch.object(control, "require_packet"):
            process.run.return_value.returncode = 1
            with self.assertRaisesRegex(control.PairControlError, "not_committed"):
                control.require_public_ci()

    def test_final_preflight_collision_stops_before_custody(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            collision = Path(directory) / "preflight.json"
            collision.touch()
            with patch.object(preflight, "FINAL_PREFLIGHT", collision), \
                    patch.object(preflight, "require_public_ci", return_value={}), \
                    patch.object(preflight, "BEFORE_SOURCE", Path(directory) / "must-not-open"):
                with self.assertRaisesRegex(control.PairControlError, "collision"):
                    preflight.preflight()

    def test_environment_drops_sensitive_keys(self) -> None:
        self.assertEqual(control.child_environment({"PATH": "synthetic", "CDSE_TOKEN": "secret",
                                                    "PASSWORD": "secret", "API_KEY": "secret"}),
                         {"PATH": "synthetic"})

    def test_one_shot_reservation_and_secret_safe_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt = root / "before-attempt"
            terminal_path = root / "terminal.json"
            preflight_path = root / "preflight.json"
            preflight_path.write_text(json.dumps({
                "status": "pass_exact_no_payload_preflight_before_screen_only",
                "public_execution_gate_sha256": "synthetic-gate"}), encoding="utf-8")
            python_path = root / "python.exe"
            worker_path = root / "worker.py"
            python_path.touch()
            worker_path.touch()
            calls = []

            def synthetic_runner(_command, **kwargs):
                calls.append("spawn")
                self.assertTrue((attempt / "terminal-reserved.json").is_file())
                self.assertTrue((attempt / "cleanup-reserved.json").is_file())
                self.assertNotIn("CDSE_TOKEN", kwargs["env"])
                (attempt / "worker-terminal.json").write_text(json.dumps({
                    "status": "completed_single_date_screen",
                    "header_status": "pass_single_source_header_only",
                    "stage": "secret-value"}), encoding="utf-8")
                (attempt / "screen.json").write_text(json.dumps({
                    "status": "block", "source_id": "M2-OPT-001", "threshold": .8,
                    "new_source_requested": False,
                    "pair_pixel_qa_or_scientific_admission": False,
                    "unknown_scl_present": False, "aoi_results": {
                        "AOI-SOURCE": {"aoi_cell_count": 10, "covered_cell_count": 10,
                                       "usable_cell_count": 1, "usable_fraction_of_aoi": .1},
                        "AOI-UPPER-CORRIDOR": {"aoi_cell_count": 10,
                                               "covered_cell_count": 10,
                                               "usable_cell_count": 2,
                                               "usable_fraction_of_aoi": .2}},
                    "untrusted": "secret-value"}), encoding="utf-8")
                return type("Result", (), {"returncode": 0})()

            with patch.object(before_execute, "ATTEMPT", attempt), \
                    patch.object(before_execute, "BEFORE_TERMINAL", terminal_path), \
                    patch.object(before_execute, "FINAL_PREFLIGHT", preflight_path), \
                    patch.object(before_execute, "ARCGIS_PYTHON", python_path), \
                    patch.object(before_execute, "WORKER", worker_path), \
                    patch.object(before_execute, "require_public_ci"), \
                    patch.object(before_execute, "sha256_file", side_effect=lambda path:
                                 "synthetic-gate" if path == before_execute.EXECUTION_GATE
                                 else hashlib.sha256(Path(path).read_bytes()).hexdigest()), \
                    patch.dict(before_execute.os.environ, {"CDSE_TOKEN": "secret-value"}):
                result = before_execute.run_once(runner=synthetic_runner)
                self.assertEqual(result["status"], "completed_single_date_screen")
                self.assertEqual(result["screen_status"], "block")
                self.assertNotIn("secret-value", terminal_path.read_text(encoding="utf-8"))
                with self.assertRaisesRegex(control.PairControlError, "consumed_or_collision"):
                    before_execute.run_once(runner=synthetic_runner)
            self.assertEqual(calls, ["spawn"])

    def test_untrusted_screen_cannot_invent_passing_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            (attempt / "worker-terminal.json").write_text(json.dumps({
                "status": "completed_single_date_screen",
                "header_status": "pass_single_source_header_only"}), encoding="utf-8")
            (attempt / "screen.json").write_text(json.dumps({
                "status": "pass_acquisition_prerequisite_only", "source_id": "M2-OPT-001",
                "threshold": .8, "new_source_requested": False,
                "pair_pixel_qa_or_scientific_admission": False,
                "unknown_scl_present": False,
                "aoi_results": {key: {"aoi_cell_count": 10,
                                      "covered_cell_count": 10,
                                      "usable_cell_count": 1,
                                      "usable_fraction_of_aoi": .1}
                                for key in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")}}),
                encoding="utf-8")
            with patch.object(before_execute, "ATTEMPT", attempt):
                result = before_execute.terminal_from_child(0)
            self.assertEqual(result["status"], "stopped")
            self.assertIsNone(result["screen_status"])

    def test_interrupted_spawn_consumes_identity_and_keeps_safe_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt = root / "before-attempt"
            terminal_path = root / "terminal.json"
            preflight_path = root / "preflight.json"
            preflight_path.write_text(json.dumps({
                "status": "pass_exact_no_payload_preflight_before_screen_only",
                "public_execution_gate_sha256": "synthetic-gate"}), encoding="utf-8")
            python_path = root / "python.exe"
            worker_path = root / "worker.py"
            python_path.touch()
            worker_path.touch()
            calls = []

            def interrupted(_command, **_kwargs):
                calls.append("spawn")
                self.assertTrue((attempt / "terminal-reserved.json").exists())
                raise OSError("secret-value")

            with patch.object(before_execute, "ATTEMPT", attempt), \
                    patch.object(before_execute, "BEFORE_TERMINAL", terminal_path), \
                    patch.object(before_execute, "FINAL_PREFLIGHT", preflight_path), \
                    patch.object(before_execute, "ARCGIS_PYTHON", python_path), \
                    patch.object(before_execute, "WORKER", worker_path), \
                    patch.object(before_execute, "require_public_ci"), \
                    patch.object(before_execute, "sha256_file", return_value="synthetic-gate"):
                result = before_execute.run_once(runner=interrupted)
                self.assertEqual(result["status"], "stopped")
                self.assertEqual(result["stage"], "supervisor_spawn_or_receipt")
                self.assertNotIn("secret-value", terminal_path.read_text(encoding="utf-8"))
                with self.assertRaisesRegex(control.PairControlError, "consumed_or_collision"):
                    before_execute.run_once(runner=interrupted)
            self.assertEqual(calls, ["spawn"])

    def test_worker_safe_failure_retains_terminal_without_exception_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory)
            with patch.object(before_worker, "ATTEMPT", attempt), \
                    patch.object(before_worker, "run", side_effect=RuntimeError("secret-value")):
                self.assertEqual(before_worker.main(), 20)
            terminal = (attempt / "worker-terminal.json").read_text(encoding="utf-8")
            self.assertNotIn("secret-value", terminal)
            self.assertEqual(json.loads(terminal)["status"], "stopped")


if __name__ == "__main__":
    unittest.main()
