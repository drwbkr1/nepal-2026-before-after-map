#!/usr/bin/env python3
"""Check metadata-only ArcPy calls on six disposable TIFFs."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image

from m2_radar_gtc_input_compatibility_diagnostic_001 import inspect_candidates


def main() -> int:
    import arcpy

    with tempfile.TemporaryDirectory(prefix="gtc-metadata-synthetic-") as temporary:
        paths = []
        for index in range(6):
            path = Path(temporary) / f"candidate-{index}.tif"
            Image.new("F", (2, 2), 1.0).save(path, format="TIFF")
            paths.append(path)
        observations, comparisons = inspect_candidates(arcpy, tuple(paths))
        result = {
            "status": "pass_six_disposable_metadata_descriptions" if len(observations) == 6 else "block_synthetic_metadata",
            "observed_count": len(observations),
            "arcgis_exists_all": all(item["arcgis_exists"] for item in observations),
            "band_counts": [item["describe"]["bandCount"] for item in observations],
            "structural_comparisons": comparisons,
            "geoprocessing_called": False,
            "pixel_data_read": False,
        }
        print(json.dumps(result, indent=2))
        return 0 if result["status"].startswith("pass_") else 12


if __name__ == "__main__":
    raise SystemExit(main())
