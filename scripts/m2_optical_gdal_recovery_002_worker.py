#!/usr/bin/env python3
"""One offline GDAL child; no ArcPy, network, credentials, or retries."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = ROOT.parent / f"{ROOT.name}-data" / "derived/m2-optical-gdal-header-pixel-recovery-002/real-001"


def utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def marker(name: str, value: dict[str, Any]) -> None:
    with (ATTEMPT / name).open("xb") as stream:
        stream.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def safe_error(exc: BaseException) -> dict[str, str | None]:
    allowed = {"PilotControlError", "OSError", "FileNotFoundError", "PermissionError",
               "ImportError", "ModuleNotFoundError", "RuntimeError", "ValueError",
               "TypeError", "AttributeError", "KeyError", "MemoryError", "Exception"}
    kind = type(exc).__name__
    code = getattr(exc, "code", None)
    return {"error_class": kind if kind in allowed else "unclassified_error",
            "safe_code": code if kind == "PilotControlError" and isinstance(code, str)
                         and re.fullmatch(r"[a-z0-9_]{3,96}", code) else None}


def main() -> int:
    stage = "child_bootstrap"
    terminal: dict[str, Any] = {
        "schema_version": "1.0", "status": "stopped", "stage": stage,
        "completed_at_utc": None, "exception_text_recorded": False,
        "network_or_credential_action": False, "automatic_retry": False,
        "arcpy_imported": False, "baseline_or_change_analysis": False,
    }
    try:
        if sys.argv[1:] != ["--real"] or not ATTEMPT.is_dir():
            return 12
        for name in ("started.json", "terminal-reserved.json", "cleanup-reserved.json"):
            if not (ATTEMPT / name).is_file():
                return 12
        marker("child-started.json", {"status": "started", "at_utc": utc()})
        stage = "project_imports"
        from m2_optical_gdal_recovery_002_core import (  # noqa: PLC0415
            HEADER_RECEIPT, PIXEL_RECEIPT, exact_sources, read_json,
            require_execution_release, sha256_file, write_new_json,
        )
        from m2_optical_gdal_recovery_002_engine import inspect_pair, qa_pair  # noqa: PLC0415

        if "arcpy" in sys.modules:
            raise RuntimeError("gdal_real_worker_arcpy_imported")

        marker("imports-complete.json", {"status": "complete", "at_utc": utc()})
        stage = "execution_release"
        require_execution_release()
        marker("release-checked.json", {"status": "pass", "at_utc": utc()})
        stage = "gdal_import"
        marker("gdal-import-started.json", {"status": "started", "at_utc": utc()})
        from osgeo import gdal  # type: ignore[import-not-found]  # noqa: PLC0415

        gdal.SetConfigOption("PROJ_NETWORK", "OFF")
        gdal.SetConfigOption("GDAL_PAM_ENABLED", "NO")
        marker("gdal-import-complete.json", {"status": "complete", "at_utc": utc()})
        sources = exact_sources()
        stage = "header"
        marker("header-started.json", {"status": "started", "at_utc": utc(),
                                       "source_ids_in_order": ["M2-OPT-001", "M2-OPT-002"]})
        header, paths = inspect_pair(sources)
        write_new_json(HEADER_RECEIPT, header)
        marker("header-complete.json", {"status": header["status"], "at_utc": utc(),
                                        "header_sha256": sha256_file(HEADER_RECEIPT)})
        terminal["header_status"] = header["status"]
        if header["status"] != "pass_header_readability_only":
            return 20
        stage = "pixel_qa"
        marker("pixel-started.json", {"status": "started", "at_utc": utc(),
                                      "header_sha256": sha256_file(HEADER_RECEIPT)})
        pixel = qa_pair(paths, header)
        if "arcpy" in sys.modules:
            raise RuntimeError("gdal_real_worker_arcpy_imported")
        write_new_json(PIXEL_RECEIPT, pixel)
        marker("pixel-complete.json", {"status": pixel["status"], "at_utc": utc(),
                                       "pixel_receipt_sha256": sha256_file(PIXEL_RECEIPT)})
        terminal.update({"status": "completed_qa_evaluation", "stage": "pixel_qa",
                         "pixel_status": pixel["status"]})
        return 0
    except BaseException as exc:
        terminal.update({"status": "stopped", "stage": stage, **safe_error(exc)})
        return 20
    finally:
        terminal["completed_at_utc"] = utc()
        try:
            if ATTEMPT.is_dir() and not (ATTEMPT / "worker-terminal.json").exists():
                marker("worker-terminal.json", terminal)
        except BaseException:
            # The parent reserved a separate terminal identity before this child.
            pass


if __name__ == "__main__":
    raise SystemExit(main())
