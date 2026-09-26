"""Pure, no-network guards for the approved ASF HyP3 RTC map route."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_REF = "records/observations/m2-asf-rtc-four-scene-candidate-001-local.json"
CANDIDATE_SHA256 = "d18d0b9e47892e5930bd306fb196d8f49884e773b5b9e8495018e3b2c7c138ba"
PROPOSAL_REF = "contracts/milestone-002-asf-hyp3-rtc-map-route-001-proposal.json"
PROPOSAL_SHA256 = "5118b0bb3727e9ef6080bed9015a68cd64bbbba226dc422948ec5cac294fbb55"
BUNDLE_REF = "reviews/m2-asf-hyp3-rtc-map-route-001/review-bundle.json"
BUNDLE_SHA256 = "f6afe7e4f5b1210c6d614ca4ba7c701b8a016bc773825f72cf1eb16d07a8bdca"
APPROVAL_REF = "records/source-gates/m2-asf-hyp3-rtc-map-route-001-approval.json"
ORDER = ("M1-SRC-002", "M1-SRC-005", "M1-SRC-001", "M1-SRC-004")
PER_JOB_CREDIT_CEILING = 60
TOTAL_CREDIT_CEILING = 240
PARAMETERS = {
    "resolution": 10.0,
    "dem_name": "copernicus",
    "radiometry": "gamma0",
    "scale": "power",
    "speckle_filter": False,
    "dem_matching": False,
    "include_dem": True,
    "include_inc_map": True,
    "include_scattering_area": True,
    "include_rgb": False,
}


class RouteStop(ValueError):
    """A fail-closed, nonsecret route-control failure."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _read_bound_json(root: Path, ref: str, expected_sha256: str) -> dict:
    path = root / ref
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise RouteStop("bound_file_identity_mismatch")
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        if isinstance(exc, RouteStop):
            raise
        raise RouteStop("bound_file_unreadable") from None
    if not isinstance(value, dict):
        raise RouteStop("bound_file_shape_invalid")
    return value


def load_approved_jobs(root: Path = ROOT) -> tuple[dict, ...]:
    """Return exact approved jobs after checking immutable identities."""
    _read_bound_json(root, PROPOSAL_REF, PROPOSAL_SHA256)
    _read_bound_json(root, BUNDLE_REF, BUNDLE_SHA256)
    approval = _read_bound_json(root, APPROVAL_REF, _approval_sha256(root))
    if (
        approval.get("decision") != "approve"
        or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA256
        or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA256
        or approval.get("authority", {}).get("at_most_one_job_per_exact_source_in_reviewed_order_after_gates") is not True
        or approval.get("authority", {}).get("no_paid_credits") is not True
    ):
        raise RouteStop("approval_boundary_invalid")
    candidate = _read_bound_json(root, CANDIDATE_REF, CANDIDATE_SHA256)
    jobs = candidate.get("candidate_jobs")
    if not isinstance(jobs, list) or len(jobs) != len(ORDER):
        raise RouteStop("candidate_job_count_invalid")
    if tuple(job.get("source_id") for job in jobs) != ORDER:
        raise RouteStop("candidate_order_invalid")
    allowed_job_keys = {"source_id", "event_role", "name", "job_type", "job_parameters"}
    for job in jobs:
        if set(job) != allowed_job_keys or job["job_type"] != "RTC_GAMMA":
            raise RouteStop("candidate_job_shape_invalid")
        params = job["job_parameters"]
        if set(params) != set(PARAMETERS) | {"granules"}:
            raise RouteStop("candidate_parameters_invalid")
        if any(type(params[key]) is not type(value) or params[key] != value for key, value in PARAMETERS.items()):
            raise RouteStop("candidate_method_changed")
        granules = params["granules"]
        if not isinstance(granules, list) or len(granules) != 1 or not isinstance(granules[0], str):
            raise RouteStop("candidate_granule_invalid")
        if not granules[0].startswith("S1D_IW_GRDH_1SDV_202608") or len(granules[0]) != 67:
            raise RouteStop("candidate_granule_invalid")
        if job["name"] != f"m2-rtc-002-{job['source_id'].lower()}":
            raise RouteStop("candidate_name_invalid")
    return tuple(jobs)


def _approval_sha256(root: Path) -> str:
    # Approval is append-only. Its recorded hash is fixed by the public review gate.
    gate = root / "records/readiness/m2-asf-hyp3-rtc-map-route-001-review-publication-gate.json"
    try:
        data = json.loads(gate.read_text(encoding="utf-8"))
        if data.get("status") != "pass_exact_review_packet_public_ci_only":
            raise RouteStop("review_publication_gate_missing")
        value = data["bindings"]["owner_approval_sha256"]
    except (OSError, KeyError, ValueError):
        raise RouteStop("review_publication_gate_missing") from None
    if value != "1c3103429418f1c1847fa5865f5634b6dece7acd8cd19e42a279537709087596":
        raise RouteStop("review_publication_gate_identity_mismatch")
    return value


def one_job_payload(jobs: tuple[dict, ...], source_id: str) -> dict:
    """Build only a single exact job; never batch or silently submit another source."""
    if tuple(job["source_id"] for job in jobs) != ORDER or source_id not in ORDER:
        raise RouteStop("job_order_or_source_invalid")
    job = next(item for item in jobs if item["source_id"] == source_id)
    return {"jobs": [{key: job[key] for key in ("name", "job_type", "job_parameters")}], "validate_only": False}


def check_free_credits(account: dict, *, required_jobs: int = 1) -> float | int:
    """Check free Basic capacity without retaining account identifiers."""
    if not isinstance(account, dict) or not 1 <= required_jobs <= 4:
        raise RouteStop("account_or_job_count_invalid")
    value = account.get("remaining_credits")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RouteStop("free_credit_balance_unknown")
    if value < required_jobs * PER_JOB_CREDIT_CEILING:
        raise RouteStop("insufficient_free_credits")
    # The API's application_status field is not documented as a Basic-service
    # eligibility decision. A validate-only exact-job response checks that.
    return value


def inspect_submission(reply: dict, expected_job: dict) -> dict:
    """Extract a nonsecret exact-job receipt; ambiguous responses stop the route."""
    if not isinstance(reply, dict) or reply.get("validate_only") is not False:
        raise RouteStop("submission_response_invalid")
    jobs = reply.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 1:
        raise RouteStop("submission_response_ambiguous")
    actual = jobs[0]
    if not isinstance(actual, dict):
        raise RouteStop("submission_response_invalid")
    if any(actual.get(key) != expected_job[key] for key in ("name", "job_type", "job_parameters")):
        raise RouteStop("submission_identity_mismatch")
    job_id = actual.get("job_id")
    if not isinstance(job_id, str) or len(job_id) != 36:
        raise RouteStop("submission_job_id_missing")
    cost = actual.get("credit_cost")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or not 0 <= cost <= PER_JOB_CREDIT_CEILING:
        raise RouteStop("submission_credit_cost_invalid")
    status = actual.get("status_code")
    if status not in {"PENDING", "RUNNING", "SUCCEEDED"}:
        raise RouteStop("submission_not_accepted")
    return {
        "job_id": job_id,
        "name": actual["name"],
        "job_type": actual["job_type"],
        "job_parameters": actual["job_parameters"],
        "request_time": actual.get("request_time"),
        "status_code": status,
        "credit_cost": cost,
    }
