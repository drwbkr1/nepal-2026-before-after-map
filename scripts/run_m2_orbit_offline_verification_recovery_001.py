#!/usr/bin/env python3
"""Run the approved orbit-verification recovery sequence once in exact order."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from verify_m2_orbit_eof_recovery_001 import OUTPUT_REFS, ROOT, SOURCE_IDS, execute


Invoke = Callable[[str], tuple[int, dict[str, Any]]]


def run_sequence(invoke: Invoke) -> tuple[int, dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for source_id in SOURCE_IDS:
        code, result = invoke(source_id)
        results.append({"source_id": source_id, "return_code": code, "result": result})
        if code != 0 or result.get("status") != "pass_orbit_input_only":
            return code if code != 0 else 2, {
                "status": "stopped_on_first_failure",
                "source_ids_in_exact_order": SOURCE_IDS,
                "completed_source_ids": [item["source_id"] for item in results[:-1]],
                "stopped_source_id": source_id,
                "results": results,
                "automatic_retry_performed": False,
            }
    return 0, {
        "status": "pass_all_four_exact_orbit_inputs_only",
        "source_ids_in_exact_order": SOURCE_IDS,
        "completed_source_ids": SOURCE_IDS,
        "results": results,
        "automatic_retry_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--custody-root", type=Path, required=True)
    args = parser.parse_args()

    def invoke(source_id: str) -> tuple[int, dict[str, Any]]:
        return execute(source_id, args.custody_root, ROOT / OUTPUT_REFS[source_id])

    code, result = run_sequence(invoke)
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
