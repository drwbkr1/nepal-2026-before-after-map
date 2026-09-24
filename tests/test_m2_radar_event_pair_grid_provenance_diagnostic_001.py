"""Portable safeguards for the read-only event-pair grid diagnostic."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_radar_event_pair_grid_provenance_diagnostic_001_core as core  # noqa: E402


class FakeArcPy:
    def __init__(self, *, conflict: bool = False) -> None:
        self.conflict = conflict
        self.calls: list[tuple[str, str]] = []

    def Raster(self, path: str):
        self.calls.append(("Raster", path))
        extent = SimpleNamespace(XMin=80.0, YMin=10.0, XMax=100.0, YMax=30.0)
        return SimpleNamespace(width=2, height=2, bandCount=2, meanCellWidth=10.0,
                               meanCellHeight=10.0, spatialReference=SimpleNamespace(factoryCode=4326), extent=extent)

    def Describe(self, path: str):
        self.calls.append(("Describe", path))
        extent = SimpleNamespace(XMin=80.0, YMin=10.0, XMax=100.0, YMax=30.0)
        return SimpleNamespace(bandCount=1 if self.conflict else 2, meanCellWidth=10.0,
                               meanCellHeight=10.0, spatialReference=SimpleNamespace(factoryCode=4326), extent=extent)


class GridProvenanceDiagnosticTests(unittest.TestCase):
    def test_exact_five_names_and_path_escape_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "s" / "2"
            root.mkdir(parents=True)
            paths = core.candidate_paths(root)
            self.assertEqual(len(paths), 5)
            for item in paths:
                item.mkdir()
                core.check_candidate_path(item, root)
            with self.assertRaisesRegex(core.DiagnosticError, "candidate_path_outside_exact_allowlist"):
                core.check_candidate_path(root / ".." / "other.crf", root)

    def test_missing_input_blocks_before_arcpy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fake = FakeArcPy()
            with self.assertRaisesRegex(core.DiagnosticError, "exact_candidate_missing_or_unsafe"):
                core.inspect_raster(fake, Path(temp) / core.NAMES[0], root=Path(temp))
            self.assertEqual(fake.calls, [])

    def test_metadata_comparison_tolerates_explicit_describe_unavailable_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / core.NAMES[0]
            candidate.mkdir()
            fake = FakeArcPy()
            record = core.inspect_raster(fake, candidate, root=root)
            self.assertEqual(record["raster"]["width"], 2)
            self.assertEqual(record["describe_unavailable_fields"], ["width", "height"])
            self.assertEqual([item[0] for item in fake.calls], ["Raster", "Describe"])

    def test_metadata_conflict_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / core.NAMES[0]
            candidate.mkdir()
            with self.assertRaisesRegex(core.DiagnosticError, "raster_describe_metadata_conflict"):
                core.inspect_raster(FakeArcPy(conflict=True), candidate, root=root)

    def test_configuration_identity_exact_and_no_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "gamma0_linear_gtc_raw.crf"
            candidate.mkdir()
            config = candidate / "raster.conf"
            config.write_bytes(b"synthetic-configuration")
            expected = hashlib.sha256(config.read_bytes()).hexdigest()
            with patch.object(core, "EXPECTED_CONF_SHA256", expected):
                result = core.verify_gtc_configuration(candidate, root=root)
            self.assertEqual(result["configuration_sha256"], expected)
            self.assertEqual(config.read_bytes(), b"synthetic-configuration")
            with self.assertRaisesRegex(core.DiagnosticError, "gtc_configuration_identity_mismatch"):
                core.verify_gtc_configuration(candidate, root=root)

    def test_receipt_reservation_is_durable_and_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "terminal.json"
            stream = core.reserve(receipt)
            self.assertEqual(receipt.stat().st_size, 0)
            with self.assertRaises(FileExistsError):
                core.reserve(receipt)
            core.persist(stream, {"status": "terminal"})
            self.assertEqual(core.load_json(receipt)["status"], "terminal")
            with self.assertRaises(FileExistsError):
                core.reserve(receipt)

    def test_first_coarse_stage_is_only_metadata_classification(self) -> None:
        records = [{"name": "slant", "raster": {"wkid": 4326, "cell_size_x": 0.01, "cell_size_y": 0.01}},
                   {"name": "gtc", "raster": {"wkid": 4326, "cell_size_x": 10.0, "cell_size_y": 10.0}}]
        self.assertEqual(core.first_declared_coarse_stage(records), "gtc")


if __name__ == "__main__":
    unittest.main()
