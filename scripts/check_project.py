#!/usr/bin/env python3
"""Validate the lightweight public project repository."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "AGENTS.md",
    "docs/PROJECT_CHARTER.md",
    "docs/ROADMAP.md",
    "docs/DATA_AND_METHODS_PLAN.md",
    "docs/SOURCES.md",
    "docs/ARCGIS_DELIVERY_PLAN.md",
    "docs/VALIDATION.md",
    "docs/STATUS.md",
    "docs/DECISIONS.md",
    "contracts/milestone-001.json",
    "records/project-control-profile.json",
    "records/long-term-goal.json",
    "records/evidence-ledger.jsonl",
]

FORBIDDEN_SUFFIXES = {
    ".tif", ".tiff", ".jp2", ".img", ".nc", ".hdf", ".h5",
    ".zip", ".7z", ".gpkg", ".shp", ".ppkx", ".mpkx", ".lpkx", ".slpk",
}

FORBIDDEN_NAME_PARTS = (
    "credential", "secret", "access_token", "refresh_token", "private_key",
)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    profile = json.loads((ROOT / "records/project-control-profile.json").read_text(encoding="utf-8"))
    contract = json.loads((ROOT / "contracts/milestone-001.json").read_text(encoding="utf-8"))
    goal = json.loads((ROOT / "records/long-term-goal.json").read_text(encoding="utf-8"))

    if profile["project"]["name"] != ROOT.name:
        fail("project name does not match repository directory")
    if profile["project"]["repository_identity"]["default_branch"] != "main":
        fail("expected default branch must be main")
    if not (ROOT / "AGENTS.md").read_text(encoding="utf-8").strip():
        fail("AGENTS.md must contain controlling project instructions")
    if goal["status"] != "active":
        fail("long-term goal record must be active")
    if contract["project_profile_ref"] != "records/project-control-profile.json":
        fail("milestone must reference the project control profile")
    if contract["status"] != "active":
        fail("M1 must be active after goal activation")
    if contract["authority"]["mode"] != "inherited":
        fail("active M1 must inherit the exact user authority")
    if profile["authority"]["authority_ref"] != contract["authority"]["authority_ref"]:
        fail("profile and milestone authority references must agree")
    prohibited = set(contract["scope"]["forbidden_work"])
    if "download full satellite products" not in prohibited:
        fail("full satellite-product acquisition must remain prohibited in M1")

    for number, line in enumerate(
        (ROOT / "records/evidence-ledger.jsonl").read_text(encoding="utf-8").splitlines(), 1
    ):
        if line.strip():
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                fail(f"invalid evidence ledger JSON on line {number}: {exc}")

    violations = []
    for relative in tracked_files():
        path = Path(relative)
        lower = relative.lower()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(relative)
        if any(part in lower for part in FORBIDDEN_NAME_PARTS):
            violations.append(relative)
        if ".safe/" in lower or ".gdb/" in lower:
            violations.append(relative)
    if violations:
        fail("forbidden tracked artifacts: " + ", ".join(sorted(set(violations))))

    print(f"PASS: {len(REQUIRED)} required files, JSON controls, and Git artifact boundaries validated.")


if __name__ == "__main__":
    main()
