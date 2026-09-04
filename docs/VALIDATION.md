# Validation plan

Validation is staged. Passing repository checks does not validate pixels or scientific conclusions.

## Repository validation

`scripts/check_project.py` verifies:

- required charter, status, contract, and control files exist;
- JSON records parse;
- expected identifiers and project paths agree;
- forbidden large geospatial formats and obvious credential files are not tracked.

GitHub Actions runs the same check on pushes and pull requests.

The current repository check also validates the exact M2 approval and reconciliation, active contract, live source gate, non-mutating preflight, initialized-custody receipt, active intake contract, authentication stop, and three independent candidate before/after routes. It does not access the external custody root in CI or treat the public receipt as proof that another machine has the local data directory.

Portable unit tests also verify the ArcGIS evidence schema, the separation of observation, interpretation, and attribution, required adverse states, initial empty scientific state, receipt bindings, preview hash, and retained failures:

```powershell
python -m unittest tests.test_arcgis_evidence_schema -v
```

## M2 activation, preflight, and intake validation

The active M2 records can be checked with the project and skill validators:

```powershell
python scripts/check_project.py
python C:\Users\drewb\.codex\skills\standardize-project-control-plane\scripts\validate_project_control.py records/project-control-profile.json --project-root . --verify-paths --milestone-contract contracts/milestone-002.json --as-of 2026-09-03T19:25:32Z
python C:\Users\drewb\.codex\skills\gate-external-sources\scripts\validate_source_gate.py records/source-gates/m2-live-source-gate.json --as-of 2026-09-03T17:31:17Z
python C:\Users\drewb\.codex\skills\intake-controlled-data\scripts\validate_intake_contract.py contracts/m2-intake.json --project-root C:\Projects\Active --json
python C:\Users\drewb\.codex\skills\run-controlled-milestone\scripts\validate_milestone.py contracts/milestone-002.json --project-profile records/project-control-profile.json --as-of 2026-09-03T17:35:43Z
```

The profile binds `M2-CUSTODY-PREFLIGHT` and `M2-ACQUIRE` directly to the exact completed M2 activation approval, so the combined profile/milestone lint has no gate findings. Its advisory that `data_processing` has no blanket default classification is intentional; the active milestone supplies only its bounded processing authority. The live record proves only the source and custody preflight at its stated timestamp. It does not prove an authenticated transfer, current future availability, local bytes, valid product containers, usable pixels, or scientific fitness.

The transfer state machine has a separate network-free suite:

```powershell
python -m unittest tests.test_m2_transfer_core -v
```

The suite verifies missing-reference refusal without intake mutation, exclusive staging, streamed hashes, mismatch retention, redirect refusal, path containment, receipt no-replacement, failed-attempt history, destination collision preservation, and atomic no-replace promotion. The passing readiness receipt is synthetic/local evidence only and does not establish real CDSE behavior or product integrity.

The mutable active intake has a separate progress validator:

```powershell
python -m unittest tests.test_m2_acquisition_progress -v
python scripts/validate_m2_acquisition_progress.py
python scripts/validate_m2_acquisition_progress.py --verify-external
```

The first command exercises authorized, staging, failed, and promoted states plus identity drift, missing receipt, and secret-bearing-key failures. The repository-only command validates portable state and receipt evidence without touching the sibling data root. The external command additionally reconciles the controlled staging and custody paths; for promoted products it re-hashes the retained archive, so it may be slow after acquisition. Neither command reads the credential environment variable or performs a network request.

Checkpoint reconciliation remains a separate read-only derivation:

```powershell
python -m unittest tests.test_m2_checkpoint_reconciliation -v
python scripts/derive_m2_acquisition_checkpoint.py --verify-external
```

The derivation must match both `records/project-control-profile.json` and `records/long-term-goal.json` to pass. When they differ after a real attempt, use a new `--candidate-output-root scratch/<unique-attempt>` to emit exclusive candidate controls for review; the tool never overwrites tracked truth.

