"""Portable guards for the coverage-verified map route; no ArcPy import."""

from __future__ import annotations

import sys
import tempfile
import unittest
import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from m2_map_route_feasibility_001_core import (  # noqa: E402
    MapRouteStop, TARGET, check_final, check_intermediate, project_then_clip,
)
from m2_map_route_feasibility_001_processing import (  # noqa: E402
    compare_retained_windows, require_materialization_space,
)
import validate_m2_map_route_feasibility_001_arcgis as validator  # noqa: E402
import validate_m2_map_route_feasibility_001_crf_arcgis as crf_validator  # noqa: E402
import validate_m2_map_route_feasibility_001_crf_resource_arcgis as resource_validator  # noqa: E402
import m2_map_route_feasibility_001 as runner  # noqa: E402


def grid(bounds, bands=2):
    return {"wkid": 32645, "bounds": list(bounds),
            "width": round((bounds[2] - bounds[0]) / 10),
            "height": round((bounds[3] - bounds[1]) / 10),
            "band_count": bands, "cell_size_x": 10.0, "cell_size_y": 10.0}


INTERMEDIATE = (270750.0, 3067790.0, 369770.0, 3151720.0)


class FakeArcPy:
    def __init__(self, intermediate_bounds=INTERMEDIATE):
        self.calls = []
        self.grids = {}
        self.intermediate_bounds = intermediate_bounds
        self.management = SimpleNamespace(ProjectRaster=self.project, Clip=self.clip)

    def SpatialReference(self, wkid):
        return f"EPSG:{wkid}"

    def Extent(self, *bounds, spatial_reference=None):
        self.calls.append(("extent", bounds, spatial_reference))
        return (bounds, spatial_reference)

    def EnvManager(self, **settings):
        self.calls.append(("environment", settings))
        fake = self

        class Context:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                fake.calls.append(("environment_restored",))
                return False

        return Context()

    def project(self, source, destination, crs, method, cell):
        self.calls.append(("project", source, destination, crs, method, cell))
        self.grids[destination] = grid(self.intermediate_bounds)
        Path(destination).write_bytes(b"projected")

    def clip(self, source, rectangle, destination, nodata, clipping_geometry, maintain, mode):
        self.calls.append(("clip", source, rectangle, destination, nodata, clipping_geometry, maintain, mode))
        self.grids[destination] = grid(TARGET)
        Path(destination).write_bytes(b"clipped")

    def Raster(self, path):
        info = self.grids[path]
        return SimpleNamespace(
            spatialReference=SimpleNamespace(factoryCode=info["wkid"]),
            extent=SimpleNamespace(XMin=info["bounds"][0], YMin=info["bounds"][1],
                                   XMax=info["bounds"][2], YMax=info["bounds"][3]),
            width=info["width"], height=info["height"], bandCount=info["band_count"],
            meanCellWidth=info["cell_size_x"], meanCellHeight=info["cell_size_y"],
        )


