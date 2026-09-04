# Project instructions

## Purpose

Maintain an evidence-bound, ArcGIS-ready before/after map of the 26 August 2026 Nepal debris avalanche and flash flood.

## Current authority

The long-term goal is active, M1 is complete, and `contracts/milestone-002.json` is the active acquisition milestone. `contracts/milestone-002-proposal.json` remains immutable proposal evidence, while `records/project-control-profile.json` is the routing manifest.

The exact M2 activation was approved and reconciled on 3 September 2026. The live source/path/storage preflight passed, and controlled external custody is at `C:\Projects\Active\nepal-2026-before-after-map-data`. The current checkpoint is `M2-ACQUISITION-REVIEW`: `M1-SRC-001` through `M1-SRC-003` are promoted and passed offline container verification, while `M1-SRC-004` failed exact-length verification after 561,593,598 of 1,732,332,897 bytes and its partial is retained. Four sources remain authorized and unattempted. Do not delete or resume the partial, retry `M1-SRC-004`, or continue another Sentinel transfer until the retained-failure review is completed. The runner emits lowercase schema-compatible attempt IDs; its historical readiness evidence remains retained. Stop on interactive login, MFA, recovery, new terms, identity drift, a paid route, unsafe paths, collision, or any additional transfer failure.

The current blank recovery review bundle has SHA-256 `dffa194cc91636a35b5f55af6ece32bb6eb90d77b65ea3d9865413f912d146e7` and binds proposal SHA-256 `7b8b5e83265b37962f879ca7dad85ab5f5c04ceb28ee0f15fa774a79df7fd013`. It contains zero human decisions. A future approval may release only one fresh byte-zero transfer of the same exact `M1-SRC-004` through a distinct exclusive staging identity, preservation of the failed partial and events, and post-success continuation of only the four still-unattempted products. Do not treat the prepared bundle as approval.

One owner-run `M1-SRC-001` invocation later stopped before its started-event boundary because the rendered CDSE terms-page SHA-256 changed. Live reconciliation at `2026-09-04T03:41:36Z` confirmed zero Sentinel attempts, zero Sentinel custody files, all eight exact products still online and unchanged, the same structured terms-document modification date, all six scope-relevant legal statements, and the unchanged linked Sentinel Data Legal Notice. `records/acquisition/preflight-refresh.json` now supplements the immutable initial preflight. The runner binds the terms content by its normalized legal section while retaining exact-byte checks for the OData documentation, token documentation, and Sentinel Legal Notice. Any legal-section, structured modification-date, legal-notice, account, or terms-acceptance change still stops before mutation. No credential value was read or recorded during the refresh.

At `2026-09-04T04:50:25Z`, `records/acquisition/sentinel-acquisition-reconciliation-001.json` reconciled three exact promoted Sentinel-1 archives and three passing container-only receipts, plus the retained `M1-SRC-004` truncation. The active intake validates locally with four authorized, one failed, and three promoted assets. No credential value is present in project evidence, and no raster readability, AOI coverage, pixel usability, registration, or scientific change is established.

The base M2 contract permits acquisition and verification of only the eight exact reviewed Sentinel products. Separate approved amendments cover four exact Copernicus DEM tiles and four exact S1D `AUX_RESORB` files; each retains its own prerequisites and custody controls. No approval permits provider-terms acceptance, account creation or recovery, credential disclosure, spending, repository-license selection, high-resolution restricted imagery, scientific-claim publication, or irreversible external actions outside its exact boundary.

ArcGIS Pro terrain correction has a separately approved DEM workstream. The owner approved review bundle SHA-256 `caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e`, proposal SHA-256 `92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69`, and exact license document SHA-256 `9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd`. `records/source-gates/m2-dem-amendment-approval.json` authorizes only a fresh preflight, anonymous acquisition of the four named Copernicus DEM GLO-30 tiles, verification, non-Git custody, and the bounded radar-processing use. This does not replace or resolve the separate eight-product Sentinel retained-failure review.

