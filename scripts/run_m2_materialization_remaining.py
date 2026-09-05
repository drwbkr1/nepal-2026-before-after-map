#!/usr/bin/env python3
"""Run the five exact approved materializations once each in fixed order."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

from m2_materialization_remaining_core import (
    ATTEMPT_IDS,
    FINAL_PREFLIGHT_REF,
    ROOT,
    SOURCE_ORDER,
    attempt_root,
    load,
    observe_preflight,
    receipt_ref,
    validate_preflight,
    validate_static_authority,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Required explicit execution switch.")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("refusing without --execute")
    validate_static_authority(require_publication_gate=True)
    preflight = load(FINAL_PREFLIGHT_REF)
    validate_preflight(preflight)
    # Repeat every live read-only observation immediately before the first
    # extraction. A drifted archive, receipt, path, or free-space state stops.
    live = observe_preflight(utc_now(), require_publication_gate=True)
    if [item["archive_sha256"] for item in live["planned_sources"]] != [item["archive_sha256"] for item in preflight["planned_sources"]]:
        raise SystemExit("archive identity changed after final preflight")
    results = []
    for source_id in SOURCE_ORDER:
        if attempt_root(source_id).exists() or (ROOT / receipt_ref(source_id)).exists():
            raise SystemExit(f"refusing materialization collision before {source_id}")
        command = [
            sys.executable,
            str(ROOT / "scripts" / "materialize_m2_product.py"),
            "--source-id",
            source_id,
            "--attempt-id",
            ATTEMPT_IDS[source_id],
            "--started-at-utc",
            utc_now(),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)
        public_result = {"source_id": source_id, "returncode": completed.returncode}
        if completed.returncode != 0:
            print(json.dumps({"status": "stopped_on_first_failure", "result": public_result, "completed": results}, indent=2))
            return completed.returncode or 20
        receipt = load(receipt_ref(source_id))
        if receipt.get("status") != "pass_materialization_only" or receipt.get("source_id") != source_id or receipt.get("attempt_id") != ATTEMPT_IDS[source_id]:
            print(json.dumps({"status": "stopped_on_first_failure", "result": public_result, "code": "receipt_not_passing_exact_identity", "completed": results}, indent=2))
            return 20
        results.append({"source_id": source_id, "attempt_id": ATTEMPT_IDS[source_id], "status": receipt["status"]})
        print(json.dumps({"status": "source_materialized", "source_id": source_id, "completed_count": len(results)}), flush=True)
    print(json.dumps({"status": "pass_all_five_materialized", "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
