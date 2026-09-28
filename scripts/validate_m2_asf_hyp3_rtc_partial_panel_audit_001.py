#!/usr/bin/env python3
"""Disposable installed-ArcGIS audit of a saved and reopened partial panel."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from m2_asf_hyp3_rtc_partial_pair_map_001 import build_local_panel
from validate_m2_asf_hyp3_rtc_partial_pair_arcgis_synthetic_001 import _generated_tif


ROOT = Path(__file__).resolve().parents[1]


def validate() -> dict:
    import arcpy

    with tempfile.TemporaryDirectory(prefix="nepal-rtc-panel-audit-") as temp:
        root = Path(temp)
        before, after = root / "before.tif", root / "after.tif"
        values = np.full((64, 64), -12.0, dtype=np.float32)
        values[:8, :] = np.nan
        _generated_tif(before, values)
        _generated_tif(after, values + 1)
        output = root / "panel"
        build_local_panel(
            before, after, output,
            common_valid_by_aoi={"AOI-SOURCE": .55, "AOI-UPPER-CORRIDOR": .74},
            credits_and_dois="Synthetic ASF/ESA credit | https://doi.org/10.5281/zenodo.4646138",
        )
        command = [sys.executable, "-c",
                   "import json,sys; sys.path.insert(0,'scripts'); from pathlib import Path; "
                   "from m2_asf_hyp3_rtc_partial_pair_map_001 import verify_fresh_reopen; "
                   "from m2_asf_hyp3_rtc_partial_panel_audit_001 import audit_saved_panel; "
                   "reopen=verify_fresh_reopen(Path(sys.argv[1])); "
                   "audit=audit_saved_panel(Path(sys.argv[1])); "
                   "print(json.dumps({'reopen':reopen,'audit':audit}))", str(output)]
        process = subprocess.run(command, cwd=ROOT, capture_output=True,
                                 text=True, timeout=120, check=False)
        if process.returncode != 0:
            raise RuntimeError("partial_panel_fresh_process_invalid: "
                               + process.stderr[-1200:])
        receipts = json.loads(process.stdout)
        audit = receipts["audit"]
        if (receipts["reopen"]["status"] != "pass_local_arcgis_fresh_reopen_export"
                or audit["status"] != "pass_local_partial_panel_artifact_audit_only"
                or audit["broken_layers"] != 0
                or audit["warning_coverage_and_credits_present"] is not True):
            raise RuntimeError("partial_panel_audit_invalid")
        return {"status": "pass_disposable_panel_handoff_audit",
                "arcgis_version": arcpy.GetInstallInfo()["Version"],
                "map_count": audit["map_count"], "broken_layers": 0,
                "project_or_provider_data_read": False,
                "network_or_credential_action": False,
                "scientific_admission": False}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
