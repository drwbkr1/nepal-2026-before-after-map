#!/usr/bin/env python3
"""Write the one final no-mutation preflight for five approved materializations."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from m2_materialization_remaining_core import FINAL_PREFLIGHT_REF, ROOT, observe_preflight, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", required=True)
    args = parser.parse_args()
    if not args.observed_at_utc.endswith("Z"):
        raise SystemExit("observed time must be UTC")
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise SystemExit("refusing final-preflight output collision")
    record = observe_preflight(args.observed_at_utc, require_publication_gate=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": record["status"], "output": FINAL_PREFLIGHT_REF, "sha256": sha256_file(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
