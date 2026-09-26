#!/usr/bin/env python3
"""One offline ArcGIS child; reserve stages before project or ArcPy imports."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
ATTEMPT = REPO.parent / f"{REPO.name}-data" / "derived/m2-optical-pair-header-receipt-recovery-001/real-001"
def utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def marker(name: str, value: dict[str, Any]) -> None:
    path = ATTEMPT / name
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def safe_error(exc: BaseException) -> dict[str, str | None]:
    kind = type(exc).__name__
    code = getattr(exc, "code", None)
    allowed = {"PilotControlError", "OSError", "FileNotFoundError", "PermissionError",
               "ImportError", "ModuleNotFoundError", "RuntimeError", "ValueError",
               "TypeError", "AttributeError", "KeyError", "MemoryError", "KeyboardInterrupt",
               "SystemExit", "Exception"}
    return {
        "error_class": kind if kind in allowed else "unclassified_error",
        "safe_code": code if kind == "PilotControlError" and isinstance(code, str)
                     and re.fullmatch(r"(?:pilot|recovery)_[a-z0-9_]{3,72}", code) else None,
    }


def main() -> int:
    stage = "child_bootstrap"
    terminal: dict[str, Any] = {
        "schema_version": "1.0", "status": "stopped", "stage": stage,
        "completed_at_utc": None, "exception_text_recorded": False,
        "network_or_credential_action": False, "automatic_retry": False,
    }
    try:
        if sys.argv[1:] != ["--real"] or not ATTEMPT.is_dir():
            return 12
        marker("child-started.json", {"status": "started", "at_utc": utc(), "stage": stage})
        stage = "project_imports"
        from m2_optical_pair_header_recovery_001_core import (  # noqa: PLC0415
            HEADER_RECEIPT, PIXEL_RECEIPT, exact_sources, require_execution_release, sha256_file,
        )
        from m2_optical_pair_header_recovery_001_pixel import run_qa_pixels  # noqa: PLC0415
        from m2_optical_pair_header_recovery_001_header import inspect_recovery_headers  # noqa: PLC0415

        marker("imports-complete.json", {"status": "complete", "at_utc": utc()})
        stage = "execution_release"
        require_execution_release()
        marker("release-checked.json", {"status": "pass", "at_utc": utc()})
        stage = "arcpy_import"
        marker("arcpy-import-started.json", {"status": "started", "at_utc": utc()})
        import arcpy  # type: ignore[import-not-found]  # noqa: PLC0415

        marker("arcpy-import-complete.json", {"status": "complete", "at_utc": utc()})
        sources = exact_sources()
        stage = "header"
        marker("header-started.json", {"status": "started", "at_utc": utc(), "source_ids_in_order": ["M2-OPT-001", "M2-OPT-002"]})
        header = inspect_recovery_headers(sources, arcpy, HEADER_RECEIPT)
        marker("header-complete.json", {
            "status": header["status"], "at_utc": utc(), "header_sha256": sha256_file(HEADER_RECEIPT),
        })
        if header["status"] != "pass_header_readability_only":
            terminal.update({"stage": "header", "header_status": header["status"]})
            return 20
        stage = "pixel_qa"
        marker("pixel-started.json", {"status": "started", "at_utc": utc(), "header_sha256": sha256_file(HEADER_RECEIPT)})
        pixel = run_qa_pixels(sources, arcpy=arcpy)
        marker("pixel-complete.json", {
            "status": pixel["status"], "at_utc": utc(), "pixel_receipt_sha256": sha256_file(PIXEL_RECEIPT),
        })
        terminal.update({"status": "completed_qa_evaluation", "stage": "pixel_qa", "pixel_status": pixel["status"]})
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
            # The parent reserved a distinct terminal identity before spawning us.
            pass


if __name__ == "__main__":
    raise SystemExit(main())
