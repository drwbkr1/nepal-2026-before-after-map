"""Portable handoff-audit guards; all data and ArcGIS objects are disposable."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m2_asf_hyp3_rtc_partial_panel_audit_001 import (  # noqa: E402
    AFTER_LABEL, APRX, BEFORE_LABEL, PNG_FILES, RASTERS, WARNING,
    _png_size, audit_saved_panel,
)


def _png(path: Path) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR"
                     + struct.pack(">II", 1950, 1125))


class FakeMap:
    def __init__(self, name: str, source: Path):
        self.name = name
        self.spatialReference = SimpleNamespace(factoryCode=32645)
        self._layer = SimpleNamespace(isBroken=False, dataSource=str(source),
                                      supports=lambda value: value == "DATASOURCE")

    def listLayers(self):
        return [self._layer]


class FakeLayout:
    def __init__(self, *, warning: str = WARNING, credits: str | None = None):
        coverage = ("Common valid VV/VH: source 55.0%; upper corridor 74.0%. "
                    "Blank areas exclude layover, shadow or NoData.")
        values = {
            "before label": BEFORE_LABEL, "after label": AFTER_LABEL,
            "Title": "Nepal 2026 | EPSG:32645 | ASF RTC gamma0 dB",
            "Coverage": coverage, "Partial-data warning": warning,
            "Credits and DOIs": credits or "ASF/ESA | https://doi.org/10.5281/test",
        }
        self._elements = [SimpleNamespace(name=name, text=text)
                          for name, text in values.items()]

    def listElements(self, kind: str):
        assert kind == "TEXT_ELEMENT"
        return self._elements


class FakeArcpy:
    def __init__(self, output: Path, *, warning: str = WARNING,
                 changed_path: bool = False):
        maps = [FakeMap(label, output / filename)
                for label, filename in RASTERS.items()]
        if changed_path:
            maps[1]._layer.dataSource = str(output.parent / "other.tif")
        layout = FakeLayout(warning=warning)
        project = SimpleNamespace(listMaps=lambda: maps,
                                  listLayouts=lambda: [layout])
        self.mp = SimpleNamespace(ArcGISProject=lambda path: project)


class PanelAuditTests(unittest.TestCase):
    def fixture(self, output: Path) -> None:
        output.mkdir()
        for name in RASTERS.values():
            (output / name).write_bytes(name.encode("ascii"))
        for name in PNG_FILES:
            _png(output / name)
        (output / APRX).write_bytes(b"disposable project")
        hashes = [hashlib.sha256((output / name).read_bytes()).hexdigest()
                  for name in RASTERS.values()]
        project_hash = hashlib.sha256((output / APRX).read_bytes()).hexdigest()
        png_hash = hashlib.sha256((output / PNG_FILES[0]).read_bytes()).hexdigest()
        (output / "build.json").write_text(json.dumps({
            "status": "built_local_partial_visual_pending_fresh_reopen",
            "wkid": 32645, "staged_sha256": hashes,
            "aprx_sha256": project_hash, "first_png_sha256": png_hash,
            "common_valid_by_aoi": {"AOI-SOURCE": .55,
                                    "AOI-UPPER-CORRIDOR": .74},
            "DEM_raster_displayed": False,
            "change_analysis_or_attribution": False,
            "public_pixel_publication": False,
        }), encoding="utf-8")

    @staticmethod
    def check_header(_arcpy, _path):
        return (64, 64, 300000.0, 3100000.0, 300640.0, 3100640.0)

    def test_pass_then_warn_on_text_and_path_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "panel"
            self.fixture(output)
            with patch("m2_asf_hyp3_rtc_partial_panel_audit_001._check_raster",
                       side_effect=self.check_header):
                result = audit_saved_panel(output, arcpy_module=FakeArcpy(output))
                self.assertTrue(result["warning_coverage_and_credits_present"])
                with self.assertRaisesRegex(ValueError, "layer_path_drift"):
                    audit_saved_panel(output, arcpy_module=FakeArcpy(
                        output, changed_path=True))
                with self.assertRaisesRegex(ValueError, "warning_or_title_drift"):
                    audit_saved_panel(output, arcpy_module=FakeArcpy(
                        output, warning="Everything is certain"))

    def test_raster_mutation_stops_before_project_open(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "panel"
            self.fixture(output)
            (output / RASTERS[BEFORE_LABEL]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "raster_hash_drift"):
                audit_saved_panel(output, arcpy_module=FakeArcpy(output))

    def test_png_header_required(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fake.png"
            path.write_bytes(b"not a PNG")
            with self.assertRaisesRegex(ValueError, "png_invalid"):
                _png_size(path)


if __name__ == "__main__":
    unittest.main()
