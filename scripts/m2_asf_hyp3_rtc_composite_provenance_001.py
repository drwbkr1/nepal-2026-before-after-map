#!/usr/bin/env python3
"""One append-only, receipt-only evaluation of first HyP3 RTC provenance.

No network, credential, ZIP payload, raster header, or pixel access occurs.
The old README attempt remains terminal and unchanged.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

from m2_asf_hyp3_rtc_acquire_first_001 import DATA_ROOT
from m2_asf_hyp3_rtc_composite_provenance_core_001 import (
    ARCHIVE_SHA256, ARCHIVE_SIZE, JOB_ID, PRODUCT_FILENAME, SOURCE_ID,
    evaluate_composite,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop, load_approved_jobs


PROPOSAL_REF = "contracts/milestone-002-asf-hyp3-rtc-provenance-rule-amendment-001-proposal.json"
BUNDLE_REF = "reviews/m2-asf-hyp3-rtc-provenance-rule-amendment-001/review-bundle.json"
APPROVAL_REF = "records/source-gates/m2-asf-hyp3-rtc-provenance-rule-amendment-001-approval.json"
SOURCE_GATE_REF = "records/source-gates/m2-asf-hyp3-rtc-processing-source-gate-001.json"
OLD_README_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-readme-first-implementation-gate-001.json"
OLD_TERMINAL_RECONCILIATION_REF = "records/readiness/m2-asf-hyp3-rtc-readme-first-terminal-reconciliation-001.json"
IMPLEMENTATION_GATE_REF = "records/readiness/m2-asf-hyp3-rtc-composite-provenance-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-composite-provenance-001-execution-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-composite-provenance-001" / "attempt-001"
RECEIPT_REFS = {
    "submission": "m2-asf-hyp3-rtc-submit-first-001/attempt-001/terminal.json",
    "descriptor": "m2-asf-hyp3-rtc-acquire-first-001/attempt-001/descriptor.json",
    "acquisition": "m2-asf-hyp3-rtc-acquire-first-001/attempt-001/terminal.json",
    "readme": "m2-asf-hyp3-rtc-readme-first-001/attempt-001/terminal.json",
}
HISTORICAL_CODE_HASHES = {
    "scripts/m2_asf_hyp3_rtc_job_status_core_001.py": "854db8cbb963da46b3c790814e91d9dbe309a0958a1f6e81710ad5e65c77bea7",
    "scripts/m2_asf_hyp3_rtc_download_core_001.py": "e04f8327db90392e64c4f0c7b10050cb8cb7d9a9ecc77bcec2d686b2f0aac76d",
    "scripts/m2_asf_hyp3_rtc_http_transfer_001.py": "b1f961ec0e1cf35f3066349ab7c976c0d1066bed0c0766bcdf42c1e983d70359",
    "scripts/m2_asf_hyp3_rtc_acquire_first_001.py": "5c17521e739a4a9db15d9fa01bad3f7a8f6315f21ba35f81a67df0059e40cbc8",
    "scripts/m2_asf_hyp3_rtc_transfer_core_001.py": "39388fb32297c7457686c7a1b9ac9783f9233e20a08e0343d1f03bfd51c29c4e",
    "scripts/m2_asf_hyp3_rtc_zip_core_001.py": "7338d61dbb5deb1f4bbc82a03df556e818b4c3b94f74905e2db57009aed976df",
    "scripts/m2_asf_hyp3_rtc_package_core_001.py": "9293e47889ccf6b032966c5824af43bfe1f1da5f1932d521ab4521723eb9ce7d",
    "scripts/m2_asf_hyp3_rtc_readme_core_001.py": "a2add7b7e5fb05682a18b4319214a016bd76d919e391c465f9301666c53e59d8",
    "scripts/m2_asf_hyp3_rtc_readme_first_001.py": "4db17f16cc96574cd337837901819313bca27d820d266399c660252417c751af",
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and not bool(
            getattr(path.stat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError:
        return False


def _safe_dir(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink() and not bool(
            getattr(path.stat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
    except OSError:
        return False


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RouteStop("rtc_composite_record_unavailable") from None
    if not isinstance(value, dict):
        raise RouteStop("rtc_composite_record_invalid")
    return value


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_release(
    root: Path = ROOT, data_root: Path = DATA_ROOT,
    attempt_root: Path = ATTEMPT_ROOT,
) -> tuple[dict, dict]:
    """Verify only code, receipts, path metadata, and published gates."""
    try:
        proposal = _read_json(root / PROPOSAL_REF)
        bundle = _read_json(root / BUNDLE_REF)
        approval = _read_json(root / APPROVAL_REF)
        source_gate = _read_json(root / SOURCE_GATE_REF)
        old_readme_gate = _read_json(root / OLD_README_GATE_REF)
        gate = _read_json(root / IMPLEMENTATION_GATE_REF)
        preflight = _read_json(root / PREFLIGHT_REF)
        if (
            not _safe_dir(data_root)
            or attempt_root.parent.parent.resolve() != data_root.resolve()
            or attempt_root.parent.is_symlink()
            or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
            or attempt_root.exists() or attempt_root.is_symlink()
            or approval.get("decision") != "approve"
            or approval.get("bindings", {}).get("proposal_sha256") != _sha(root / PROPOSAL_REF)
            or approval.get("bindings", {}).get("review_bundle_sha256") != _sha(root / BUNDLE_REF)
            or approval.get("bindings", {}).get("old_readme_terminal_reconciliation_sha256")
            != _sha(root / OLD_TERMINAL_RECONCILIATION_REF)
            or proposal.get("frozen_evidence", {}).get("terminal_reconciliation_sha256")
            != _sha(root / OLD_TERMINAL_RECONCILIATION_REF)
            or proposal.get("status") != "local_zero_decision_not_published_not_approved"
            or bundle.get("status") != "local_zero_decision_not_published_not_approved"
            or any(_sha(root / item["path"]) != item["sha256"] for item in bundle["artifacts"])
            or source_gate.get("decision", {}).get("status") != "ready"
            or source_gate.get("authority", {}).get("authority_ref")
            != "records/source-gates/m2-asf-hyp3-rtc-map-route-001-approval.json"
            or old_readme_gate.get("status") != "pass_readme_first_implementation_public_ci_only"
            or old_readme_gate.get("public_ci", {}).get("conclusion") != "success"
            or old_readme_gate.get("bindings", {}).get("source_gate_sha256") != _sha(root / SOURCE_GATE_REF)
            or proposal.get("readme_probe_logic_bindings", {}).get("implementation_gate_sha256")
            != _sha(root / OLD_README_GATE_REF)
            or any(
                _sha(root / ref) != proposal.get("readme_probe_logic_bindings", {}).get(key)
                for key, ref in (
                    ("readme_core_sha256", "scripts/m2_asf_hyp3_rtc_readme_core_001.py"),
                    ("readme_runner_sha256", "scripts/m2_asf_hyp3_rtc_readme_first_001.py"),
                    ("package_core_sha256", "scripts/m2_asf_hyp3_rtc_package_core_001.py"),
                )
            )
            or gate.get("status") != "pass_composite_implementation_public_ci_only"
            or gate.get("public_ci", {}).get("conclusion") != "success"
            or gate.get("bindings", {}).get("amendment_approval_sha256") != _sha(root / APPROVAL_REF)
            or preflight.get("status") != "pass_composite_no_content_preflight"
            or preflight.get("bindings", {}).get("implementation_gate_sha256")
            != _sha(root / IMPLEMENTATION_GATE_REF)
            or preflight.get("assertions", {}).get("attempt_absent") is not True
            or preflight.get("assertions", {}).get("no_product_payload_or_pixel_read") is not True
            or any(_sha(root / ref) != sha for ref, sha in HISTORICAL_CODE_HASHES.items())
        ):
            raise RouteStop("rtc_composite_not_released")
        implementation_files = gate.get("bindings", {}).get("implementation_file_sha256")
        if not isinstance(implementation_files, dict) or set(implementation_files) != {
            "scripts/m2_asf_hyp3_rtc_composite_provenance_core_001.py",
            "scripts/m2_asf_hyp3_rtc_composite_provenance_001.py",
            "tests/test_m2_asf_hyp3_rtc_composite_provenance_001.py",
        } or any(_sha(root / ref) != sha for ref, sha in implementation_files.items()):
            raise RouteStop("rtc_composite_implementation_drift")
        for name, relative in RECEIPT_REFS.items():
            path = data_root / relative
            if not _safe_file(path) or not _safe_dir(path.parent) or not _safe_dir(path.parent.parent):
                raise RouteStop("rtc_composite_receipt_path_invalid")
            if name in ("descriptor", "acquisition", "readme"):
                key = {
                    "descriptor": "non_git_descriptor_sha256",
                    "acquisition": "non_git_acquisition_terminal_sha256",
                    "readme": "non_git_readme_probe_terminal_sha256",
                }[name]
                if _sha(path) != proposal.get("frozen_evidence", {}).get(key):
                    raise RouteStop("rtc_composite_receipt_hash_mismatch")
            if preflight.get("bindings", {}).get(f"{name}_sha256") != _sha(path):
                raise RouteStop("rtc_composite_preflight_drift")
        archive = data_root / "m2-asf-hyp3-rtc-products-001" / PRODUCT_FILENAME
        if not _safe_dir(archive.parent) or not _safe_file(archive) or archive.stat().st_size != ARCHIVE_SIZE:
            raise RouteStop("rtc_composite_archive_metadata_invalid")
        receipts = {name: _read_json(data_root / relative) for name, relative in RECEIPT_REFS.items()}
        return receipts, proposal
    except RouteStop:
        raise
    except (OSError, ValueError, TypeError, KeyError):
        raise RouteStop("rtc_composite_release_unavailable") from None


def _write_new_json(path: Path, value: dict) -> None:
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise RouteStop("rtc_composite_receipt_collision") from None
    except OSError:
        raise RouteStop("rtc_composite_receipt_write_failed") from None


def evaluate_once(receipts: dict, attempt_root: Path = ATTEMPT_ROOT) -> dict:
    """Reserve the distinct attempt before one receipt-only evaluation."""
    if attempt_root.exists() or attempt_root.is_symlink():
        raise RouteStop("rtc_composite_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("rtc_composite_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("rtc_composite_attempt_reservation_failed") from None
    _write_new_json(attempt_root / "started.json", {
        "status": "receipt_only_evaluation_reserved", "source_id": SOURCE_ID,
        "job_id": JOB_ID, "started_at_utc": now_utc(),
        "archive_opened": False, "raster_pixels_read": False,
    })
    try:
        approved = load_approved_jobs()[0]
        terminal = evaluate_composite(
            receipts["submission"], receipts["descriptor"],
            receipts["acquisition"], receipts["readme"], approved,
        )
        terminal["finished_at_utc"] = now_utc()
    except RouteStop as exc:
        terminal = {"status": "stopped_receipt_only_no_automatic_retry", "code": exc.code,
                    "source_id": SOURCE_ID, "job_id": JOB_ID,
                    "finished_at_utc": now_utc(), "archive_opened": False,
                    "raster_pixels_read": False}
    except Exception:
        terminal = {"status": "stopped_receipt_only_no_automatic_retry",
                    "code": "rtc_composite_unexpected_failure", "source_id": SOURCE_ID,
                    "job_id": JOB_ID, "finished_at_utc": now_utc(),
                    "archive_opened": False, "raster_pixels_read": False}
    _write_new_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        receipts, _ = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_composite_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("rtc_composite_arguments_invalid")
        result = evaluate_once(receipts)
        print(json.dumps({"status": result["status"], "code": result.get("code"),
                          "source_id": SOURCE_ID, "raster_pixels_read": False}, sort_keys=True))
        return 0 if result["status"] == "pass_composite_provenance_for_local_qa_only" else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "raster_pixels_read": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "rtc_composite_unexpected_failure",
                          "raster_pixels_read": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
