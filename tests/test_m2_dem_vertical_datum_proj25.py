from __future__ import annotations

import hashlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_dem_vertical_datum_proj25_core import (  # noqa: E402
    EXPECTED_GRID_COPYRIGHT,
    EXPECTED_GRID_DESCRIPTION,
    EXPECTED_GRID_SHA256,
    SOURCE_ORDER,
    controlled_path,
    direction_residual,
    ellipsoidal_height,
    load_contract,
    promote_no_replace,
    stream_to_exclusive_staging,
    validate_grid_metadata,
    vertical_pipeline,
)
from convert_m2_dem_vertical_datum_proj25 import output_extent, same_geotransform  # noqa: E402


class DemVerticalDatumProj25Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (ROOT / "scratch").mkdir(parents=True, exist_ok=True)

    def test_contract_freezes_exact_grid_and_four_source_order(self) -> None:
        contract = load_contract()
        self.assertEqual(contract["grid"]["expected_sha256"], EXPECTED_GRID_SHA256)
        self.assertEqual([item["source_id"] for item in contract["dem_sources_in_exact_order"]], SOURCE_ORDER)
        self.assertFalse(contract["grid"]["resume"])
        self.assertFalse(contract["grid"]["automatic_retry"])
        self.assertEqual(contract["grid"]["maximum_requests"], 1)
        self.assertEqual(contract["metadata_recovery"]["network_requests"], 0)
        self.assertEqual(contract["metadata_recovery"]["maximum_offline_verification_attempts"], 1)
        self.assertEqual(contract["conversion"]["maximum_attempts_per_dem"], 1)
        self.assertTrue(contract["conversion"]["stop_on_first_failure"])

    def test_publication_gate_releases_only_final_preflight_and_control_checkpoint(self) -> None:
        gate = __import__("json").loads(
            (ROOT / "records/readiness/m2-dem-vertical-datum-proj25-implementation-publication-gate.json").read_text(encoding="utf-8")
        )
        reconciliation = __import__("json").loads(
            (ROOT / "records/readiness/m2-dem-vertical-datum-proj25-publication-reconciliation.json").read_text(encoding="utf-8")
        )
        profile = __import__("json").loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(gate["implementation_commit"], "961d58ec8b7099df6f68705ec3c22ee53894cd91")
        self.assertEqual(gate["public_ci_run_id"], 35300447490)
        self.assertEqual(gate["public_ci_conclusion"], "success")
        self.assertFalse(gate["assertions"]["grid_request_performed"])
        self.assertFalse(gate["assertions"]["dem_pixels_read"])
        self.assertEqual(reconciliation["status"], "pass_public_gate_final_no_payload_preflight_ready")
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], "M2-DEM-PROJ25-RECEIPT-PERSISTENCE-RECOVERY-002-REVIEW-PUBLICATION")

    def test_controlled_paths_reject_traversal_and_absolute_paths(self) -> None:
        for unsafe in ("../escape.tif", "/absolute.tif", "a/../../escape.tif"):
            with self.assertRaises(ValueError):
                controlled_path(unsafe)

    def test_pipeline_is_explicit_local_inverse_vertical_shift(self) -> None:
        pipeline = vertical_pipeline(Path(r"C:\safe\us_nga_egm08_25.tif"))
        self.assertIn("+inv +proj=vgridshift", pipeline)
        self.assertIn("+multiplier=1", pipeline)
        self.assertIn("+xy_in=deg +xy_out=rad", pipeline)
        self.assertIn("+xy_in=rad +xy_out=deg", pipeline)
        self.assertNotIn("@", pipeline)
        self.assertNotIn("http", pipeline)

    def test_height_relation_and_direction_residual(self) -> None:
        self.assertAlmostEqual(ellipsoidal_height(1000.0, 42.75), 1042.75)
        self.assertEqual(direction_residual(1000.0, 42.75, 1042.75), 0.0)
        self.assertGreater(direction_residual(1000.0, 42.75, 957.25), 80.0)

    def test_grid_metadata_is_exactly_constrained(self) -> None:
        metadata = {"driver": "GTiff", "band_count": 1, "width": 8640, "height": 4321,
                    "world_coverage": True, "source_crs": None, "target_crs": None,
                    "tiff_tag_imagedescription": EXPECTED_GRID_DESCRIPTION,
                    "target_crs_epsg_code": "3855",
                    "type": "VERTICAL_OFFSET_GEOGRAPHIC_TO_VERTICAL", "area_of_use": "World",
                    "area_or_point": "Point", "tiff_tag_copyright": EXPECTED_GRID_COPYRIGHT}
        validate_grid_metadata(metadata)
        for key, bad in (("driver", "VRT"), ("band_count", 2), ("world_coverage", False),
                         ("tiff_tag_imagedescription", EXPECTED_GRID_DESCRIPTION.replace("3855", "5773")),
                         ("target_crs_epsg_code", "5773"), ("tiff_tag_copyright", "unknown")):
            changed = dict(metadata); changed[key] = bad
            with self.assertRaises(ValueError):
                validate_grid_metadata(changed)

    def test_generic_crs_keys_do_not_substitute_for_the_exact_official_representation(self) -> None:
        metadata = {"driver": "GTiff", "band_count": 1, "width": 8640, "height": 4321,
                    "world_coverage": True, "source_crs": "EPSG:4979", "target_crs": "EPSG:3855",
                    "type": "VERTICAL_OFFSET_GEOGRAPHIC_TO_VERTICAL", "area_of_use": "World",
                    "area_or_point": "Point", "tiff_tag_copyright": EXPECTED_GRID_COPYRIGHT}
        with self.assertRaises(ValueError):
            validate_grid_metadata(metadata)

    def test_stream_is_exclusive_and_preserves_interrupted_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            staging = Path(temporary) / "one" / "grid.part"
            observed = stream_to_exclusive_staging(io.BytesIO(b"abc"), staging, 3)
            self.assertEqual(observed["size_bytes"], 3)
            self.assertEqual(staging.read_bytes(), b"abc")
            with self.assertRaises(FileExistsError):
                stream_to_exclusive_staging(io.BytesIO(b"new"), staging, 3)

    def test_conversion_grid_geometry_is_exact_and_north_up_only(self) -> None:
        transform = (84.0, 1.0 / 3600.0, 0.0, 29.0, 0.0, -1.0 / 3600.0)
        self.assertEqual(output_extent(transform, 3600, 3600), (84.0, 28.0, 85.0, 29.0))
        self.assertTrue(same_geotransform(transform, tuple(transform)))
        changed = list(transform); changed[1] += 1e-8
        self.assertFalse(same_geotransform(transform, tuple(changed)))
        with self.assertRaises(ValueError):
            output_extent((84.0, 1.0, 0.1, 29.0, 0.0, -1.0), 1, 1)

    def test_real_scripts_are_no_network_conversion_and_anonymous_grid_only(self) -> None:
        acquisition = (ROOT / "scripts/acquire_m2_dem_vertical_grid_proj25.py").read_text(encoding="utf-8")
        conversion = (ROOT / "scripts/convert_m2_dem_vertical_datum_proj25.py").read_text(encoding="utf-8")
        self.assertNotIn("Authorization", acquisition)
        self.assertNotIn("token", acquisition.casefold())
        self.assertIn("NoRedirectHandler", acquisition)
        self.assertIn('os.environ["PROJ_NETWORK"] = "OFF"', conversion)
        self.assertIn("stop", conversion.casefold())

    def test_metadata_recovery_scripts_have_no_network_client_or_payload_route(self) -> None:
        recovery = (ROOT / "scripts/recover_m2_dem_vertical_grid_proj25_metadata_001.py").read_text(encoding="utf-8")
        preflight = (ROOT / "scripts/preflight_m2_dem_vertical_datum_proj25_metadata_recovery_001.py").read_text(encoding="utf-8")
        for source in (recovery, preflight):
            folded = source.casefold()
            self.assertNotIn("urllib", folded)
            self.assertNotIn("requests.", folded)
            self.assertNotIn("http://", folded)
            self.assertNotIn("https://", folded)
        self.assertIn('"network_request_count": 0', recovery)
        self.assertIn('"preserved_content_bytes_read": 0', preflight)

    def test_promotion_is_no_replace_and_preserves_staged_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            base = Path(temporary)
            staged, destination = base / "grid.part", base / "custody" / "grid.tif"
            payload = b"synthetic-grid-bytes"
            staged.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            result = promote_no_replace(staged, destination, len(payload), digest)
            self.assertEqual(result["sha256"], digest)
            self.assertEqual(staged.read_bytes(), payload)
            with self.assertRaises(FileExistsError):
                promote_no_replace(staged, destination, len(payload), digest)

    def test_partial_or_wrong_bytes_fail_without_deletion_or_promotion(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            base = Path(temporary)
            staged, destination = base / "interrupted.part", base / "grid.tif"
            staged.write_bytes(b"partial")
            with self.assertRaises(ValueError):
                promote_no_replace(staged, destination, 99, "0" * 64)
            self.assertTrue(staged.exists())
            self.assertFalse(destination.exists())

    def test_source_file_snapshot_is_unchanged_by_destination_failure(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            base = Path(temporary)
            source, destination = base / "source.tif", base / "destination.tif"
            source.write_bytes(b"immutable-source")
            before = (source.stat().st_size, hashlib.sha256(source.read_bytes()).hexdigest())
            destination.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                promote_no_replace(source, destination, before[0], before[1])
            after = (source.stat().st_size, hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(after, before)


if __name__ == "__main__":
    os.makedirs(ROOT / "scratch", exist_ok=True)
    unittest.main()