The portable unit test invokes the derivation without `--verify-external`, because CI does not own the operator's external custody roots. The separate local command above performs the read-only external reconciliation when those roots exist. Failed GitHub Actions run `33800916326` is retained in the portability-correction receipt as the evidence that exposed this boundary error.

The active offline-verification binding and wrapper stop are tested separately:

```powershell
python -m unittest tests.test_m2_active_verification -v
```

These tests verify exact inheritance from the M2 approval, preservation of all eight candidate container profiles, offline/read-only behavior, and refusal before custody access when an asset has not been promoted.

## M2 DEM amendment activation validation

The exact review artifacts remain immutable and the active amendment can be validated without requesting a DEM payload:

```powershell
python C:\Users\drewb\.codex\skills\gate-external-sources\scripts\validate_source_gate.py records/source-gates/m2-dem-source-gate.json --validate-only
python C:\Users\drewb\.codex\skills\conduct-human-review\scripts\prepare_review_bundle.py reviews/m2-dem-amendment/review-bundle.json --project-root .
python -m unittest tests.test_m2_dem_amendment -v
python -m unittest tests.test_m2_dem_activation -v
python -m unittest tests.test_m2_dem_preflight -v
python -m unittest tests.test_m2_dem_transfer -v
python C:\Users\drewb\.codex\skills\intake-controlled-data\scripts\validate_intake_contract.py contracts/m2-dem-intake.json --project-root C:\Projects\Active --json
python C:\Users\drewb\.codex\skills\run-controlled-milestone\scripts\validate_milestone.py contracts/milestone-002.json --project-profile records/project-control-profile.json --as-of 2026-09-03T20:27:26Z
```

The historical source-gate validator must still report its immutable pre-decision **blocked** result; activation does not rewrite it. Before activation, `scripts/activate_m2_dem_amendment.py --activated-at-utc 2026-09-03T20:27:26Z --verify-only` passed against the then-pending control profile. That one-way derivation command is not rerunnable against the already activated profile. Current-state validation uses the activation suite and repository checker. They require the exact review bundle, proposal, accepted license, locked response, and one-decision reconciliation; preserve the four-item, 170,302,058-byte set; require four authorized unattempted intake entries; and keep verification gate-deferred. The activation suite covers exact current bindings and the no-network/no-payload boundary.

The full repository suite currently passes 164 tests, and `scripts/check_project.py` validates 162 required files. Eight activation-stage fail-closed results are retained in `EVID-0031`. Four exposed checker integration errors: a DEM-unit lookup used the M1 unit map; historical Sentinel readiness records and the transfer verifier were compared to the newly amended M2 hash; and the published portability correction was compared to the current checker instead of its immutable checker hash. Four more protected immutable controls: attempted status edits changed the bound review and DEM protocol files, one validation command used the wrong timestamp flag, and the one-way activation generator was rerun against an already active profile. Every issue was corrected before publication and changed no external data, approval evidence, or payload state.

The live preflight test suite validates exact STAC and object-header comparisons, redirect refusal, remote-identity drift, no-payload evidence, empty-custody binding, and the transition to `M2-DEM-ACQUISITION`. `EVID-0032` retains the initial checker failure caused by its old preflight-checkpoint expectation; updating that expectation did not change the live evidence or external custody.

The current full repository suite passes 219 tests, and `scripts/check_project.py` validates 258 required files after adding the locked orbit approval, activation, fresh preflight, preserved custody-initialization failure and correction, completed empty custody, guarded transfer/EOF-verification controls, the retained active-intake schema failure and correction, and the retained stale activation-label finding and correction. Project-control and milestone validators pass. The two still-pending DEM review bundles report `ready_for_handoff`; the orbit bundle remains immutable historical review evidence whose exact decision has been locked, reconciled, and activated. Local reconciliation re-hashed all four promoted DEM files totaling 170,302,058 bytes. GitHub Actions run `33809208304` remains a failed historical result because its Linux runner lacked the external Windows custody root; the corrected portable test validates repository receipts without external access while production reconciliation still defaults to strict external checking.

