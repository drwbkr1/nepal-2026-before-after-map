# Project instructions

## Purpose

Maintain an evidence-bound, ArcGIS-ready before/after map of the 26 August 2026 Nepal debris avalanche and flash flood.

## Current authority

The long-term goal is active, M1 is complete, and `contracts/milestone-002.json` is the active acquisition milestone. `contracts/milestone-002-proposal.json` remains immutable proposal evidence, while `records/project-control-profile.json` is the routing manifest.

The exact M2 activation was approved and reconciled on 3 September 2026. The live source/path/storage preflight passed, and the empty external custody structure was initialized at `C:\Projects\Active\nepal-2026-before-after-map-data`. The current checkpoint is `M2-AUTHENTICATION-REFERENCE`: do not attempt a product transfer until a secret-safe reference to an existing owner-controlled CDSE credential or authenticated session is available. Stop on interactive login, MFA, recovery, new terms, identity drift, a paid route, unsafe paths, or collision.

The active contract permits acquisition and verification of only the eight exact reviewed products. It does not permit provider-terms acceptance, account creation or recovery, credential disclosure, spending, repository-license selection, high-resolution restricted imagery, scientific-claim publication, or irreversible external actions outside its exact boundary.

ArcGIS Pro terrain correction has a separate pending dependency gate. `contracts/milestone-002-dem-amendment-proposal.json` and `reviews/m2-dem-amendment/review-bundle.json` identify four exact Copernicus DEM GLO-30 tiles and a license requiring owner acceptance. They are non-authorizing. Do not request DEM payload bytes, accept the license, register for CCM access, generate S3 credentials, or process DEM pixels until the exact amendment is approved and reconciled. This pending gate does not replace the current eight-product CDSE authentication checkpoint.

`contracts/m2-dem-intake-candidate.json`, `contracts/m2-dem-offline-verification-candidate.json`, and `config/qa/radar-baseline-processing-contract.json` are predeclared controls only. The candidate verifier must refuse execution. Do not silently choose `GEOID` or `NONE` for the EGM2008 orthometric DEM, and do not download updated orbit vectors: both require their recorded dependency conditions to be resolved first.

`config/qa/optical-baseline-processing-contract.json` is the predeclared Sentinel-2 route. Do not replace metadata-derived BOA offsets with an unchecked divide-by-10,000 rule, clamp valid reflectance values, change the conservative SCL classes, harmonize over event pixels, or tune cloud masks to recover a stronger result. Preserve an inconclusive optical route.

`contracts/m2-materialization.json` is the active but gate-deferred SAFE extraction control for the same eight products. It may run only after an exact promoted intake identity and matching `pass_container_only` receipt. Keep every complete, partial, and failed attempt outside Git; never reuse an attempt path or treat materialization as raster or pixel fitness.

`config/qa/optical-input-readiness-contract.json` is the next Sentinel-2 gate. It may inspect only the exact materialized RUM pair after two passing materialization receipts. Header and metadata readiness permits later pixel QA only; do not treat a readable JP2, matching grid, or parsed scaling field as usable-pixel or change evidence.

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