`contracts/m2-dem-intake.json` and `contracts/m2-dem-offline-verification.json` are the active DEM controls. All four exact tiles were acquired one at a time through append-only staging, local SHA-256 and length verification, and atomic no-replace promotion. ArcGIS Pro 3.7.1 read all four exact rasters, confirmed their declared structure, and scanned 51,840,000 finite non-NoData cells with zero NoData or nonfinite cells; all approved AOI bounds fall within that verified four-tile footprint. The fixed attempt-003 terrain screen also passed all four tile checks, four seam checks, the AOI slope screen, EPSG:32645 projection, stable-output reconciliation, and PNG/PDF visual criteria. Its 189 stable derived files remain outside Git and the two earlier terrain-wrapper failures remain immutable. This establishes gross-artifact and map-surface fitness only. The current parallel checkpoint remains `M2-DEM-VERTICAL-DATUM-REVIEW`: review bundle SHA-256 `9b40e81df766ea866c5bff51cdbc4d83e7e7da6a554fb1709fc553d8221bebbc` proposes the exact EGM2008 one-minute preconversion route, but contains zero human decisions. The required ArcGIS Coordinate Systems Data component is absent and remains owner-controlled. Vertical-datum fitness, independent elevation accuracy, pair-specific radar fitness, radar processing, and scientific fitness are not established. The candidate controls remain immutable historical evidence, and their verifier must still refuse execution. Do not silently choose `GEOID` or `NONE` for the EGM2008 orthometric DEM; the vertical gate must be resolved before radar terrain correction.

`config/qa/dem-terrain-quality-contract.json` predeclares an independent read-only terrain-quality check. Attempt-001 failed before opening a DEM because its external root omitted the active `custody` segment. Attempt-002 created outputs but failed before its manifest and receipt because the inventory opened a transient geodatabase lock. Preserve both failure receipts and external attempt directories; never reuse their paths. `config/qa/dem-terrain-quality-contract-attempt-003.json` changes only stable-inventory handling and the exclusive output path. It may read only the same four exact promoted DEM tiles, excludes only `.lock` files while hashing every stable artifact, applies no vertical transform, and may not publish DEM-derived raster imagery. Preserve any failed attempt and do not change thresholds after metrics are observed.

The terrain-screen result has a separate human gate at `M2-DEM-TERRAIN-RESULT-REVIEW`. Review bundle SHA-256 `834ad354fc134b2017afdd3b238c1a6271276e8b1a95776e434180c7283a26d5` contains a text-only summary and binds the external APRX, PDF, PNG, and manifest through `records/surface-receipts/m2-dem-terrain-quality.json`; it contains zero human decisions. Approval may close only the owner terrain-result review gate after exact lock and reconciliation. It cannot select the vertical route, authorize installation or other data, run radar processing, or establish a scientific result.

Sentinel-1 orbit correction is approved, but acquisition is at `M2-ORBIT-ACQUISITION-REVIEW`. Review bundle SHA-256 `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1` and proposal SHA-256 `b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292` authorize only four exact S1D `AUX_RESORB` files for their six exact Sentinel source bindings. Preserve the failed first custody initialization and its bounded correction. Also preserve the test-induced `M2-ORB-001` attempt and events: a tracked nonsecret literal reached a rejected download request, received zero payload bytes, and created no payload file. The corrected runner must stop with `sentinel_verification_unit_not_complete` before catalogue access, token lookup, events, or payload requests until the full `M2-VERIFY` unit is complete. Orbit recovery bundle SHA-256 `df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b` binds proposal SHA-256 `ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a`, remains blank, and releases no action. Do not retry or continue orbit acquisition without the exact owner decision. Do not silently substitute a later `AUX_POEORB` file. The DEM vertical-datum and terrain-result gates, Sentinel custody, pixel readiness, radar processing, and scientific claims remain separate.

Preserve the test-induced `M1-SRC-001` materialization attempt `fixture-must-not-run` and its explicit provenance. Also preserve the planned `M1-SRC-002` and `M1-SRC-003` materializations. Across the three append-only attempts, all 78 files and 5,183,550,209 extracted bytes match their manifests. They establish no raster readability, pixel usability, baseline, change, or scientific admission and release no downstream processing by themselves. Do not materialize failed or unattempted sources.

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
