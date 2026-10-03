#!/usr/bin/env python3
"""Outcome-scoped visual completion with immutable attempts and metadata gate.

Reuse the frozen scientific route and durable supervisor in a private process.
Only selected metadata semantics and control bindings change. No network/retry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

import landsat9_grouped_visual_metadata_001 as metadata
import run_m2_landsat9_pixel_visual_recovery_001 as durable

frozen = durable.frozen
ROOT, DATA, RUNTIME = durable.ROOT, durable.DATA, durable.RUNTIME
SCOPE = "landsat9-visual-route-completion-001"
APPROVAL = ROOT / "records/source-gates/m2-landsat9-visual-route-completion-001-approval.json"
APPROVAL_SHA = "9ba6d3366aa43f7e2d34fa44d9dd0f67ef1674099887ca6496c0677a695a7389"
PROPOSAL = ROOT / "contracts/milestone-002-landsat9-visual-route-completion-001-proposal.json"
PROPOSAL_SHA = "7f4dc4bec11cea3f370f7efd26ab586360fad0e85e5b4f278cd7a7f279c38e6f"
BUNDLE = ROOT / "reviews/m2-landsat9-visual-route-completion-001/review-bundle.json"
BUNDLE_SHA = "22c6d4843838b363c851919fb9fd585fc6dbaf6850075b5dcc07e2c529ddab45"
AUDIT = DATA / ".attempt-events" / SCOPE / "metadata-audit-001"
AUDIT_FALLBACK = DATA / ".attempt-fallback" / SCOPE / "metadata-audit-001"
METADATA_CODES = frozenset("""mtl_selected_value_syntax_invalid mtl_selected_group_missing_or_duplicate
mtl_selected_field_missing_or_duplicate mtl_selected_text_xml_disagreement
mtl_text_encoding_invalid mtl_odl_structure_invalid mtl_odl_identity_syntax_invalid
mtl_xml_unsafe_declaration mtl_xml_invalid mtl_xml_root_invalid mtl_xml_structure_invalid
mtl_xml_identity_syntax_invalid mtl_required_group_missing_or_duplicate mtl_root_group_invalid
mtl_identity_path_missing_or_unexpected mtl_level2_or_scene_identity_mismatch
mtl_level1_provenance_invalid mtl_level2_processing_level_invalid
mtl_level1_processing_level_invalid mtl_text_xml_identity_disagree""".split())
now, sha, write_new = durable.now, durable.sha, durable.write_new


def roots(attempt_id):
    if not re.fullmatch(r"real-00[3-9]|real-0[1-9][0-9]|real-[1-9][0-9]{2}", attempt_id):
        raise frozen.RouteStop("fresh_attempt_identity_invalid")
    return (DATA / "processing" / SCOPE / attempt_id,
            DATA / ".attempt-events" / SCOPE / attempt_id,
            DATA / ".attempt-fallback" / SCOPE / attempt_id)


def fields(paths, role):
    product, scene, *_ = frozen.PRODUCTS[role]
    try:
        return metadata.inspect(paths["_MTL.txt"].read_bytes(), paths["_MTL.xml"].read_bytes(), product, scene)
    except (metadata.MetadataError, metadata.identity.BundleIntegrityError) as exc:
        code = str(exc)
        raise frozen.RouteStop(code if code in METADATA_CODES | durable.WORKER_CODES
                               else "metadata_unclassified_failure") from None


@contextmanager
def binding(attempt):
    replacements = {"ATTEMPT": attempt, "APPROVAL": APPROVAL, "APPROVAL_SHA": APPROVAL_SHA,
                    "PROPOSAL": PROPOSAL, "PROPOSAL_SHA": PROPOSAL_SHA,
                    "BUNDLE": BUNDLE, "BUNDLE_SHA": BUNDLE_SHA, "now": now,
                    "mtl_fields": fields}
    originals = {k: getattr(frozen, k) for k in replacements}
    try:
        for k, v in replacements.items():
            setattr(frozen, k, v)
        yield
    finally:
        for k, v in originals.items():
            setattr(frozen, k, v)


@contextmanager
def supervisor_binding():
    old_approval, old_codes = durable.APPROVAL_SHA, durable.WORKER_CODES
    try:
        durable.APPROVAL_SHA = APPROVAL_SHA
        durable.WORKER_CODES = old_codes | METADATA_CODES
        yield
    finally:
        durable.APPROVAL_SHA, durable.WORKER_CODES = old_approval, old_codes


def controls(attempt):
    for path, expected in ((APPROVAL, APPROVAL_SHA), (PROPOSAL, PROPOSAL_SHA), (BUNDLE, BUNDLE_SHA)):
        if sha(path) != expected:
            raise frozen.RouteStop("frozen_control_hash_drift")
    for item in frozen.read_json(BUNDLE)["bound_files"]:
        if sha(ROOT / item["ref"]) != item["sha256"]:
            raise frozen.RouteStop("review_bundle_bound_file_drift")
    if not durable.PRIOR.is_dir() or list(durable.PRIOR.iterdir()):
        raise frozen.RouteStop("consumed_real_001_observation_drift")
    prior = frozen.read_json(ROOT / "records/readiness/m2-landsat9-pixel-visual-recovery-001-terminal-reconciliation.json")
    old_roots = {"worker": durable.ATTEMPT, "supervisor": durable.EVENTS, "fallback": durable.FALLBACK}
    for kind, receipts in prior["real_attempt"]["external_receipt_sha256"].items():
        for name, expected in receipts.items():
            if sha(old_roots[kind] / name) != expected:
                raise frozen.RouteStop("consumed_real_002_receipt_drift")
    _, events, fallback = roots(attempt.name)
    for target in (attempt, events, fallback, AUDIT, AUDIT_FALLBACK):
        for path in (target, *target.parents):
            if path == DATA.parent:
                break
            if path.is_symlink() or (path.exists() and frozen.is_reparse_point(path)):
                raise frozen.RouteStop("fresh_attempt_path_unsafe")
    with binding(attempt):
        frozen._check_controls()


def code_hashes():
    return {p.name: sha(p) for p in (Path(__file__).resolve(), Path(metadata.__file__).resolve())}


def preflight(commit, run, attempt_id, audit_ref=None):
    attempt, events, fallback = roots(attempt_id)
    controls(attempt)
    if any(p.exists() or p.is_symlink() for p in (attempt, events, fallback)):
        raise frozen.RouteStop("fresh_attempt_or_receipt_collision")
    with binding(attempt):
        gate = frozen.preflight(commit, run)
    gate.update({"attempt_id": attempt_id, "recovery_approval_sha256": APPROVAL_SHA,
                 "recovery_attempt_root_absent": True, "independent_event_roots_absent": True,
                 "implementation_hashes": code_hashes()})
    if audit_ref:
        receipt = frozen.read_json(Path(audit_ref))
        if receipt.get("status") != "pass_exact_two_source_metadata_only":
            raise frozen.RouteStop("metadata_audit_gate_invalid")
        gate.update({"metadata_audit_ref": str(audit_ref), "metadata_audit_sha256": sha(Path(audit_ref))})
        validate_audit(gate)
    else:
        if AUDIT.exists() or AUDIT_FALLBACK.exists():
            raise frozen.RouteStop("metadata_audit_already_consumed")
    return gate


def audit_pair(role):
    product, scene, size, expected_sha, *_ = frozen.PRODUCTS[role]
    archive = DATA / "custody/landsat9-c2l2" / (product + ".tar")
    if archive.stat().st_size != size or frozen.sha256_file(archive) != expected_sha:
        raise frozen.RouteStop("promoted_archive_identity_drift")
    members = {PurePosixPath(m["name"]).name: m for m in frozen._receipt(role)["members"]}
    raw, evidence = {}, {}
    with tarfile.open(archive, "r:") as tar:
        indexed = {m.name: m for m in tar.getmembers()}
        for suffix in ("_MTL.txt", "_MTL.xml"):
            item = members[product + suffix]
            member = indexed.get(item["name"])
            if (member is None or not member.isfile() or member.size != item["size_bytes"]
                    or member.size > metadata.identity.MAX_METADATA_BYTES):
                raise frozen.RouteStop("exact_member_missing_or_size_drift")
            with tar.extractfile(member) as stream:
                raw[suffix] = stream.read(metadata.identity.MAX_METADATA_BYTES + 1)
            digest = hashlib.sha256(raw[suffix]).hexdigest()
            if len(raw[suffix]) != item["size_bytes"] or digest != item["sha256"]:
                raise frozen.RouteStop("materialized_member_hash_drift")
            evidence[suffix] = {"size_bytes": item["size_bytes"], "sha256": digest}
    result = metadata.inspect(raw["_MTL.txt"], raw["_MTL.xml"], product, scene)
    if archive.stat().st_size != size or frozen.sha256_file(archive) != expected_sha:
        raise frozen.RouteStop("promoted_archive_changed_during_materialization")
    return {"role": role, "product_id": product, "archive_sha256": expected_sha,
            "members": evidence, "validated_metadata": result}


def metadata_audit(gate_path):
    gate = frozen.read_json(gate_path)
    validate_gate(gate)
    attempt, *_ = roots(gate["attempt_id"])
    controls(attempt)
    if AUDIT.exists() or AUDIT_FALLBACK.exists():
        raise frozen.RouteStop("metadata_audit_already_consumed")
    AUDIT_FALLBACK.mkdir(parents=True, exist_ok=False)
    write_new(AUDIT_FALLBACK / "ready.json", {"status": "reserved_before_metadata", "at_utc": now()})
    AUDIT.mkdir(parents=True, exist_ok=False)
    result = {"status": "blocked_metadata_audit", "completed_sources": []}
    try:
        write_new(AUDIT / "intent.json", {"status": "reserved_before_metadata", "gate_sha256": sha(gate_path), "at_utc": now()})
        for role in ("before", "after"):
            write_new(AUDIT / (role + "-start.json"), {"role": role, "at_utc": now()})
            receipt = audit_pair(role)
            write_new(AUDIT / (role + "-metadata.json"), receipt)
            result["completed_sources"].append(role)
        result["status"] = "pass_exact_two_source_metadata_only"
    except BaseException as exc:
        result.update({"exception_class": durable.safe_exception(exc), "reason": safe_code(exc)})
    result.update({"at_utc": now(), "tiff_header_or_pixel_read": False, "provider_requests": 0,
                   "approval_sha256": APPROVAL_SHA, "implementation_hashes": code_hashes(),
                   "source_results": {role: sha(AUDIT / (role + "-metadata.json"))
                                      for role in result["completed_sources"]}})
    try:
        write_new(AUDIT / "terminal.json", result)
    except BaseException:
        write_new(AUDIT_FALLBACK / "terminal.json", result)
    write_new(AUDIT_FALLBACK / "cleanup.json", {"status": "metadata_receipts_retained", "at_utc": now(), "source_mutation": False})
    return result


def validate_gate(gate):
    if (gate.get("status") != "pass_final_no_content_preflight"
            or gate.get("approval_sha256") != APPROVAL_SHA
            or gate.get("implementation_hashes") != code_hashes()):
        raise frozen.RouteStop("final_preflight_gate_invalid")


def safe_code(exc):
    code = str(exc)
    return code if code in durable.WORKER_CODES | METADATA_CODES else "local_io_or_unexpected_failure"


def validate_audit(gate):
    audit = Path(gate.get("metadata_audit_ref", ""))
    if audit not in (AUDIT / "terminal.json", AUDIT_FALLBACK / "terminal.json"):
        raise frozen.RouteStop("metadata_audit_gate_invalid")
    if sha(audit) != gate.get("metadata_audit_sha256"):
        raise frozen.RouteStop("metadata_audit_gate_invalid")
    receipt = frozen.read_json(audit)
    if (receipt.get("status") != "pass_exact_two_source_metadata_only"
            or receipt.get("approval_sha256") != APPROVAL_SHA
            or receipt.get("implementation_hashes", {}).get(Path(metadata.__file__).name)
               != sha(Path(metadata.__file__))
            or receipt.get("completed_sources") != ["before", "after"]):
        raise frozen.RouteStop("metadata_audit_gate_invalid")
    for role, expected in receipt.get("source_results", {}).items():
        if role not in ("before", "after") or sha(AUDIT / (role + "-metadata.json")) != expected:
            raise frozen.RouteStop("metadata_audit_gate_invalid")
    if set(receipt.get("source_results", {})) != {"before", "after"}:
        raise frozen.RouteStop("metadata_audit_gate_invalid")


def supervise(gate_path, *, attempt=None, events=None, fallback=None, worker=None, after_intent=None):
    gate = frozen.read_json(gate_path)
    validate_gate(gate)
    # Injectable disposable roots bypass real audit/control access in tests only.
    if attempt is None:
        attempt, events, fallback = roots(gate["attempt_id"])
        controls(attempt)
        validate_audit(gate)
    if worker is None:
        def worker(path):
            with open(os.devnull, "wb") as sink:
                return subprocess.run([str(RUNTIME), str(Path(__file__).resolve()), "worker", "--gate", str(path)],
                                      stdout=sink, stderr=sink, check=False, timeout=14400).returncode
    with supervisor_binding():
        return durable.supervise(gate_path, attempt=attempt, events=events, fallback=fallback,
                                 worker=worker, after_intent=after_intent)


def worker_once(gate_path):
    gate = frozen.read_json(gate_path)
    validate_gate(gate)
    validate_audit(gate)
    attempt, events, fallback = roots(gate["attempt_id"])
    controls(attempt)
    intent = frozen.read_json(events / "intent.json")
    if (intent.get("gate_sha256") != sha(gate_path) or not (events / "worker-start.json").is_file()
            or not (fallback / "ready.json").is_file()):
        raise frozen.RouteStop("final_preflight_gate_invalid")
    write_new(events / "worker-claim.json", {"status": "one_worker_claimed", "at_utc": now(), "gate_sha256": sha(gate_path)})
    try:
        write_new(events / "arcpy-import-start.json", {"status": "starting_arcpy_import", "at_utc": now()})
        import arcpy
        write_new(events / "arcpy-import-pass.json", {"status": "arcpy_import_passed", "at_utc": now()})
        with binding(attempt), supervisor_binding(), durable.worker_stage_markers(events):
            result = frozen.run_once(gate, arcpy)
        return 0 if result["status"].startswith("pass_") else 20
    except BaseException as exc:
        payload = {"status": "worker_error_preserved_no_retry", "at_utc": now(), "exception_class": durable.safe_exception(exc)}
        try:
            write_new(events / "worker-error.json", payload)
        except BaseException:
            write_new(fallback / "worker-error.json", payload)
        return 20


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "metadata-audit", "supervise", "worker"))
    parser.add_argument("--attempt-id", default="real-003")
    parser.add_argument("--public-ci-commit", default="")
    parser.add_argument("--public-ci-run", default="")
    parser.add_argument("--audit-ref")
    parser.add_argument("--gate")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        if args.mode == "worker":
            return worker_once(Path(args.gate))
        if args.mode == "preflight":
            result = preflight(args.public_ci_commit, args.public_ci_run, args.attempt_id, args.audit_ref)
        elif args.mode == "metadata-audit":
            result = metadata_audit(Path(args.gate))
        else:
            result = supervise(Path(args.gate))
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            write_new(out, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"].startswith("pass_") else 20
    except BaseException as exc:
        print(json.dumps({"status": "stopped", "code": safe_code(exc), "exception_class": durable.safe_exception(exc)}, sort_keys=True))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