class MapRouteCoreTests(unittest.TestCase):
    def test_materialization_free_space_floor(self):
        with mock.patch("m2_map_route_feasibility_001_processing.shutil.disk_usage",
                        return_value=SimpleNamespace(free=40 * 1024**3)):
            require_materialization_space(Path("generated-only"))
        with mock.patch("m2_map_route_feasibility_001_processing.shutil.disk_usage",
                        return_value=SimpleNamespace(free=40 * 1024**3 - 1)):
            with self.assertRaisesRegex(MapRouteStop, "materialization_free_space_below_40_gib"):
                require_materialization_space(Path("generated-only"))

    def test_distinct_runner_source_order_and_first_failure_stop(self):
        self.assertEqual(runner.ATTEMPT_ROOT.name, "a3")
        called = []

        def worker(source_id):
            called.append(source_id)
            return {"source_id": source_id, "status": "stop_source_aoi_qa_no_next_date"}

        self.assertEqual(len(runner.source_sequence(worker)), 1)
        self.assertEqual(called, ["M1-SRC-002"])

    def test_supervisor_preserves_terminal_when_child_exits_without_one(self):
        class FailedChild:
            pid = 12345

            @staticmethod
            def poll():
                return 21

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gate = root / "implementation.json"
            gate.write_text("{}")
            execution = root / "execution.json"
            execution.write_text("{}")
            mosaic = root / "mosaic.tif"
            mosaic.write_bytes(b"generated-test")
            preflight = root / "preflight.json"
            preflight.write_text(__import__("json").dumps({
                "status": "pass_final_no_content_two_source_radar_preflight",
                "implementation_gate_sha256": runner.sha256_file(gate),
                "execution_gate_sha256": runner.sha256_file(execution),
            }))
            assessment = root / "dem-assessment.json"
            assessment.write_text(__import__("json").dumps({
                "status": "pass_actual_sources_and_full_processing_extent_valid_dem",
                "mosaic_sha256": runner.sha256_file(mosaic),
            }))
            attempt = root / "a3"
            with (mock.patch.object(runner, "DATA_ROOT", root),
                  mock.patch.object(runner, "ATTEMPT_ROOT", attempt),
                  mock.patch.object(runner, "MOSAIC", mosaic),
                  mock.patch.object(runner, "PREFLIGHT", preflight),
                  mock.patch.object(runner, "IMPLEMENTATION_GATE", gate),
                  mock.patch.object(runner, "EXECUTION_GATE", execution),
                  mock.patch.object(runner, "DEM_ASSESSMENT", assessment),
                  mock.patch.object(runner.subprocess, "Popen", return_value=FailedChild())):
                result = runner.run_supervised()
            self.assertEqual(result["worker_return_code"], 21)
            self.assertGreater((attempt / "terminal.json").stat().st_size, 0)
            self.assertGreater((attempt / "cleanup.json").stat().st_size, 0)
            self.assertFalse(result["worker_terminal_receipt_written"])

    def test_dem_assessment_reserves_and_persists_block_before_radar(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gate = root / "implementation.json"
            gate.write_text("{}")
            execution = root / "execution.json"
            execution.write_text("{}")
            preflight = root / "preflight.json"
            preflight.write_text(__import__("json").dumps({
                "status": "pass_final_no_content_two_source_radar_preflight",
                "implementation_gate_sha256": runner.sha256_file(gate),
                "execution_gate_sha256": runner.sha256_file(execution),
            }))
            assessment = root / "assessment.json"
            with (mock.patch.object(runner, "PREFLIGHT", preflight),
                  mock.patch.object(runner, "IMPLEMENTATION_GATE", gate),
                  mock.patch.object(runner, "EXECUTION_GATE", execution),
                  mock.patch.object(runner, "DEM_ASSESSMENT", assessment),
                  mock.patch.object(runner, "ATTEMPT_ROOT", root / "absent-a3"),
                  mock.patch.object(runner, "DATA_ROOT", root),
                  mock.patch.object(runner, "event_plan", side_effect=runner.IntakeError("synthetic_stop"))):
                result = runner.run_dem_assessment()
            self.assertEqual(result["status"], "block_dem_assessment_no_radar_attempt")
            self.assertGreater(assessment.stat().st_size, 0)
            self.assertFalse(result["radar_geoprocessing_started"])

    def test_no_content_preflight_requires_exact_disposable_and_public_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            safe = root / "source.safe"
            safe.mkdir()
            orbit = root / "orbit.EOF"
            orbit.write_bytes(b"generated")
            mosaic = root / "mosaic.tif"
            mosaic.write_bytes(b"generated")
            disposable = root / "disposable.json"
            disposable.write_text(__import__("json").dumps({
                "status": "pass_disposable_grid_and_sampled_pixels_only",
                "attempt_terminal_sha256": "generated-terminal-hash",
            }))
            gate = root / "implementation.json"
            gate.write_text(__import__("json").dumps({
                "status": "pass_public_ci_map_route_implementation",
                "runner_sha256": runner.sha256_file(Path(runner.__file__)),
                "processor_sha256": runner.sha256_file(Path(__file__).resolve().parents[1] / "scripts/m2_map_route_feasibility_001_processing.py"),
                "core_sha256": runner.sha256_file(Path(__file__).resolve().parents[1] / "scripts/m2_map_route_feasibility_001_core.py"),
                "disposable_receipt_sha256": runner.sha256_file(disposable),
                "disposable_terminal_sha256": "generated-terminal-hash",
                "footprint_gate_sha256": runner.sha256_file(runner.FOOTPRINT_GATE),
            }))
            execution = root / "execution.json"
            execution.write_text(__import__("json").dumps({
                "status": "pass_public_ci_map_route_execution_gate",
                "implementation_gate_sha256": runner.sha256_file(gate),
            }))
            plan = {"sources": [{"safe_root": str(safe)}],
                    "orbits": {"M2-ORB-001": {"custody_path": str(orbit)}}}
            arcpy = SimpleNamespace(CheckExtension=lambda _: "Available",
                                    GetInstallInfo=lambda: {"Version": "synthetic"})
            with (mock.patch.object(runner, "IMPLEMENTATION_GATE", gate),
                  mock.patch.object(runner, "EXECUTION_GATE", execution),
                  mock.patch.object(runner, "DISPOSABLE_RECEIPT", disposable),
                  mock.patch.object(runner, "PREFLIGHT", root / "absent-preflight.json"),
                  mock.patch.object(runner, "DEM_ASSESSMENT", root / "absent-assessment.json"),
                  mock.patch.object(runner, "ATTEMPT_ROOT", root / "absent-a3"),
                  mock.patch.object(runner, "DATA_ROOT", root),
                  mock.patch.object(runner, "MOSAIC", mosaic),
                  mock.patch.object(runner, "event_plan", return_value=plan),
                  mock.patch.object(runner, "projected_paths", return_value={"projected_path_count": 1}),
                  mock.patch.object(runner, "arcgis_signature_status", return_value={"all_match": True}),
                  mock.patch.object(runner.shutil, "disk_usage", return_value=SimpleNamespace(free=100 * 1024**3))):
                self.assertEqual(runner.no_content_preflight(arcpy)["status"],
                                 "pass_final_no_content_two_source_radar_preflight")
                execution.write_text('{"status":"pending"}')
                with self.assertRaisesRegex(Exception, "event_pair_radar_public_implementation_gate_missing"):
                    runner.no_content_preflight(arcpy)

    def test_sampled_clip_comparison_stops_on_pixel_change(self):
        class Window:
            shape = (128, 128)

            def __init__(self, value):
                self.value = value

        class RasterRead:
            Point = staticmethod(lambda x, y: (x, y))

            def __init__(self, changed=False):
                self.changed = changed

            def RasterToNumPyArray(self, path, **_):
                return Window(2 if self.changed and path == "final" else 1)

        arrays = SimpleNamespace(array_equal=lambda a, b: a.value == b.value)
        result = compare_retained_windows(RasterRead(), arrays, Path("middle"),
                                          Path("final"), categorical=False)
        self.assertEqual(len(result["windows"]), 3)
        with self.assertRaisesRegex(MapRouteStop, "sampled_retained_pixels_changed"):
            compare_retained_windows(RasterRead(changed=True), arrays,
                                     Path("middle"), Path("final"), categorical=True)

    def test_timestamp_survives_arcgis_global_datetime_rebinding(self):
        for module in (validator, crf_validator, resource_validator):
            with self.subTest(module=module.__name__), mock.patch.object(module, "datetime", datetime, create=True):
                self.assertRegex(module.now_utc(), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_import_failure_persists_distinct_terminal_and_public_block(self):
        for module in (validator, crf_validator, resource_validator):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                attempt = root / "disposable"
                public = root / "public.json"
                with (mock.patch.object(module, "ATTEMPT", attempt),
                      mock.patch.object(module, "PUBLIC_RECEIPT", public),
                      mock.patch.object(module, "check_packet_gate"),
                      mock.patch.dict(sys.modules, {"arcpy": None})):
                    terminal = module.run()
                self.assertEqual(terminal["status"], "block_disposable_no_real_attempt")
                self.assertGreater((attempt / "terminal.json").stat().st_size, 0)
                self.assertEqual(module.sha(attempt / "terminal.json"),
                                 __import__("json").loads(public.read_text())["attempt_terminal_sha256"])
                self.assertFalse(terminal["project_data_or_external_custody_accessed"])

    def test_observed_83m_cell_coverage_is_within_new_intermediate_cap(self):
        result = check_intermediate(grid(INTERMEDIATE), expected_bands=2)
        self.assertEqual(result["cells"], 83_107_486)
        self.assertEqual(result["extension_each_side_m"], [1550.0, 1440.0, 950.0, 1510.0])

    def test_missing_boundary_large_extension_and_resource_drifts_stop(self):
        cases = [
            (grid((273200.0, TARGET[1], TARGET[2], TARGET[3])), "intermediate_does_not_cover_frozen_target"),
            (grid((TARGET[0] - 2010, TARGET[1], TARGET[2], TARGET[3])), "intermediate_extension_above_2000_m"),
            (grid((TARGET[0] - 10000, TARGET[1] - 10000, TARGET[2] + 10000, TARGET[3] + 10000)), "intermediate_cell_ceiling_exceeded"),
            (grid((TARGET[0] - 5, TARGET[1], TARGET[2] - 5, TARGET[3])), "grid_snap_alignment_missing"),
        ]
        for info, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(MapRouteStop, code):
                check_intermediate(info, expected_bands=2)

    def test_final_requires_exact_frozen_grid_and_bands(self):
        self.assertTrue(check_final(grid(TARGET), expected_bands=2)["exact_frozen_grid"])
        for info in (grid((TARGET[0] + 10, TARGET[1], TARGET[2] + 10, TARGET[3])),
                     grid(TARGET, bands=1)):
            with self.assertRaises(MapRouteStop):
                check_final(info, expected_bands=2)

    def test_one_project_one_no_maintain_clip_and_stop_before_clip_on_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = FakeArcPy()
            result = project_then_clip(fake, root / "native.tif", root / "intermediate.tif",
                                       root / "final.tif", root / "snap.tif", categorical=False,
                                       expected_bands=2)
            self.assertEqual(result["resampling"], "BILINEAR")
            self.assertTrue(result["final"]["exact_frozen_grid"])
            self.assertEqual([call[0] for call in fake.calls if call[0] in {"project", "clip"}],
                             ["project", "clip"])
            self.assertEqual([call for call in fake.calls if call[0] == "clip"][0][-1],
                             "NO_MAINTAIN_EXTENT")
            failed = FakeArcPy((273200.0, TARGET[1], TARGET[2], TARGET[3]))
            with self.assertRaisesRegex(MapRouteStop, "intermediate_does_not_cover_frozen_target"):
                project_then_clip(failed, root / "native.tif", root / "gap.tif",
                                  root / "must_not_exist.tif", root / "snap.tif", categorical=True,
                                  expected_bands=2)
            self.assertFalse((root / "must_not_exist.tif").exists())
            self.assertEqual([call[0] for call in failed.calls if call[0] in {"project", "clip"}],
                             ["project"])
            stages = []

            def before(stage):
                stages.append(stage)
                if stage == "Clip":
                    raise MapRouteStop("synthetic_space_stop")

            guarded = FakeArcPy()
            with self.assertRaisesRegex(MapRouteStop, "synthetic_space_stop"):
                project_then_clip(guarded, root / "native.tif", root / "guarded_middle.tif",
                                  root / "guarded_final.tif", root / "snap.tif",
                                  categorical=False, expected_bands=2,
                                  before_materialization=before)
            self.assertEqual(stages, ["ProjectRaster", "Clip"])
            self.assertFalse((root / "guarded_final.tif").exists())


if __name__ == "__main__":
    unittest.main()
