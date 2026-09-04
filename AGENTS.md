# Project instructions

## Purpose

Maintain an evidence-bound, ArcGIS-ready before/after map of the 26 August 2026 Nepal debris avalanche and flash flood.

## Current authority

The long-term goal is active, M1 is complete, and `contracts/milestone-002.json` is the active acquisition milestone. `contracts/milestone-002-proposal.json` remains immutable proposal evidence, while `records/project-control-profile.json` is the routing manifest.

The exact M2 activation was approved and reconciled on 3 September 2026. The live source/path/storage preflight passed, and the empty external custody structure was initialized at `C:\Projects\Active\nepal-2026-before-after-map-data`. The current checkpoint is `M2-AUTHENTICATION-REFERENCE`: do not attempt a product transfer until a secret-safe reference to an existing owner-controlled CDSE credential or authenticated session is available. The unattempted Sentinel transfer runner now emits lowercase schema-compatible attempt IDs; its historical readiness receipt and prospective correction are both retained. Stop on interactive login, MFA, recovery, new terms, identity drift, a paid route, unsafe paths, or collision.

The active contract permits acquisition and verification of only the eight exact reviewed products. It does not permit provider-terms acceptance, account creation or recovery, credential disclosure, spending, repository-license selection, high-resolution restricted imagery, scientific-claim publication, or irreversible external actions outside its exact boundary.

ArcGIS Pro terrain correction has a separately approved DEM workstream. The owner approved review bundle SHA-256 `caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e`, proposal SHA-256 `92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69`, and exact license document SHA-256 `9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd`. `records/source-gates/m2-dem-amendment-approval.json` authorizes only a fresh preflight, anonymous acquisition of the four named Copernicus DEM GLO-30 tiles, verification, non-Git custody, and the bounded radar-processing use. This does not replace or resolve the separate eight-product CDSE authentication checkpoint.

`contracts/m2-dem-intake.json` and `contracts/m2-dem-offline-verification.json` are the active DEM controls. All four exact tiles were acquired one at a time through append-only staging, local SHA-256 and length verification, and atomic no-replace promotion. ArcGIS Pro 3.7.1 read all four exact rasters, confirmed their declared structure, and scanned 51,840,000 finite non-NoData cells with zero NoData or nonfinite cells; all approved AOI bounds fall within that verified four-tile footprint. The fixed attempt-003 terrain screen also passed all four tile checks, four seam checks, the AOI slope screen, EPSG:32645 projection, stable-output reconciliation, and PNG/PDF visual criteria. Its 189 stable derived files remain outside Git and the two earlier terrain-wrapper failures remain immutable. This establishes gross-artifact and map-surface fitness only. The current parallel checkpoint remains `M2-DEM-VERTICAL-DATUM-REVIEW`: review bundle SHA-256 `9b40e81df766ea866c5bff51cdbc4d83e7e7da6a554fb1709fc553d8221bebbc` proposes the exact EGM2008 one-minute preconversion route, but contains zero human decisions. The required ArcGIS Coordinate Systems Data component is absent and remains owner-controlled. Vertical-datum fitness, independent elevation accuracy, pair-specific radar fitness, radar processing, and scientific fitness are not established. The candidate controls remain immutable historical evidence, and their verifier must still refuse execution. Do not silently choose `GEOID` or `NONE` for the EGM2008 orthometric DEM, and do not download updated orbit vectors: both require their recorded dependency conditions to be resolved first.

`config/qa/dem-terrain-quality-contract.json` predeclares an independent read-only terrain-quality check. Attempt-001 failed before opening a DEM because its external root omitted the active `custody` segment. Attempt-002 created outputs but failed before its manifest and receipt because the inventory opened a transient geodatabase lock. Preserve both failure receipts and external attempt directories; never reuse their paths. `config/qa/dem-terrain-quality-contract-attempt-003.json` changes only stable-inventory handling and the exclusive output path. It may read only the same four exact promoted DEM tiles, excludes only `.lock` files while hashing every stable artifact, applies no vertical transform, and may not publish DEM-derived raster imagery. Preserve any failed attempt and do not change thresholds after metrics are observed.

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