The generic intake-contract validator separately reports four invalid attempt identifiers because the completed DEM transfer IDs contain uppercase RFC 3339 `T` and `Z` characters and its identifier grammar is lowercase-only. The immutable attempt receipts, checkpoint paths, and external event history are not rewritten. This retained schema-validation failure does not change the project-specific byte and custody passes or approve downstream processing; future transfer runners must correct identifier generation before use.

Before any Sentinel transfer, the unattempted runner was corrected to lowercase its generated attempt identifier while leaving RFC 3339 event timestamps unchanged. Eleven focused tests cover the generator and existing transfer controls, and the unchanged active Sentinel intake passes the generic validator. Receipt `records/acquisition/transfer-runner-attempt-id-correction.json` binds the current runner and tests without claiming authentication, network access, external mutation, or transfer.

The transfer-runner suite validates exact header matching, redirect and requester-charge failure, exclusive staging, streamed size and SHA-256, partial retention, and absence of any credential or authorization-header route. `EVID-0033` and the readiness receipt bind the exact runner and seven passing tests without claiming a live transfer.

## Historical static intake-control validation

Before activation or data transfer, the repository established that:

- the candidate intake contract binds the exact reviewed acquisition plan, proposed M2 contract, and pending activation bundle;
- all eight assets remain `planned` with no attempts and pending authorization;
- staging and final destinations are distinct, relative, collision-safe, and outside Git;
- download routes use the exact approved provider UUIDs over the documented CDSE HTTPS host without secret-bearing query values;
- catalog sizes and provider checksums are preserved as metadata without being mislabeled as authenticated transfer identity or local SHA-256;
- the dry-run record claims no network request, authenticated session, filesystem probe, directory creation, or acquisition authority;
- mutation tests reject authority drift, traversal, overwrite behavior, and product-set changes.

Run:

```powershell
python scripts/prepare_m2_intake.py --created-at 2026-09-02T04:46:03Z --verify-only
python -m unittest discover -s tests -v
```

## M2 offline container and readiness validation

Before activation, static verification confirms that the offline contract remains an exact derivation of the approved product set and that all data-readiness gates remain deferred:

```powershell
python scripts/prepare_m2_verification.py --created-at 2026-09-03T16:43:33Z --verify-only
python -m unittest tests.test_m2_verification -v
```

Synthetic fixtures test a valid Sentinel-1 member inventory, unsafe ZIP paths, missing custody files, authority drift, exact-byte regeneration, required Sentinel-2 bands and SCL, and the `defer` readiness result. Fixture success proves the checker behaves as specified; it is not evidence about the real products.

A later real scan must require an already-existing approved custody root and a new receipt path. It computes local SHA-256 and provider MD5, checks exact size, rejects unsafe or encrypted members, validates analysis-critical SAFE members, and runs CRC without extracting the archive. Even a container pass does not establish raster readability, AOI coverage, valid pixels, masks, registration, or scientific fitness.

## Pixel-readiness contract validation

The predeclared EPSG:32645 coverage, mask, grid, and registration decisions are implemented in a dependency-free core:

```powershell
python -m unittest tests.test_pixel_qa_core -v
```

ArcGIS Pro 3.7.1 Advanced and Spatial Analyst have also exercised the same core with deterministic 20 m synthetic rasters and all three approved AOIs. The native adapter verifies `TabulateArea` class-area accounting, an aligned before/after pair, a deliberately blocked 0.6-pixel origin shift, and the required `defer` state when registration has not been measured. See `docs/PIXEL_QA_PROTOCOL.md` for thresholds, class semantics, rerun commands, and the scientific claim boundary.

The Sentinel-2 processing contract also has a separate portable core and ArcGIS-native synthetic exercise. The adapter parses baseline 05.12 scaling metadata, preserves DN zero as NoData, applies the declared SCL exclusions, scales five bands to BOA reflectance, and checks NDVI, MNDWI, and NBR. Run the portable checks with `python -m unittest tests.test_optical_processing_core -v`; run the ArcGIS adapter using the new-attempt command in `docs/OPTICAL_BASELINE_PROCESSING_PROTOCOL.md`. Neither result is real-pixel evidence.

