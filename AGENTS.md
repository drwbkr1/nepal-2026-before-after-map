# Project instructions

## Purpose

Maintain an evidence-bound, ArcGIS-ready before/after map of the 26 August 2026 Nepal debris avalanche and flash flood.

## Current authority

The long-term goal is active. The active milestone contract is `contracts/milestone-001.json` and the routing manifest is `records/project-control-profile.json`. Consume only the action classes in those records.

Full satellite-product downloads, credential use, provider terms acceptance, spending, repository-license selection, high-resolution restricted imagery, scientific-claim publication, and irreversible external actions remain human gates unless a later exact contract grants them.

## Source and custody rules

- Treat catalog results as availability evidence, not proof of usable pixels, valid coverage, or event causation.
- Record exact product identity, provider, acquisition time, rights, query, checksum, coverage assessment, and disposition before scientific use.
- Preserve rejected, failed, inconclusive, invalid, superseded, and masked observations.
- Never tune dates or thresholds solely to obtain a visually stronger result.
- Keep credentials, raw archives, SAFE directories, rasters, geodatabases, packages, and licensed high-resolution imagery outside Git.
- Do not imply that public repository visibility changes third-party data rights.

## Scientific claim rules

- Separate observation, interpretation, and attribution.
- Use “satellite-observed change” unless causation is supported by event timing, geometry, independent evidence, and documented review.
- Every mapped feature must retain source dates, sensor, method, confidence, and review status.
- Cloud, shadow, snow, radar layover, radar shadow, speckle, registration error, and terrain effects must be represented as limitations or exclusion masks.

## Working rules

- Verify the branch, commit, worktree, active contract, and current checkpoint before consequential writes.
- Run `python scripts/check_project.py` after changing project controls.
- Validate the control profile and milestone contract with their project validators.
- Preserve evidence receipts in `records/` and keep heavy data outside Git.
- Update status and handoff records when current truth changes.
