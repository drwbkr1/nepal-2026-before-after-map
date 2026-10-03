"""Fixed-policy EarthExplorer handoff, budgets and no-replace local custody.

No provider request occurs here. A reserved activation counts before an exact
browser click, including owner clicks; a monitor never initiates a retry.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path

import optical_alternate_catalog_001 as policy
from landsat_l2_grouped_mtl_integrity_002 import inspect_bundle, BundleIntegrityError
from m2_transfer_core import promote_atomic_no_replace, sha256_file

PolicyStop, read, write_new, now = policy.PolicyStop, policy.read, policy.write_new, policy.now
MAX_ARCHIVE = 2_147_483_648
MAX_RECEIVED = 12_884_901_888
MAX_PROMOTED = 8_589_934_592
MIN_FREE = 32_212_254_720
PARTIALS = (".crdownload", ".part", ".partial", ".tmp")


def snapshot(downloads, product):
    """No content read. Retain only exact-product names, sizes and timestamps."""
    downloads = Path(downloads)
    if not downloads.is_dir() or downloads.is_symlink() or policy.is_reparse_point(downloads):
        raise PolicyStop("download_directory_unsafe")
    result = {}
    for file in downloads.iterdir():
        if file.name.startswith(product):
            if not file.is_file() or file.is_symlink() or policy.is_reparse_point(file):
                raise PolicyStop("browser_candidate_unsafe")
            s = file.stat()
            result[file.name] = {"bytes": s.st_size, "mtime_ns": s.st_mtime_ns}
    return result


def received_bytes(attempts):
    # Observed browser byte maxima include failed/partial attempts, rather than
    # counting only successfully promoted archives or duplicated staging copies.
    total = 0
    for attempt in sorted(Path(attempts).glob("activation-*")):
        samples = [read(p) for p in attempt.glob("sample-*.json")]
        total += max((s["observed_received_bytes"] for s in samples), default=0)
    return total


def record_sample(attempt, names):
    size = sum(value["bytes"] for value in names.values())
    count = len(list(attempt.glob("sample-*.json"))) + 1
    write_new(attempt / f"sample-{count:05d}.json", {"at_utc": now(), "files": names,
                                                     "observed_received_bytes": size})
    if size > MAX_ARCHIVE or received_bytes(attempt.parent) > MAX_RECEIVED:
        raise PolicyStop("received_source_byte_budget_exhausted")


def candidate(names, product):
    if not names:
        return None
    base = product + ".tar"
    if any(name != base and not any(name == base + ext for ext in PARTIALS) for name in names):
        raise PolicyStop("ambiguous_or_unexpected_browser_file")
    if any(name != base for name in names):
        return None
    value = names[base]
    if value["bytes"] <= 0 or value["bytes"] > MAX_ARCHIVE:
        raise PolicyStop("browser_archive_size_out_of_bounds")
    return value


def reserve(data, downloads, selection_path, rank, role, gate, rights, previous_pair_qa=None, recovery_of=None):
    selection = read(selection_path)
    if selection.get("status") != "pass_complete_fixed_policy_selection_locked" or selection.get("approval_sha256") != policy.APPROVAL_SHA:
        raise PolicyStop("selection_lock_invalid")
    if (gate.get("status") != "pass_final_no_content_preflight" or gate.get("approval_sha256") != policy.APPROVAL_SHA
            or not rights.get("pass_unchanged_usgs_rights_and_exact_full_bundle_option")):
        raise PolicyStop("intake_gate_or_rights_invalid")
    if rank not in (1, 2) or role not in ("before", "after"):
        raise PolicyStop("source_order_invalid")
    pairs = selection["pairs"]
    if rank > len(pairs) or pairs[rank - 1]["locked_rank"] != rank:
        raise PolicyStop("source_outside_locked_shortlist")
    if rank == 2 and (not previous_pair_qa or previous_pair_qa.get("status") != "pass_pair_visual_qa_only"
                      or previous_pair_qa.get("full_both_aois") is not False):
        raise PolicyStop("second_pair_not_released_by_ordinary_coverage_outcome")
    source = pairs[rank - 1][role]
    if source["product_id"] in policy.EXCLUDED or not source["eligible"]:
        raise PolicyStop("terminal_or_ineligible_source_cannot_requeue")
    data = Path(data)
    if not data.is_dir() or data.is_symlink() or policy.is_reparse_point(data) or shutil.disk_usage(data).free < MIN_FREE:
        raise PolicyStop("controlled_data_root_or_space_invalid")
    attempts = data / ".intake-staging" / policy.SCOPE / "attempt-events"
    policy.safe_path(data, attempts)
    existing = sorted(attempts.glob("activation-*"))
    if any(not (p / "terminal.json").is_file() and not (p / "terminal-fallback.json").is_file() for p in existing):
        raise PolicyStop("prior_activation_not_terminal_no_replay")
    if len(existing) >= 6 or received_bytes(attempts) >= MAX_RECEIVED:
        raise PolicyStop("activation_or_total_byte_budget_exhausted")
    reservations = [read(p / "intent.json") for p in existing]
    initials = [r for r in reservations if not r["recovery_of"]]
    product = source["product_id"]
    if recovery_of:
        if sum(bool(r["recovery_of"]) for r in reservations) >= 2:
            raise PolicyStop("classified_transfer_recovery_budget_exhausted")
        prior = next((p for p in existing if p.name == recovery_of), None)
        if prior is None:
            raise PolicyStop("recovery_lineage_invalid")
        old = read(prior / "terminal.json")
        if old.get("product_id") != product or old.get("failure_code") not in ("transient_transfer_interrupted", "agent_handoff_mechanical_failure"):
            raise PolicyStop("failure_not_classified_transfer_recoverable")
    elif any(r["product_id"] == product for r in reservations) or len({r["product_id"] for r in initials}) >= 4:
        raise PolicyStop("source_already_attempted_or_distinct_product_budget_exhausted")
    # A source shared by locked pairs is handled by verified local reuse, never
    # a duplicate acquisition activation.
    if role == "after":
        before = pairs[rank - 1]["before"]["product_id"]
        if not (data / "custody" / policy.SCOPE / (before + ".tar")).is_file():
            raise PolicyStop("before_source_not_promoted")
    promoted = data / "custody" / policy.SCOPE
    if sum(p.stat().st_size for p in promoted.glob("*.tar")) > MAX_PROMOTED:
        raise PolicyStop("promoted_source_byte_budget_exhausted")
    initial = snapshot(downloads, product)
    if initial:
        raise PolicyStop("exact_product_browser_file_preexists")
    number = len(existing) + 1
    attempt = attempts / f"activation-{number:03d}"
    staging = data / ".intake-staging" / policy.SCOPE / "attempt-bytes" / attempt.name / (product + ".tar.part")
    destination = promoted / (product + ".tar")
    for target in (attempt, staging, destination):
        policy.safe_path(data, target)
        if target.exists() or target.is_symlink():
            raise PolicyStop("intake_no_replace_collision")
    # Reservation is itself the exclusive activation budget. A crash or failed
    # click consumes it; it is never silently reused as a new click permission.
    attempt.mkdir(parents=True, exist_ok=False)
    write_new(attempt / "intent.json", {"status": "exclusive_activation_reserved_before_click", "at_utc": now(),
               "product_id": product, "scene_id": source["scene_id"], "rank": rank, "role": role,
               "selection_sha256": sha256_file(selection_path), "approval_sha256": policy.APPROVAL_SHA,
               "preflight": gate, "rights_and_option_observation": rights,
               "initial_download_snapshot": initial, "recovery_of": recovery_of,
               "weak_browser_file_provenance": True, "provider_checksum_available": False})
    return attempt, staging, destination


def close(attempt, payload):
    result = {**payload, "at_utc": now(), "provider_authenticated_checksum": False, "pixel_qa": False}
    try:
        write_new(attempt / "terminal.json", result)
    except BaseException:
        write_new(attempt / "terminal-fallback.json", result)
    # Cleanup receipt is independent; browser files and all partials are retained.
    write_new(attempt / "cleanup.json", {"status": "all_inputs_and_partial_evidence_retained", "at_utc": now()})
    return result


def finish(attempt, staging, destination, downloads, *, clock=time.monotonic, pause=time.sleep, limit=1800, stable=30):
    intent = read(attempt / "intent.json")
    if any((attempt / name).exists() for name in ("terminal.json", "terminal-fallback.json", "monitor-claim.json")):
        raise PolicyStop("activation_already_consumed_or_monitor_claimed")
    product, scene = intent["product_id"], intent["scene_id"]
    write_new(attempt / "monitor-claim.json", {"at_utc": now(), "status": "one_monitor_claimed_no_click_or_retry"})
    begin, last, since = clock(), None, None
    try:
        while clock() - begin <= limit:
            names = snapshot(downloads, product)
            if names != last:
                record_sample(attempt, names)
                last, since = names, clock()
            found = candidate(names, product)
            if found and since is not None and clock() - since >= stable:
                break
            pause(1)
        else:
            raise PolicyStop("browser_arrival_timeout_indeterminate_transfer")
        source = Path(downloads) / (product + ".tar")
        if staging.exists() or destination.exists():
            raise PolicyStop("intake_no_replace_collision")
        staging.parent.mkdir(parents=True, exist_ok=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest, copied = hashlib.sha256(), 0
        with source.open("rb") as reader, staging.open("xb") as writer:
            for block in iter(lambda: reader.read(8 * 1024**2), b""):
                copied += len(block)
                if copied > MAX_ARCHIVE:
                    raise PolicyStop("browser_archive_size_out_of_bounds")
                writer.write(block); digest.update(block)
            writer.flush(); os.fsync(writer.fileno())
        if snapshot(downloads, product) != names or copied != found["bytes"] or sha256_file(source) != digest.hexdigest():
            raise PolicyStop("browser_source_changed_during_copy")
        verified = inspect_bundle(staging, product, scene)
        if (verified["archive_size_bytes"], verified["archive_sha256"]) != (copied, digest.hexdigest()):
            raise PolicyStop("staged_archive_identity_drift")
        write_new(attempt / "verification.json", verified)
        if sum(p.stat().st_size for p in destination.parent.glob("*.tar")) + copied > MAX_PROMOTED:
            raise PolicyStop("promoted_source_byte_budget_exhausted")
        promoted = promote_atomic_no_replace(staging, destination)
        if (promoted["size_bytes"], promoted["sha256"]) != (copied, digest.hexdigest()):
            raise PolicyStop("promoted_archive_identity_drift")
        return close(attempt, {"status": "pass_container_only_no_replace_custody", "product_id": product,
                              "scene_id": scene, "archive_size_bytes": copied, "archive_sha256": digest.hexdigest()})
    except BaseException as exc:
        # Fixed locally generated codes only. Never persist arbitrary errors,
        # paths, cookies, URLs or browser session/account information.
        code = str(exc) if isinstance(exc, (PolicyStop, BundleIntegrityError)) else "local_io_or_unexpected_failure"
        return close(attempt, {"status": "block_container_or_browser_handoff", "product_id": product,
                              "failure_code": code, "partial_preserved": staging.exists()})
