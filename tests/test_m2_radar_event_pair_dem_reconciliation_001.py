"""Synthetic terminal and byte-identity tests for seven-tile reconciliation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reconcile_m2_radar_event_pair_dem_intake_001 as route


class ReconciliationTests(unittest.TestCase):
    def test_valid_terminal_and_bytes_then_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {key: root / (key + ".json" if key in {"terminal", "error", "cleanup"} else key + ".tif") for key in ("staging", "terminal", "error", "cleanup", "destination")}
            payload = b"synthetic-data"
            paths["destination"].write_bytes(payload)
            paths["error"].write_bytes(b"")
            paths["cleanup"].write_text(json.dumps({"status": "no_cleanup_required"}), encoding="utf-8")
            terminal = {
                "status": "pass_verified_and_promoted",
                "item_id": "exact-item",
                "attempt": "attempt-001",
                "size_bytes": len(payload),
                "sha256": route.sha256(paths["destination"]),
                "geotiff": {"width": 3600, "height": 3600, "epsg": 4326, "valid_pixels": 12960000, "nonfinite_pixels": 0},
            }
            paths["terminal"].write_text(json.dumps(terminal), encoding="utf-8")
            asset = {"item_id": "exact-item", "observed_head_content_length_bytes": len(payload)}
            self.assertEqual(route.validate_tile(asset, paths)["sha256"], terminal["sha256"])
            paths["destination"].write_bytes(b"changed-data")
            with self.assertRaisesRegex(route.IntakeError, "promoted_tile_byte_identity_drift"):
                route.validate_tile(asset, paths)


if __name__ == "__main__":
    unittest.main()