## DEM terrain-quality validation

The four exact promoted DEM hashes, four native seams, quantitative thresholds, EPSG:32645 processing, external-only outputs, and mandatory visual review are fixed before the first real terrain-quality run:

```powershell
python -m unittest tests.test_dem_terrain_quality_core -v
python scripts/check_project.py
```

Five portable tests cover continuous terrain, a moderate systematic seam offset, a gross seam and impossible elevation, nonfinite cells, decision precedence, and unsupported seam orientation. The first failed synthetic fixture remains recorded. Passing tests establish control behavior only; the predeclaration receipt records no real DEM read, ArcGIS execution, terrain-quality conclusion, vertical conversion, Sentinel processing, or scientific claim.

The first public terrain-control run, `33819299553`, passed the repository checker but failed because NumPy was absent from the Linux runner. Run `33819378562` then failed at workflow level with zero jobs; GitHub exposed no job log, so the record does not claim a more specific cause. The corrected workflow pins `numpy==2.5.1`, and run `33819458096` installed that exact version, validated 199 required files before the additive correction receipt, and passed all 190 tests. Correction-evidence run `33819677224` then exposed a CRLF-to-LF receipt-hash mismatch; the published blob and local working file were measured separately and the receipt was rewritten with explicit LF bytes. All three failed runs remain explicit evidence.

ArcGIS attempt-001 is also retained as a failed result. It stopped during strict resolution of the first source path before source open, byte hashing, pixel read, output-root creation, or metric calculation. The attempt-002 correction is validated as a path-only change: it adds the active `custody` segment, moves to a new exclusive output, and preserves the exact input assets, hashes, sizes, seams, metrics, thresholds, processing method, and no-vertical-transform boundary.

Attempt-002 is retained as a second failed result. It read all four exact sources, completed the ArcGIS raster and map creation, reverified unchanged source custody, and then failed before manifest and receipt creation while trying to hash a transient `.lock` file. The post-exit failed directory contains 189 stable files totaling 520,653,986 bytes, but its in-process metrics were not persisted and no terrain decision is admitted. Attempt-003 changes only inventory handling: basename-suffixed `.lock` files are listed as transient exclusions while every stable file remains hashed at a new exclusive output path.

Attempt-003 completed successfully under the published correction. All four tile evaluations, four native seam evaluations, the EPSG:32645 30 metre projection check, and the AOI slope evaluation passed. A separate post-exit pass re-hashed 189 of 189 stable files totaling 520,668,653 bytes, found no missing, unexpected, size-mismatched, hash-mismatched, or remaining `.lock` file, and independently reverified the four source hashes. The PNG and a 180 dpi rendering of the one-page PDF passed the five declared visual criteria. Key external identities are APRX `08829c97eeb831758573fbfc0146f09e5d1a39d342f313f5adab4ba2c6facc83`, PNG `39c63525171ae7cd24b540577079467c7efbaedb4aae959086e3f4d1a38ad811`, PDF `139e4a4f0f5a02018c824cbfc2f85ddcf3b1d1c4b8d477dd7936efc4d0f74d0b`, and manifest `6baf1ec47f4bc27c9dc2ab3501637690d717673e63d9e0f5036e1b2dc2ed1620`.

The dataset-readiness audit can be reproduced with:

```powershell
python C:\Users\drewb\.codex\skills\audit-dataset-readiness\scripts\audit_readiness.py audit --input records\readiness\m2-dem-terrain-readiness-input.json --output <new-exclusive-output>.json
```

The retained decision is `defer`, not `pass`: source/terms, custody, structure, coverage, and reproducibility pass, while vertical and independent elevation uncertainty, pair-specific radar fitness, and owner or independent expert result review remain unresolved. The audit created no authority and released no downstream action. Do not overwrite the retained decision file when independently rerunning the utility.

