"""Bounded read-only metadata inspection for the distinct grid recovery."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, BinaryIO

from m2_radar_event_pair_grid_provenance_diagnostic_001_core import (
    DATA_ROOT, NAMES, OLD_ATTEMPT, ROOT, SOURCE_ROOT, DiagnosticError,
    candidate_paths, first_declared_coarse_stage, inspect_raster, load_json,
    reserve, sha256_file,
)

PREFIX = "m2-radar-event-area-pair-grid-provenance-recovery-001"
PROPOSAL = ROOT / "contracts" / "milestone-002-radar-event-area-pair-grid-provenance-recovery-001-proposal.json"
BUNDLE = ROOT / "reviews" / PREFIX / "review-bundle.json"
APPROVAL = ROOT / "records" / "source-gates" / f"{PREFIX}-approval.json"
PACKET_GATE = ROOT / "records" / "readiness" / f"{PREFIX}-packet-publication-gate.json"
EXPECTED_PROPOSAL_SHA256 = "ccb4617ae462910789eefc4d411b0a9c6b8d4baf1c9107ed301eed536feafdc3"
EXPECTED_BUNDLE_SHA256 = "27d55419ddc0a02edfc009c076a45faaaaaf90a25f7f5b5a0a3aa107be691645"
EXPECTED_CONF_SHA256 = "eff271e62660d4ae2fe64d614c9051a953c750f167926b946dcf3cb5e9c7d419"
MAX_ENTRIES = 20_000
MAX_CANDIDATES = 256
MAX_CANDIDATE_BYTES = 1_048_576
CONFIG_SUFFIXES = (".conf", ".json", ".xml", ".cdi")


def check_authority() -> None:
    if sha256_file(PROPOSAL) != EXPECTED_PROPOSAL_SHA256 or sha256_file(BUNDLE) != EXPECTED_BUNDLE_SHA256:
        raise DiagnosticError("proposal_or_bundle_drift")
    approval = load_json(APPROVAL)
    gate = load_json(PACKET_GATE)
    if (
        approval.get("decision") != "approve"
        or approval.get("bindings", {}).get("proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or approval.get("bindings", {}).get("review_bundle_sha256") != EXPECTED_BUNDLE_SHA256
        or gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
        or gate.get("bindings", {}).get("approval_sha256") != sha256_file(APPROVAL)
        or gate.get("bindings", {}).get("packet_commit_sha") != "75508e75e5e6e2c2201c2df6b11e67db81a00e47"
        or gate.get("bindings", {}).get("public_ci_conclusion") != "success"
    ):
        raise DiagnosticError("packet_authority_not_pass")


def append_stage(stream: BinaryIO, value: dict[str, Any]) -> None:
    stream.write((json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8"))
    stream.flush()
    os.fsync(stream.fileno())


def _is_unsafe(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def _config_class(path: Path) -> bool:
    lower = path.name.lower()
    return lower.endswith(CONFIG_SUFFIXES) or lower.endswith(".aux.xml")


def inventory_gtc_configuration(path: Path, *, root: Path = SOURCE_ROOT,
                                expected_sha256: str = EXPECTED_CONF_SHA256) -> dict[str, Any]:
    if path != root / "gamma0_linear_gtc_raw.crf" or not path.is_dir() or _is_unsafe(path):
        raise DiagnosticError("configuration_root_not_exact_gtc")
    resolved_root = path.resolve()
    if resolved_root != root.resolve() / path.name:
        raise DiagnosticError("configuration_root_resolved_outside_exact_source")
    entries = 0
    candidates = 0
    candidate_hashes: list[str] = []
    matching = 0
    pending = [path]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            children = sorted(iterator, key=lambda item: item.name)
        for child in children:
            entries += 1
            if entries > MAX_ENTRIES:
                raise DiagnosticError("gtc_directory_entry_bound_exceeded")
            item = Path(child.path)
            if _is_unsafe(item) or not item.resolve().is_relative_to(resolved_root):
                raise DiagnosticError("gtc_directory_entry_unsafe")
            if child.is_dir(follow_symlinks=False):
                pending.append(item)
            elif child.is_file(follow_symlinks=False) and _config_class(item):
                candidates += 1
                if candidates > MAX_CANDIDATES:
                    raise DiagnosticError("gtc_configuration_candidate_bound_exceeded")
                size = child.stat(follow_symlinks=False).st_size
                if size > MAX_CANDIDATE_BYTES:
                    raise DiagnosticError("gtc_configuration_candidate_oversized")
                digest = sha256_file(item)
                candidate_hashes.append(digest)
                if digest == expected_sha256:
                    matching += 1
    return {
        "directory_entries_enumerated": entries,
        "configuration_candidates_hashed": candidates,
        "configuration_candidate_sha256s": sorted(candidate_hashes),
        "historical_configuration_sha256": expected_sha256,
        "matching_historical_configuration_count": matching,
        "historical_configuration_identity": "unique_match" if matching == 1 else "unresolved_no_match_or_ambiguous",
    }
