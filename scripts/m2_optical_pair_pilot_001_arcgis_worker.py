#!/usr/bin/env python3
"""One offline ArcGIS header and conditional pixel QA attempt; no token input."""

from __future__ import annotations

import sys

from m2_optical_pair_pilot_001_core import load_contract, require_execution_release
from m2_optical_pair_pilot_001_offline import inspect_pair_headers
from m2_optical_pair_pilot_001_pixel import HEADER_RECEIPT, PUBLIC_RECEIPT, run_qa_pixels


def main() -> int:
    if not sys.stdin.closed and sys.stdin.isatty():
        return 12
    require_execution_release()
    contract = load_contract()
    if HEADER_RECEIPT.exists() or PUBLIC_RECEIPT.exists():
        return 12
    import arcpy  # type: ignore[import-not-found]

    sources = contract["sources_in_order"]
    header = inspect_pair_headers(sources, arcpy, HEADER_RECEIPT)
    if header["status"] != "pass_header_readability_only":
        return 20
    run_qa_pixels(sources, arcpy=arcpy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