The owner terrain-result review packet is validated separately:

```powershell
python C:\Users\drewb\.codex\skills\conduct-human-review\scripts\prepare_review_bundle.py reviews\m2-dem-terrain-result\review-bundle.json --project-root .
python C:\Users\drewb\.codex\skills\conduct-human-review\scripts\review_response.py prepare --contract reviews\m2-dem-terrain-result\review-contract.json --output <new-exclusive-blank-response>.json
```

The bundle must report manifest SHA-256 `834ad354fc134b2017afdd3b238c1a6271276e8b1a95776e434180c7283a26d5`, seven verified tracked artifacts, and `ready_for_handoff`. Its text-only PNG was visually inspected at 1800 by 1680 pixels with no observed clipping, no selected decision, and no DEM-derived map pixels. The retained blank response contains one exact item, no decision, no timestamps, and a false attestation. Approval can close only the owner terrain-result review after exact lock and reconciliation; the other readiness deferrals remain.

## M2 Sentinel-1 orbit amendment and runner validation

The historical orbit review and the current activation controls are reproducible without credential or payload access:

```powershell
python -m unittest tests.test_m2_orbit_amendment -v
python -m unittest tests.test_m2_orbit_activation tests.test_m2_orbit_preflight tests.test_m2_orbit_io -v
python C:\Users\drewb\.codex\skills\gate-external-sources\scripts\validate_source_gate.py records\source-gates\m2-orbit-source-gate.json
python scripts\render_m2_orbit_amendment_review.py --manifest records\source-gates\m2-orbit-candidate-manifest.json --proposal contracts\milestone-002-orbit-amendment-proposal.json --output <new-exclusive-review-surface>.png
python scripts\check_project.py
```

The historical source-gate validator still reports its immutable pre-decision **blocked** result; activation does not rewrite it. The consumed review-bundle manifest remains immutable at SHA-256 `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1`, but its manifest included then-current mutable project controls that have now advanced through activation. Do not rerun it as though it were a current handoff packet. The project checker verifies that historical manifest without demanding stale current-artifact equality, then separately requires the exact locked approval and reconciliation, the four-file active intake, the active offline-verification boundary, all four current live catalogue identities, both reviewed rights hashes, and zero promoted Sentinel or orbit assets.

Fresh preflight passed at `2026-09-04T02:07:51Z` without authentication or payload transfer. Empty-custody attempt-001 failed after seven directories because the `attempt-events` parent was absent; its failure receipt remains required. Attempt-002 was predeclared against that exact empty partial inventory and created the remaining ten directories. The runner suite has 29 passing tests and pins `blake3==1.0.9` in local and CI environments. It verifies provider MD5 and BLAKE3, local SHA-256, no-replace promotion, XML safety, ordered finite state vectors, exact validity, and scene bindings. The generic intake validator initially failed because the four unknown pre-transfer SHA-256 fields had no `unavailable_reason`; the failure is retained, and adding only that required metadata makes the intake schema-valid. A subsequent consistency audit retained and corrected the stale `candidate_not_active` root label to `active`. The post-correction guard probe still exits 12 with `bound_sentinel_source_not_promoted` before catalogue or token access. No orbit file may be transferred until its bound Sentinel sources are promoted and offline container-verified, and no precise substitution is authorized.

The SAFE materialization control has a separate portable suite:

```powershell
python -m unittest tests.test_m2_materialization -v
python scripts/prepare_m2_materialization.py --created-at-utc 2026-09-03T18:55:04Z --verify-only
```

It checks exact-product derivation, executable bindings, synthetic per-file extraction hashes, cross-platform and Windows path hazards, collision refusal, and the production wrapper's stop before custody access when a product is not promoted. The tests do not establish that any real archive has been extracted or that any raster is readable or usable.

The Sentinel-1 materialized-input gate is validated separately before real SAFE inspection:

