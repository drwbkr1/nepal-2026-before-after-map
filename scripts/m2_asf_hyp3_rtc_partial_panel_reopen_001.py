#!/usr/bin/env python3
"""Fresh ArcGIS process for the approved local partial panel export audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from m2_asf_hyp3_rtc_partial_pair_map_001 import verify_fresh_reopen
from m2_asf_hyp3_rtc_partial_panel_audit_001 import audit_saved_panel


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"status": "stopped", "code": "partial_panel_reopen_argument_invalid"}))
        return 12
    try:
        output = Path(sys.argv[1])
        reopened = verify_fresh_reopen(output)
        audited = audit_saved_panel(output)
        if (reopened.get("status") != "pass_local_arcgis_fresh_reopen_export"
                or audited.get("status") != "pass_local_partial_panel_artifact_audit_only"):
            raise ValueError("partial_panel_reopen_or_audit_failed")
        print(json.dumps({"status": "pass_local_partial_panel_fresh_reopen_and_audit",
                          "reopen": reopened, "audit": audited}, sort_keys=True))
        return 0
    except BaseException:
        print(json.dumps({"status": "stopped",
                          "code": "partial_panel_reopen_or_audit_failed"}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
