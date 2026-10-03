"""Versioned controls for approved discovery, exact intake, frozen QA and panel.

No baseline/change/attribution method is released. Acquisition stays in the
owner's existing EarthExplorer browser. All attempted roots are append-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

import numpy as np
import optical_alternate_catalog_001 as policy
import optical_alternate_intake_001 as intake
import optical_alternate_panel_arcgis_001 as panel
import landsat9_grouped_visual_metadata_001 as metadata
import run_m2_landsat9_pixel_visual_recovery_001 as durable

frozen = durable.frozen
ROOT, DATA, SCOPE, RUNTIME = policy.ROOT, policy.DATA, policy.SCOPE, durable.RUNTIME
read, write_new, now, sha = policy.read, policy.write_new, policy.now, policy.sha256_file
METHOD_FILES = ("scripts/run_m2_landsat9_pixel_visual_panel_001.py",
                "scripts/run_m2_landsat9_pixel_visual_recovery_001.py", "scripts/landsat9_visual_panel_arcgis_001.py")
METHOD_SHAS = ("8f73dc48f8b2b669c85d6bf76c1cfe0b816d91e4acf63b07aa247111f4340c00",
               "322ffab8ff44a4d81f7aa0ddd7c487c165d10da71c54596b356e39d2d4e573e4",
               "b25d11a03c35310cbab00128a160cafb5f8cfbec43e72456430d2c98a8516362")
IMPLEMENTATION = ("optical_alternate_catalog_001.py", "optical_alternate_intake_001.py",
                  "optical_alternate_panel_arcgis_001.py", "run_m2_optical_alternate_source_route_001.py",
                  "validate_m2_optical_alternate_source_route_001_arcgis.py")
DISCOVERY = DATA / ".attempt-events" / SCOPE / "metadata-001"
RECOVERY_DISCOVERY = DATA / ".attempt-events" / SCOPE / "metadata-recovery-001"
MECHANICAL = ROOT / "records/readiness/m2-optical-alternate-source-route-001-catalog-serialization-correction-001.json"
READINESS = ROOT / "records/readiness/m2-optical-alternate-source-route-001-implementation-readiness.json"
MECHANICAL_READINESS = ROOT / "records/readiness/m2-optical-alternate-source-route-001-mechanical-recovery-001-implementation-readiness.json"


def code_hashes():
    return {"scripts/" + name: sha(ROOT / "scripts" / name) for name in IMPLEMENTATION}


def controls():
    policy.controls()
    for ref, expected in zip(METHOD_FILES, METHOD_SHAS):
        if sha(ROOT / ref) != expected:
            raise policy.PolicyStop("frozen_method_hash_drift")


def preflight(commit, run, mechanical=False):
    """No provider, source, TIFF or pixel read. Exact public CI checked live."""
    controls()
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or not re.fullmatch(r"\d{8,20}", run):
        raise policy.PolicyStop("implementation_ci_reference_invalid")
    readiness_path = MECHANICAL_READINESS if mechanical else READINESS
    readiness = read(readiness_path)
    if (readiness.get("status") != "pass_portable_and_installed_disposable_tests"
            or readiness.get("implementation_hashes") != code_hashes()
            or not readiness.get("installed_arcgis_disposable_end_to_end_pass")):
        raise policy.PolicyStop("implementation_readiness_invalid")
    result = subprocess.run(["gh", "run", "view", run, "--json", "headSha,status,conclusion"],
                            capture_output=True, text=True, check=True, timeout=45)
    ci = json.loads(result.stdout)
    if ci != {"headSha": commit, "status": "completed", "conclusion": "success"}:
        raise policy.PolicyStop("implementation_public_ci_not_pass")
    # Every implementation byte must actually be present in the gated commit.
    for ref, expected in code_hashes().items():
        blob = subprocess.run(["git", "show", commit + ":" + ref], capture_output=True, check=True).stdout
        if hashlib.sha256(blob).hexdigest() != expected:
            raise policy.PolicyStop("public_implementation_byte_mismatch")
    if not RUNTIME.is_file() or not DATA.is_dir() or shutil.disk_usage(DATA).free < intake.MIN_FREE:
        raise policy.PolicyStop("runtime_or_disk_preflight_invalid")
    search_root = RECOVERY_DISCOVERY if mechanical else DISCOVERY
    for root in (search_root, DATA / "processing" / SCOPE, DATA / ".intake-staging" / SCOPE):
        policy.safe_path(DATA, root)
        if root.exists() or root.is_symlink():
            raise policy.PolicyStop("fresh_route_root_collision")
    if mechanical:
        correction = read(MECHANICAL)
        if correction.get("status") != "classified_agent_catalog_serialization_correction_within_unchanged_envelope":
            raise policy.PolicyStop("mechanical_correction_record_invalid")
        for ref, expected in correction["preserved_metadata_attempt_files"].items():
            if sha(DISCOVERY / ref) != expected:
                raise policy.PolicyStop("consumed_metadata_attempt_drift")
        policy.MetadataLedger.sealed_budget(DISCOVERY)
    return {"status": "pass_final_no_content_preflight", "at_utc": now(), "approval_sha256": policy.APPROVAL_SHA,
            "implementation_hashes": code_hashes(), "implementation_public_ci_commit": commit,
            "implementation_public_ci_run_id": run, "readiness_sha256": sha(readiness_path),
            "readiness_ref": str(readiness_path.relative_to(ROOT)),
            "source_payload_or_pixel_access": False, "provider_requests": 0, "metadata_http_budget": 18,
            "mechanical_metadata_recovery": mechanical,
            "mechanical_correction_record_sha256": sha(MECHANICAL) if mechanical else None}


def validate_gate(gate):
    controls()
    if (gate.get("status") != "pass_final_no_content_preflight" or gate.get("approval_sha256") != policy.APPROVAL_SHA
            or gate.get("implementation_hashes") != code_hashes()):
        raise policy.PolicyStop("exact_preflight_gate_invalid")
    if gate.get("mechanical_metadata_recovery") and sha(MECHANICAL) != gate.get("mechanical_correction_record_sha256"):
        raise policy.PolicyStop("mechanical_correction_record_drift")


def rights_check(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).lower()
    return ("earthexplorer" in text and "landsat" in text
            and any(phrase in text for phrase in ("no restrictions", "no use restrictions", "no restriction on", "public domain")))


def discovery_once(gate):
    validate_gate(gate)
    mechanical = gate.get("mechanical_metadata_recovery", False)
    discovery_root = RECOVERY_DISCOVERY if mechanical else DISCOVERY
    fallback = DATA / ".attempt-fallback" / SCOPE / discovery_root.name
    if fallback.exists():
        raise policy.PolicyStop("metadata_attempt_already_consumed")
    fallback.mkdir(parents=True, exist_ok=False)
    write_new(fallback / "ready.json", {"at_utc": now(), "status": "fallback_reserved_before_http"})
    seed = policy.MetadataLedger.sealed_budget(DISCOVERY) if mechanical else None
    ledger = policy.MetadataLedger(discovery_root, seed=seed)
    terminal = {"status": "stopped_metadata_no_selection", "source_payload_requests": 0}
    try:
        if mechanical:
            if read(DISCOVERY / "rights-observation.json").get("status") != "pass_unchanged_public_usgs_rights_distribution":
                raise policy.PolicyStop("prior_verified_rights_missing")
            rights_status = "prior_exact_live_official_rights_and_root_preserved"
        else:
            root = ledger.request("root", policy.CATALOG)
            if not isinstance(root, dict) or root.get("type") != "Catalog" or not isinstance(root.get("stac_version"), str):
                raise policy.PolicyStop("catalog_root_schema_unresolved")
            rights = ledger.request("rights", policy.RIGHTS)
            if not rights_check(rights):
                raise policy.PolicyStop("rights_or_distribution_not_reconciled")
            rights_status = "new_official_page_read"
        write_new(discovery_root / "rights-observation.json", {"status": "pass_unchanged_public_usgs_rights_distribution",
                    "official_page": policy.RIGHTS, "at_utc": now(), "rights_read_number": ledger.total,
                    "verification_origin": rights_status, "account_or_terms_action": False})
        geometries = policy.focus_geometries()
        discovery = policy.discover(ledger, geometries)
        terminal = policy.lock_selection(ledger, discovery, geometries)
    except BaseException as exc:
        terminal["failure_code"] = str(exc) if isinstance(exc, policy.PolicyStop) else "unclassified_metadata_failure"
    terminal.update({"at_utc": now(), "metadata_http_requests": ledger.total,
                     "metadata_budget_counts": ledger.counts, "implementation_hashes": code_hashes(),
                     "automatic_source_payload_request": False})
    try:
        write_new(discovery_root / "terminal.json", terminal)
    except BaseException:
        write_new(fallback / "terminal.json", terminal)
    write_new(fallback / "cleanup.json", {"status": "metadata_evidence_retained", "at_utc": now()})
    return terminal


def selected_pair(selection, rank):
    if (selection.get("status") != "pass_complete_fixed_policy_selection_locked"
            or selection.get("approval_sha256") != policy.APPROVAL_SHA
            or rank not in (1, 2) or rank > len(selection["pairs"])):
        raise policy.PolicyStop("locked_pair_invalid")
    pair = selection["pairs"][rank - 1]
    if pair["locked_rank"] != rank:
        raise policy.PolicyStop("locked_order_invalid")
    return pair


def source_receipt(source, data=DATA):
    product = source["product_id"]
    hits = []
    for p in (data / ".intake-staging" / SCOPE / "attempt-events").glob("activation-*/terminal.json"):
        terminal = read(p)
        if terminal.get("product_id") == product and terminal.get("status") == "pass_container_only_no_replace_custody":
            hits.append(p)
    if len(hits) != 1:
        raise policy.PolicyStop("exact_new_custody_receipt_missing_or_ambiguous")
    verification = read(hits[0].parent / "verification.json")
    if (verification.get("status") != "pass_container_and_grouped_mtl_identity_only"
            or verification.get("product_id") != product or verification.get("scene_id") != source["scene_id"]
            or verification.get("archive_sha256") != read(hits[0])["archive_sha256"]):
        raise policy.PolicyStop("new_custody_identity_drift")
    archive = data / "custody" / SCOPE / (product + ".tar")
    policy.safe_path(data, archive)
    if archive.stat().st_size != verification["archive_size_bytes"] or sha(archive) != verification["archive_sha256"]:
        raise policy.PolicyStop("new_promoted_archive_drift")
    return archive, verification


def audit_source(source, archive, verification):
    product = source["product_id"]
    members = {PurePosixPath(m["name"]).name: m for m in verification["members"]}
    raw = {}
    with tarfile.open(archive, "r:") as tar:
        for suffix in ("_MTL.txt", "_MTL.xml"):
            item = members[product + suffix]
            member = tar.getmember(item["name"])
            if not member.isfile() or member.size != item["size_bytes"] or member.size > metadata.identity.MAX_METADATA_BYTES:
                raise policy.PolicyStop("exact_metadata_member_invalid")
            with tar.extractfile(member) as stream:
                raw[suffix] = stream.read(metadata.identity.MAX_METADATA_BYTES + 1)
            if len(raw[suffix]) != item["size_bytes"] or hashlib.sha256(raw[suffix]).hexdigest() != item["sha256"]:
                raise policy.PolicyStop("exact_metadata_member_drift")
    mtl = metadata.inspect(raw["_MTL.txt"], raw["_MTL.xml"], product, source["scene_id"])
    actual = policy.utc(mtl["date_acquired"] + "T" + mtl["scene_center_time"])
    if actual != policy.utc(source["acquired_at_utc"]):
        raise policy.PolicyStop("catalog_mtl_acquisition_time_disagreement")
    return mtl


@contextmanager
def source_binding(pair, sources, data):
    products = {role: (pair[role]["product_id"], pair[role]["scene_id"], receipt["archive_size_bytes"],
                      receipt["archive_sha256"], "new-route") for role, (archive, receipt) in sources.items()}
    original = {key: getattr(frozen, key) for key in ("PRODUCTS", "DATA", "_receipt")}
    try:
        frozen.PRODUCTS, frozen.DATA = products, data
        frozen._receipt = lambda role: sources[role][1]
        yield
    finally:
        for key, value in original.items():
            setattr(frozen, key, value)


def extract_source(source, archive, receipt, target):
    """Exact ten-member materialization, no changes to scientific methods."""
    target.mkdir(exist_ok=False)
    paths = {}
    expected = {PurePosixPath(m["name"]).name: m for m in receipt["members"]}
    with tarfile.open(archive, "r:") as tar:
        for suffix in frozen.SUFFIXES:
            name = source["product_id"] + suffix
            item = expected[name]
            member = tar.getmember(item["name"])
            if not member.isfile() or member.size != item["size_bytes"]:
                raise policy.PolicyStop("exact_member_missing_or_size_drift")
            path, digest, count = target / name, hashlib.sha256(), 0
            with tar.extractfile(member) as stream, path.open("xb") as out:
                for block in iter(lambda: stream.read(8 * 1024**2), b""):
                    out.write(block); digest.update(block); count += len(block)
                out.flush(); os.fsync(out.fileno())
            if count != item["size_bytes"] or digest.hexdigest() != item["sha256"]:
                raise policy.PolicyStop("materialized_member_hash_drift")
            paths[suffix] = path
    if sha(archive) != receipt["archive_sha256"]:
        raise policy.PolicyStop("archive_changed_during_materialization")
    return paths


def pair_qa_once(pair, attempt, events, arcpy, *, data=DATA, aoi=None, load_source=source_receipt, extract=extract_source):
    """Both MTL audits and all headers precede pixels; no panel yet."""
    attempt.mkdir(parents=True, exist_ok=False)
    write_new(attempt / "started.json", {"status": "reserved_before_content", "at_utc": now(), "rank": pair["locked_rank"]})
    sources, mtls, paths, headers, metrics, panel_data = {}, {}, {}, {}, {}, {}
    stage = 0

    def marker(name):
        nonlocal stage
        stage += 1
        write_new(events / f"stage-{stage:03d}.json", {"stage": name, "at_utc": now()})

    # Load/hash each source first; audit both exact MTL pairs before TIFFs.
    for role in ("before", "after"):
        marker(role + "_metadata")
        sources[role] = load_source(pair[role], data)
        mtls[role] = audit_source(pair[role], *sources[role])
        write_new(attempt / (role + "-metadata.json"), mtls[role])
    for role in ("before", "after"):
        marker(role + "_materialization_and_headers")
        role_root = attempt / role
        role_root.mkdir(exist_ok=False)
        paths[role] = extract(pair[role], *sources[role], role_root / "members")
        headers[role] = frozen.raster_headers(paths[role], arcpy)
        frozen.validate_headers({"before": headers[role], "after": headers[role]})
        write_new(attempt / (role + "-headers.json"), headers[role])
    marker("pair_headers")
    grid = frozen.validate_headers(headers)
    write_new(attempt / "pair-header.json", grid)
    aoi = read(aoi or ROOT / "config/aoi/approved-study-areas-epsg32645.json")
    rings = {f["attributes"]["AOI_ID"]: f["geometry"]["rings"][0] for f in aoi["features"] if f["attributes"]["AOI_ID"] in policy.AOIS}
    if set(rings) != set(policy.AOIS):
        raise policy.PolicyStop("approved_aoi_ids_missing")
    for key in policy.AOIS:
        marker("pixels_" + key)
        window = frozen.aoi_window(rings[key], grid["before"])
        xmin, ymax, cols, rows = window
        weights = frozen.aoi_cell_weights(rings[key], xmin, ymax, cols, rows)
        before, before_fp = frozen.read_aoi_date(paths["before"], headers["before"], window, arcpy)
        after, after_fp = frozen.read_aoi_date(paths["after"], headers["after"], window, arcpy)
        metrics[key] = frozen.weighted_metrics(weights, before, after, before_fp, after_fp)
        npz = attempt / (key.lower() + "-panel-data.npz")
        np.savez_compressed(npz, weights=weights, before_reason=before["reason"], after_reason=after["reason"],
                            before_bands=before["calibrated"][[4, 3, 1]], after_bands=after["calibrated"][[4, 3, 1]], xmin=xmin, ymax=ymax)
        panel_data[key] = {"window": window, "npz": npz.name, "npz_sha256": sha(npz)}
    result = {"status": "pass_pair_visual_qa_only", "rank": pair["locked_rank"], "aoi_metrics": metrics,
              "full_both_aois": all(m["visual_status"] == "full_visual_panel_qa_only" for m in metrics.values()),
              "qualifying_aois": [k for k, m in metrics.items() if m["visual_status"] != "no_visual_panel_for_aoi"],
              "panel_data": panel_data, "mtls": mtls,
              "source_bands": {role: {band: str(paths[role]["_SR_" + band + ".TIF"].relative_to(attempt)) for band in ("B7", "B6", "B4")} for role in paths},
              "registration_measured": False, "scientific_admission": False, "panel_created": False}
    # Fraction predicates, not a label spelling, establish full coverage.
    result["full_both_aois"] = all(m["before"]["footprint_fraction"] >= .99 and m["after"]["footprint_fraction"] >= .99
                                   and min(m["before"]["strict_usable_fraction"], m["after"]["strict_usable_fraction"],
                                           m["paired_strict_usable_fraction"]) >= .80 for m in metrics.values())
    write_new(attempt / "pixel-qa.json", result)
    return result


def choose_panel(outcomes, expected_pairs):
    if not outcomes or any(r.get("status") != "pass_pair_visual_qa_only" or r.get("rank") != n for n, r in enumerate(outcomes, 1)):
        raise policy.PolicyStop("qa_outcome_order_or_hard_stop")
    if outcomes[0]["full_both_aois"]:
        if len(outcomes) != 1:
            raise policy.PolicyStop("second_pair_processed_after_full_first_pair")
        return 1
    if len(outcomes) != expected_pairs:
        raise policy.PolicyStop("remaining_locked_pair_not_evaluated")
    for full in (True, False):
        for outcome in outcomes:
            if outcome["full_both_aois"] if full else bool(outcome["qualifying_aois"]):
                return outcome["rank"]
    return None


def build_selected(pair, qa_root, output, arcpy):
    qa = read(qa_root / "pixel-qa.json")
    if qa.get("status") != "pass_pair_visual_qa_only" or not qa["qualifying_aois"] or output.exists():
        raise policy.PolicyStop("selected_visual_qa_or_panel_root_invalid")
    for entry in qa["panel_data"].values():
        if sha(qa_root / entry["npz"]) != entry["npz_sha256"]:
            raise policy.PolicyStop("qa_panel_input_drift")
    for role in ("before", "after"):
        _, receipt = source_receipt(pair[role])
        expected = {PurePosixPath(m["name"]).name: m["sha256"] for m in receipt["members"]}
        for relative in qa["source_bands"][role].values():
            path = qa_root / relative
            if sha(path) != expected[path.name]:
                raise policy.PolicyStop("materialized_source_band_drift")
    old = panel.PRODUCTS
    try:
        panel.PRODUCTS = tuple(pair[r]["product_id"] for r in ("before", "after"))
        built = panel.build(qa_root, qa["aoi_metrics"], qa["panel_data"], qa["mtls"],
                            {r: {b: qa_root / p for b, p in entries.items()} for r, entries in qa["source_bands"].items()}, output, arcpy)
        write_new(output / "build-receipt.json", built)
        reopened = panel.fresh_reopen(output)
        write_new(output / "reopen-receipt.json", reopened)
        return {"status": "pass_local_visual_panel_only", "built": built, "reopened": reopened}
    finally:
        panel.PRODUCTS = old


def stage_roots(stage):
    if not re.fullmatch(r"pair-[12]-qa-real-\d{3}|panel-real-\d{3}", stage):
        raise policy.PolicyStop("stage_identity_invalid")
    return tuple(DATA / directory / SCOPE / stage for directory in ("processing", ".attempt-events", ".attempt-fallback"))


def pair_outcomes(selection):
    outcomes = []
    for n in range(1, len(selection["pairs"]) + 1):
        path = DATA / "processing" / SCOPE / f"pair-{n}-qa-real-001" / "terminal.json"
        if not path.exists():
            break
        receipt = read(path)
        if receipt.get("status") != "pass_pair_visual_qa_only":
            raise policy.PolicyStop("prior_pair_hard_stop")
        outcomes.append(receipt)
        if receipt["full_both_aois"]:
            break
    return outcomes


def prepare_stage(initial_gate, stage, selection_path):
    validate_gate(initial_gate)
    selection = read(selection_path)
    outcomes = pair_outcomes(selection)
    attempt, events, fallback = stage_roots(stage)
    for path in (attempt, events, fallback):
        policy.safe_path(DATA, path)
        if path.exists():
            raise policy.PolicyStop("stage_already_consumed")
    if stage.startswith("pair-"):
        rank = int(stage[5])
        if rank == 2 and (len(outcomes) != 1 or outcomes[0]["full_both_aois"]):
            raise policy.PolicyStop("second_pair_not_released_by_ordinary_coverage_outcome")
    else:
        rank = choose_panel(outcomes, len(selection["pairs"]))
        if rank is None:
            raise policy.PolicyStop("no_qualifying_visual_pair")
    pair = selected_pair(selection, rank)
    checks = {}
    for role in ("before", "after"):
        _, verified = source_receipt(pair[role])
        checks[role] = {"product_id": pair[role]["product_id"], "archive_sha256": verified["archive_sha256"]}
    return {**initial_gate, "stage": stage, "rank": rank, "selection_ref": str(selection_path.relative_to(DATA)),
            "selection_sha256": sha(selection_path), "source_archive_checks": checks,
            "recovery_approval_sha256": policy.APPROVAL_SHA, "recovery_attempt_root_absent": True,
            "independent_event_roots_absent": True, "at_utc": now()}


@contextmanager
def supervisor_binding():
    old_sha, old_statuses = durable.APPROVAL_SHA, durable.WORKER_STATUSES
    try:
        durable.APPROVAL_SHA = policy.APPROVAL_SHA
        durable.WORKER_STATUSES = old_statuses | {"pass_pair_visual_qa_only", "pass_local_visual_panel_only"}
        yield
    finally:
        durable.APPROVAL_SHA, durable.WORKER_STATUSES = old_sha, old_statuses


def supervise_stage(gate_path, *, roots=None, worker=None):
    gate = read(gate_path)
    validate_gate(gate)
    attempt, events, fallback = roots or stage_roots(gate["stage"])
    if worker is None:
        def worker(path):
            with open(os.devnull, "wb") as sink:
                return subprocess.run([str(RUNTIME), str(Path(__file__).resolve()), "worker", "--gate", str(path)],
                                      stdout=sink, stderr=sink, timeout=14400, check=False).returncode
    with supervisor_binding():
        return durable.supervise(gate_path, attempt=attempt, events=events, fallback=fallback, worker=worker)


def worker_once(gate_path):
    gate = read(gate_path)
    validate_gate(gate)
    attempt, events, fallback = stage_roots(gate["stage"])
    if (read(events / "intent.json")["gate_sha256"] != sha(gate_path)
            or not (events / "worker-start.json").is_file() or not (fallback / "ready.json").is_file()):
        raise policy.PolicyStop("worker_supervision_gate_invalid")
    write_new(events / "worker-claim.json", {"status": "one_worker_claimed", "at_utc": now()})
    result = {"status": "blocked_terminal_no_retry", "stage": "worker_start", "reason": "unclassified_route_failure"}
    try:
        selection_path = DATA / gate["selection_ref"]
        policy.safe_path(DATA, selection_path)
        if sha(selection_path) != gate["selection_sha256"]:
            raise policy.PolicyStop("selection_manifest_drift")
        selection = read(selection_path)
        pair = selected_pair(selection, gate["rank"])
        for role in ("before", "after"):
            _, verified = source_receipt(pair[role])
            if verified["archive_sha256"] != gate["source_archive_checks"][role]["archive_sha256"]:
                raise policy.PolicyStop("stage_source_identity_drift")
        write_new(events / "arcpy-import-start.json", {"at_utc": now()})
        import arcpy
        write_new(events / "arcpy-import-pass.json", {"at_utc": now()})
        if gate["stage"].startswith("pair-"):
            result = pair_qa_once(pair, attempt, events, arcpy)
        else:
            chosen = choose_panel(pair_outcomes(selection), len(selection["pairs"]))
            if chosen != gate["rank"]:
                raise policy.PolicyStop("panel_selection_order_drift")
            attempt.mkdir(parents=True, exist_ok=False)
            result = build_selected(pair, DATA / "processing" / SCOPE / f"pair-{chosen}-qa-real-001", attempt / "panel", arcpy)
    except BaseException as exc:
        # Keep fixed method codes without capturing arbitrary ArcPy text.
        allowed = isinstance(exc, (policy.PolicyStop, frozen.RouteStop, frozen.PixelMethodError,
                                   metadata.MetadataError, metadata.identity.BundleIntegrityError))
        code = str(exc) if allowed and re.fullmatch(r"[a-z0-9_]+", str(exc)) else "local_io_or_unexpected_failure"
        result.update({"status": "blocked_terminal_no_retry", "reason": code, "exception_class": durable.safe_exception(exc)})
    result.update({"at_utc": now(), "stage_gate_sha256": sha(gate_path), "selection_sha256": gate["selection_sha256"]})
    try:
        attempt.mkdir(parents=True, exist_ok=True)
        write_new(attempt / "terminal.json", result)
    except BaseException:
        write_new(fallback / "worker-terminal.json", result)
    write_new(fallback / "worker-cleanup.json", {"status": "attempt_inputs_and_outputs_retained", "at_utc": now()})
    return 0 if result["status"].startswith("pass_") else 20


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "discover", "stage-preflight", "supervise", "worker"))
    parser.add_argument("--public-ci-commit", default="")
    parser.add_argument("--public-ci-run", default="")
    parser.add_argument("--gate")
    parser.add_argument("--output")
    parser.add_argument("--stage")
    parser.add_argument("--selection")
    parser.add_argument("--mechanical-metadata-recovery", action="store_true")
    args = parser.parse_args()
    try:
        if args.mode == "worker":
            return worker_once(Path(args.gate))
        if args.mode == "preflight":
            result = preflight(args.public_ci_commit, args.public_ci_run, args.mechanical_metadata_recovery)
        elif args.mode == "discover":
            result = discovery_once(read(args.gate))
        elif args.mode == "stage-preflight":
            result = prepare_stage(read(args.gate), args.stage, Path(args.selection))
        else:
            result = supervise_stage(Path(args.gate))
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            write_new(output, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"].startswith(("pass_", "defer_")) else 20
    except BaseException as exc:
        print(json.dumps({"status": "stopped", "code": str(exc) if isinstance(exc, policy.PolicyStop) else "unclassified_route_failure"}))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