```powershell
python -m unittest tests.test_radar_input_readiness -v
python -c "import json,subprocess,sys; d=json.load(open('config/qa/radar-input-readiness-contract.json')); raise SystemExit(subprocess.call([sys.executable,'scripts/prepare_radar_input_readiness_contract.py','--created-at-utc',d['created_at_utc']]))"
```

Fourteen portable tests cover exact source narrowing, member selection, unsafe and duplicate paths, complete-payload DTD/entity refusal, source and acquisition identity, finite ordered orbit vectors that bracket acquisition, U16 TIFF headers, annotation-to-raster dimensions, VV/VH metadata and header consistency, and the partial pre-event decision. The final ArcGIS Pro 3.7.1 synthetic receipt opens six U16 TIFFs and blocks a deliberate VH width mismatch. Earlier prepublication passes and the failed `datetime` collision remain recorded. Control validation reads no real SAFE, and a synthetic pass cannot establish a complete pair, pixels, baseline, or change.

The optical input-readiness gate has portable and ArcGIS-native validation:

```powershell
python -m unittest tests.test_optical_input_readiness -v
python scripts/prepare_optical_input_readiness_contract.py --created-at-utc 2026-09-03T19:37:30Z --verify-only
```

The tracked ArcGIS receipt binds the corrected synthetic adapter run. ArcGIS Pro 3.7.1 opens sixteen JP2 rasters, records each format, CRS, band count, dimension, cell size, pixel type, and extent, and reads the three-band 60 m `MSK_CLASSI_B00.jp2` header from its `Band_1` through `Band_3` child descriptions. It blocks a deliberately shifted after grid with sixteen extent mismatches. The production runner stops before importing ArcPy when either exact materialization receipt is absent. This is header-readiness evidence only and does not establish real pixel access or usability. The earlier published one-band 20 m fixture and the first corrected ArcGIS attempt remain preserved as superseded and failed evidence.

## Source validation

For each external product:

- exact identity and provider are recorded;
- access and rights are reviewed;
- geometry and acquisition timing match the manifest;
- local bytes match the recorded size and checksum;
- expected bands/polarizations are present;
- AOI coverage is inspected at the pixel level;
- accepted, rejected, or deferred status is explicit.

## Spatial validation

- all analytical layers report the intended CRS;
- grid origin, cell size, resampling, and snap raster are documented;
- stable control points or invariant terrain are used to quantify co-registration;
- misregistration tolerance is chosen before change thresholds;
- area and distance measures use projected geometry.

## Optical QA

- cloud, cirrus, shadow, snow/ice, saturation, and nodata masks are inspected;
- each AOI has a valid-pixel fraction;
- spectral deltas are tested on stable reference areas;
- visual interpretations link to source and mask layers.

## Radar QA

- orbit and viewing geometry match within each comparison;
- calibration and terrain-correction settings are recorded;
- layover, shadow, border noise, water variability, and residual speckle are reviewed;
- ascending and descending results are evaluated independently;
- stable reference areas are used to characterize background change.

## Change-feature QA

- every feature has the required evidence attributes;
- confidence criteria are defined before final classification;
- optical/radar agreement and disagreement are represented;
- inconclusive areas remain in the evidence record;
- causal wording requires a separate review decision.

## ArcGIS package QA

The current metadata-only evidence workspace has a separate ArcGIS-native validator:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" scripts\validate_arcgis_evidence_workspace.py
```

It opens the retained File Geodatabase and APRX, checks all declared datasets, fields, domain assignments, row counts, relationship classes, EPSG:32645 feature classes, map and layout identity, required layout elements, and bound APRX/PDF hashes. A clean Git checkout can run the portable checks but cannot repeat this native check without the ignored retained scratch outputs and ArcGIS Pro.

- open and export tests succeed from a clean directory;
- no broken sources or undocumented network paths remain;
- layer scales, metadata, credits, and limitations are visible;
- packaged and source manifests reconcile;
- large or licensed artifacts are stored on an approved release surface, not Git.

## Public release QA

Verify repository state, GitHub release assets, public map files, rights notices, scientific wording, and downloadable package independently. A local export or green script alone is not proof of public release.
