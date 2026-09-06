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

## Recovery-002 outcome and continuation review validation — 2026-09-05

The single approved recovery-002 archive passed exact transfer and container checks, while the supervisor's later pre-attempt continuation failure remains separately retained. The active-intake validator now recognizes the versioned recovery receipt root, two-attempt append-only history, in-memory credential reference, and preserved original partial without weakening the original route. The checkpoint derivation also recognizes the exact blank continuation review instead of treating four promoted and four authorized assets as an unattended transfer state.

- `python -m unittest discover -s tests -v`: 294 tests pass.
- `python scripts/check_project.py`: 416 required files, JSON controls, and Git artifact boundaries pass.
- `validate_project_control.py`: valid with active inherited authority.
- `validate_milestone.py`: valid; `M2-SENTINEL-CONTINUATION-001-REVIEW` is the sole ready human gate.
- `review_response.py self-test`: pass.
- `prepare_review_bundle.py`: bundle `382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b` is valid and ready for handoff with zero decisions.

Public workflow run `33935109759` for commit `46aafc5249f7199308b46cb1d4c8375beecd84b5` failed before tests because the first unapproved review packet hashed CRLF workspace bytes while Git published LF bytes. The failed run and original commit remain preserved. The active blank packet is rebound to canonical LF identities; this correction changes no proposal scope, decision state, acquisition state, or scientific claim.

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

After commit `87aa2610f1a89fe2d612f9cdd6cb88e63e833c8d` passed public CI run `33905019294`, the production runner was invoked once. Exact member identity, six annotation parses, embedded vectors, and six TIFF headers passed, but the frozen contract blocked all sources because the observed `pixelValue` was `Detected`, not `AMPLITUDE`. Independent post-run verification rehashed all 78 SAFE files totaling 5,183,550,209 bytes and found exact 29-file attempt inventories with no added sidecars. Preserve `records/readiness/radar-input/m2-s1-input-readiness-real-001.json`; do not rerun it under the current contract.

The review-only label amendment uses the general source-gate validator and the human-review bundle utilities:

```powershell
python C:\Users\drewb\.codex\skills\gate-external-sources\scripts\validate_source_gate.py records/source-gates/m2-radar-input-label-specification-source-gate.json
python C:\Users\drewb\.codex\skills\conduct-human-review\scripts\prepare_review_bundle.py reviews/m2-radar-input-readiness-amendment/review-bundle.json --project-root .
python C:\Users\drewb\.codex\skills\conduct-human-review\scripts\review_response.py self-test
```

The source gate is structurally ready for metadata capture and review preparation only. The bundle binds seven exact artifacts and the review utility verifies an unattested blank response with one item and zero human decisions. These checks create no amendment or rerun authority.

The optical input-readiness gate has portable and ArcGIS-native validation:

```powershell
python -m unittest tests.test_optical_input_readiness -v
python scripts/prepare_optical_input_readiness_contract.py --created-at-utc 2026-09-03T19:37:30Z --verify-only
```

The tracked ArcGIS receipt binds the corrected synthetic adapter run. ArcGIS Pro 3.7.1 opens sixteen JP2 rasters, records each format, CRS, band count, dimension, cell size, pixel type, and extent, and reads the three-band 60 m `MSK_CLASSI_B00.jp2` header from its `Band_1` through `Band_3` child descriptions. It blocks a deliberately shifted after grid with sixteen extent mismatches. The production runner stops before importing ArcPy when either exact materialization receipt is absent. This is header-readiness evidence only and does not establish real pixel access or usability. The earlier published one-band 20 m fixture and the first corrected ArcGIS attempt remain preserved as superseded and failed evidence.

## Candidate change-evidence control validation

The future M4 route logic is portable and predeclared:

```powershell
python -m unittest tests.test_change_evidence_core -v
python scripts/check_project.py
```

Twelve focused tests cover separate optical index observations, two-sided VV/VH radar changes, zero-MAD defer behavior, exact input-QA and stable-reference requirements, minimum mapping area, candidate-area consistency, failure-history retention, zero-candidate nonfailure, all-route accounting, multisensor spatial coincidence without attribution, disagreement, and untestable-route inconclusiveness. These tests use synthetic scalar signals and route summaries. They read no satellite pixel and create no candidate feature, interpretation, attribution, or processing authority.

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

## Continuation-001 approval and local implementation validation — 2026-09-05

The completed exact owner response was written to private custody, locked before reveal, and reconciled without ambiguity. Response SHA-256 `add004d26f7a35ed1b657089dae1c1f68f01eba495c0c4edb35cee943a13cb39`, approval SHA-256 `93f451f458c5b4984f980049f5adadf73e52663c8a71ee9699939b7f85e727a1`, and reconciliation SHA-256 `420f525d160a1b95f6784da06a0ca95ddf8e6e8e37d7947925f6c865157d28a6` bind one approval, zero revise/defer decisions, and the exact reviewed source order.

- `python -m unittest tests.test_m2_sentinel_continuation_001 -v`: 23 tests pass.
- `python -m unittest discover -s tests`: 317 tests pass after the final project-record reconciliation.
- Readiness SHA-256 `f52d989352541a1fb28dacf858fd14408de28bde84fcb9355154ea623df48fad` binds the exact continuation implementation and retains superseded readiness SHA-256 `86af300807b6db28e97deb6b8188d609f02bf0bed3044741e1eb124eddc28c48`.

The tests cover Windows broker interruption, anonymous single-use pipe custody, environment scrubbing, safe known and unknown failure codes without exception text, fixed order, one attempt per source, stop on first transfer or container failure, redirect and Range refusal, exclusive staging, atomic no-replace promotion, explicit `M1-SRC-004` refusal, and a failed exact live pre-attempt check with no intake or path mutation. No network request, authentication, token value, external product mutation, payload request, real continuation attempt, pixel processing, or scientific result occurred. Successful public CI, activation, and the final no-payload preflight remain required.

## Continuation-001 implementation publication failure and correction — 2026-09-05

Commit `114cb663dbaf13bd286d26f92167ea4a9b7ec420` matched `origin/main` and passed `scripts/check_project.py` in GitHub Actions, but run `33942595168` failed in `test_live_preflight_control_failure_is_exact_and_pre_attempt`. On Linux, the production runner tried to resolve the absent external custody root before the test reached its mocked legal-page failure. Failure record SHA-256 `17035284194fad3645f95d2162a6ff639f6743e2d849c67fce4e3505340cc2f0` preserves the terminal result. Activation, credential access, and payload access did not occur.

The corrected test creates isolated temporary custody and staging roots and mocks free-space availability before invoking the exact production runner. It still requires the same legal-page failure code and proves no active-intake, destination, staging, or event-path mutation.

- `python -m unittest tests.test_m2_sentinel_continuation_001 -v`: 23 tests pass.
- `python -m unittest discover -s tests`: 317 tests pass.
- Corrected readiness SHA-256: `35bb375543dc2add5e66e80019ee7bc4eb70cee2f2cc3a4c8cf542c97369919a`.
- Superseded published readiness SHA-256: `f52d989352541a1fb28dacf858fd14408de28bde84fcb9355154ea623df48fad`.

A new exact public CI pass remains required before activation, final no-payload preflight, token entry, or acquisition.

## Radar-first path activation and orbit recovery-002 review preparation — 2026-09-05

The exact owner response to radar-first path bundle SHA-256 `5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad` and proposal SHA-256 `ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77` was locked in private non-Git custody before reconciliation. Response SHA-256 `6f571127b6c736aba227e699569f88fe7fc37401605d75222df1e956e3f44b55` reconciles to one approval and zero revise/defer decisions. Approval SHA-256 `e017099532a681f6c7d39afa8b7ab94c25e3c51495381363eaefd67a4533bdb9` activates only the route-specific control correction.

- `python scripts/check_project.py`: 600 required files, JSON controls, and Git artifact boundaries pass.
- `python -m unittest discover -s tests`: 383 tests pass; 2 tests are intentionally skipped after adding the publication-gate assertion.
- `git diff --check`: passes, with only Git line-ending notices on two existing Markdown working-copy formats.

The activated controls preserve optical real-001 as terminal `INVALID`, recovery-001 as terminal `BLOCK`, and aggregate `M2-VERIFY` as deferred. Six exact Sentinel-1 sources pass custody, materialization-identity, and header-readiness controls only; no measurement pixels were decoded. The prior orbit-recovery proposal and bundle remain immutable stale evidence. Corrected orbit recovery-002 bundle SHA-256 `6d43342b6bda2740667fa6e924a52f15313d8827cfb62563ea107bc483e87fa5` binds proposal SHA-256 `d30208c07deb66ef2c7487f8c901abd4fb5ff04aa56766bca8066d4c8d4f0db8` with zero human decisions. Exact commit `45c914695ea3e3b16e309eb0cd1aa13227624599` passed public CI run `33995547794`; publication-gate evidence records that no authority was created. The ordinary orbit runner stops at `orbit_recovery_002_unit_not_complete` before catalogue access, token lookup, event creation, or payload request. No orbit, credential, DEM, radar-pixel, baseline, change-analysis, attribution, or scientific-publication action occurred.

## Orbit recovery-002 approval and local implementation validation — 2026-09-05

The exact completed owner response was locked in private non-Git review custody before reconciliation. Approval SHA-256 `ee5922426882b5620f2e90e6703d0eb7d5f5ab77ede3ed61acfb8616b2c22d07` and reconciliation SHA-256 `b289cd6486ea819c22823fba986702c6e3b353171bff87bc437a67c6bfa0e3ab` bind one approval, zero revise/defer decisions, exact `M2-ORB-001`, and at most one future attempt.

- `python -m unittest tests.test_m2_orbit_recovery_002 -v`: 12 tests pass.
- `python -m unittest tests.test_m2_orbit_io -v`: 9 tests pass.
- `python -m unittest discover -s tests`: 395 tests pass; 2 historical production-state probes are intentionally skipped.
- `python scripts/check_project.py`: 618 required files, JSON controls, and Git artifact boundaries pass.
- `git diff --check`: passes.

The focused controls cover anonymous pipe custody, environment scrubbing, detached worker survival after broker termination on Windows, generic nonsecret failures, PowerShell parser safety, byte-zero headers without Range, distinct exclusive staging, exact source scope, retained failure history, and exactly one later successful verifier binding. No credential was read, no CDSE or orbit endpoint was contacted, no orbit payload was requested, and no external data was mutated. Successful public CI remains required before activation or the final no-payload preflight.

Implementation commit `b61673c26d1a96f5fd01c5adde0e050be374d8ba` passed repository validation in GitHub Actions run `33996953195` but failed the test step because the Linux runner has no `powershell` executable. The failed run, original readiness bytes, and exact cause are retained. The correction applies the existing deployment-platform guard to that parser test; portable static token-custody checks still run on every platform. Local Windows results remain 12 focused and 395 total tests passing. No publication gate, activation, credential access, orbit request, or external mutation occurred after the failure.

## Orbit recovery-002 Windows handoff correction — 2026-09-06

The first owner-side handoff after the corrected implementation passed public CI returned the generic `orbit_recovery_broker_failed` status. Read-only diagnosis reproduced the exact local failure: an LF-framed fixture passed, while the same synthetic nonsecret value framed with PowerShell's CRLF retained `\r` and failed `secret_contains_whitespace`. No detached supervisor, recovery staging root, new attempt ID, catalog request, destination, or payload byte existed. The active intake still contained only the retained original failed attempt. Failure receipt SHA-256 `c8ebff040e6f7f9b03091342c73d5ce09691e03d614134d4788fd872b32c055e` preserves that pre-attempt state without a credential value.

The corrected reader removes exactly one terminal LF or one terminal CRLF sequence, then applies the unchanged UTF-8, size, nonempty, and internal-whitespace validation. Earlier publication, contract, activation, preflight, and control-reconciliation artifacts are retained under superseded names rather than overwritten.

- `python -m unittest tests.test_m2_orbit_recovery_002 -v`: 12 tests pass on Windows, including LF and CRLF single-use pipe fixtures and detached-worker survival.
- `python -m unittest tests.test_m2_orbit_io -v`: 9 tests pass.
- `python -m unittest discover -s tests`: 395 tests pass; 2 historical platform or production-state probes are intentionally skipped.
- Corrected readiness SHA-256: `e640087a49a53d6c11edcc56ac7d0e4d2c842a1453b76b247e7dd53f3525f8d1`.

Public CI is pending. No automatic rerun is permitted. After CI passes, the project must recreate the exact publication gate, control reconciliation, activation, and final no-payload preflight; the owner must then deliberately run a fresh secret-safe handoff.

## Orbit recovery-002 terminal reconciliation and recovery-003 review — 2026-09-06

Corrected recovery-002 commit `67ce761003c5c841a068ed688709b348cd423ce3` passed public CI run `34048602657`. Publication gate SHA-256 `a94cf2a5c8fafdcafdfc5a4234cb05386129ca3f8579ab7a99450efbf712049a`, active contract SHA-256 `dda7741a180f2c5eabb98d4bbe936ebc6e15fb9809513bfb448ed15bf53e6247`, activation SHA-256 `a899962952251aafc670c641b6557ae37c220384ff7dbf59fcd2657c0ffbc9d1`, and final preflight SHA-256 `5458c9ce211ca85627d0420a9f3592623be126923a2d916c95c625ff2a05933f` passed before one owner handoff.

Supervisor `m2-orbit-recovery-002-20260906t172858z-42bace7e` recorded start and heartbeat evidence, then a terminal `orbit_recovery_002_supervisor_unexpected_failure` during `public_catalog_revalidation`. Read-only reconciliation found one empty exclusive payload-parent directory, no attempt event root, no attempt ID, unchanged active intake, no destination, and zero payload bytes. Code-order evidence bounds the failure after exact public catalogue revalidation returned and after the payload parent was created, but before authenticated download. The generic journal intentionally omits exception text, so the exact exception category and catalogue-response hash remain unknown. Outcome SHA-256 `3d0b6be8e09e0d9049c32c65461e321b2fdbd5db398dd9a6d1b08b62c6c51380` records these distinctions. Recovery-002 is consumed and cannot retry.

The new recovery-003 packet uses proposal SHA-256 `5aa4a0042024634a7ade191e0c5f36614216d8581a9c0535c0042be20583bfa3`, bundle SHA-256 `bc3cdc22d16251c77b26d9903036b4317221e2b01207aa9db26436bfd091fe9d`, contract SHA-256 `a122def1ac97e3ff5451d807c2a98e7713d7c46d834103d70d7807e67e694cf0`, and blank-response SHA-256 `63f8972c8d03ba66d2b9d2b850fea72e7e388e2a5b5b538c2f2fc076cd1f4f82`. The rendered surface was visually inspected; the review validator, blank-response preparation comparison, and response self-test pass. Eighteen focused recovery-003 and checkpoint tests pass, and the full suite passes 400 tests with 3 intentional skips. Exact packet commit `70226497f72c8cbbc576608b8fc7f4cbcae18cc6` passed public CI run `34050115168`; publication-gate SHA-256 `39129d10ef4468ed0fc02480dede02bd0efa8c9a4f82d502694e1726e8186fee` binds that result. The packet has zero decisions and creates no recovery, credential, catalogue, payload, DEM, radar-pixel, baseline, change, attribution, or scientific-publication authority. The exact owner decision is now pending.

## Orbit recovery-003 terminal result and OSV precision review — 2026-09-06

Recovery-003 implementation commit `d56f83714d2c8774d23ad364f8b760f06272bf7c` passed GitHub Actions run `34051909920` before activation, final no-payload preflight, and the one owner handoff. Supervisor `m2-orbit-recovery-003-20260906t183804z-e5883324` created exact attempt `m2-orb-001-recovery-002-20260906t183804z-e5883324`, wrote event-scoped start and catalogue evidence, and made one byte-zero request. The resulting staged EOF is 639,533 bytes, has SHA-256 `a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4`, and matches provider MD5 `ca7f36b1892073c883c4cff5c0517b9c` and BLAKE3 `ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b`.

The frozen verifier stopped before promotion with `osv_times_do_not_span_validity`. The header stop is `UTC=2026-08-16T14:09:56`; the final of 1,288 ordered OSVs is `UTC=2026-08-16T14:09:55.968171`, a 0.031829-second shortfall. The file remains append-only staging evidence and no orbit destination exists. The first outcome reconciliation returned `failed supervisor differs from active intake attempt` because the worker's best-effort failure finalizer had left the active intake at `staging` and `started`. That refusal is preserved at SHA-256 `0f99de4d1bd7edf0a70487b36826879a857067a80a54573a4d50a2845ff1af93`. Eighteen focused recovery tests passed before a bounded control-only finalizer changed the exact matching attempt to `failed`; the existing outcome reconciler then passed. Outcome SHA-256 is `f67b7307dfe82cb6f02a13003389f482c7c2a96342fab138f737a31c2ec2d503`.

The Copernicus POD Service File Format Specification records whole-second validity headers and microsecond OSV timestamps but does not explicitly define rounding or a numerical tolerance. Source record `records/source-gates/m2-orbit-osv-time-format-evidence.json` labels the proposed one-second endpoint rule as an inference, not a provider mandate. The zero-decision packet has proposal SHA-256 `0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4`, bundle SHA-256 `71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7`, contract SHA-256 `aeda5b43507f295fbc471e07c612555ebfc93a491e2ccd5b33a6c84a3d735ec0`, and blank-response SHA-256 `a644aa0572def81d36fc2c1e94ca3d9937bb9ea2fd9ab3758d096ea097b27a15`. The bundle validator passed all fourteen artifacts with no warnings, the generated blank response matched byte-for-byte, and the 1800-by-1620 PNG was visually inspected. Public CI remains required before owner review. No token, network request, retry, promotion, other orbit request, processing, or scientific result is authorized.

Local publication readiness then passed five focused terminal-reconciliation and blank-review tests, all 421 portable repository tests with three intentional skips, the 698-file project checker, read-only checkpoint derivation, `git diff --check`, and a JWT/bearer-pattern scan. Readiness SHA-256 `1f25703bde0c3f17ea438b6af2a095c228d5e56c6ecd0eb34eb0a58471eeac87` preserves that pre-publication result. It creates no amendment authority; public default-branch CI is still mandatory before the packet can be handed to the owner for a decision.

Publication attempt commit `fcafa846cd555a7fdbe9af5d4463be438fc4e798` passed the repository-validation step and failed GitHub Actions run `34054152812` because the portable review test imported the local rendering script, which imports optional Pillow unavailable in the deliberately minimal CI environment. The failure is preserved at SHA-256 `21b7c81688ba230e2191977e3f5fd99b9ea0f001da0d907f6511e994a83a633f`. Portability correction SHA-256 `dd7f82126c076568dafbd282457c2e2ae24c0838efd39c0dc1dff9e4146edbd0` changes only the test import boundary: immutable paths and a local SHA-256 helper replace the optional renderer import. The proposal, bundle, rendering script, staged bytes, and authority state are unchanged. Five focused and 421 full-suite tests pass locally; a fresh public CI run remains required.

Corrected commit `39a1807f77ed6463f4100b753aa85a3e299220d5` passed GitHub Actions run `34054314929`. Publication-gate SHA-256 `7f8073ad27f88dfae55df7d6c508af76dd4ca86a2eea2066b4c1f333670cff09` binds the unchanged proposal, bundle, blank response, failed run, and portability correction. Reconciliation SHA-256 `9ff9355546a761533568b90f77174d0096202380512a79abb5f2fe9dfe8fcead` moves only the project checkpoint to blank owner review. It records zero human decisions, no attestation, no amendment authority, no credential or network access, no staged-byte promotion, and no scientific result.

## OSV precision amendment-001 approval and local implementation — 2026-09-06

The completed owner response was locked outside Git and reconciled as one exact approval. Review reconciliation SHA-256 `1bdbf7a56533b67d9228f1c3545fcd5a65643eacce584a5796e7d80b8d0d1c3c` records one approve, zero revise, zero defer, a true attestation, and no fabricated decision. Approval SHA-256 `4a77a044475b6c940a4b58d4c4dbcf76730c06e63d18927eb717312a97667cf4` binds proposal SHA-256 `0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4` and review bundle SHA-256 `71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7`. The first lock invocation used an invalid generic candidate filename and performed no lock; failure SHA-256 `080c070f16eebbe576ad17581990cbc8b6cbfe2eae1c0dae74825f3ff0990495` preserves that event. The unchanged completed response was then locked under its contract-compliant identity.

Versioned contract SHA-256 `ee578c8cc7c4e27c28f6e8ea4d65b664ce1a22a33db57e06c10c9cccafbb928e` freezes a maximum one-second endpoint tolerance, zero network requests, one local validation, and conditional no-replace promotion of only exact `M2-ORB-001`. The implementation keeps a strict zero-second default for unamended contracts and rejects negative, nonfinite, or greater-than-one-second tolerances. Nine focused tests cover exact, subsecond, one-second, excessive-tolerance, strict-default, XML inspection, atomic promotion, staging preservation, and existing-destination refusal. The full portable suite passes 433 tests with 3 intentional skips. Implementation readiness SHA-256 `c8e01e91cfb30485308e68f00d8eab53de0ca17de95d37002afbafe6591b324d` records that no real staged bytes were read, no network action occurred, and no validation or promotion began.

The project checker passes 725 required files and current control bindings. An additional bounded projection check found that `M2-ORBIT-ACQUIRE.gates.osv_precision_amendment_status` still carried its pre-approval label even though the adjacent retained-failure field and authority surfaces were current. Correction SHA-256 `dfa2cda515a12701c6a3b6678685681cb8935561db02d98cb79cf95970ca7cac` changes only that status label and records no staged-byte read, network request, external mutation, or authority change. The checkpoint is `M2-ORBIT-OSV-PRECISION-AMENDMENT-001-IMPLEMENTATION-PUBLICATION`. The implementation must be committed, pushed, and pass public default-branch CI before the final preflight may inspect the preserved bytes. No token, download, recovery-003 retry, request for `M2-ORB-002` through `004`, tolerance above one second, orbit application, DEM action, radar-pixel access, baseline, change analysis, attribution, or scientific publication is released.

Exact implementation commit `55397416ac902fac7ec46382cdc3904b53566478` passed GitHub Actions run `34056822125`. Publication-gate SHA-256 `c5b8bedd2f656acc8f464a880fae11dd0d936bf2c12ac3891275bb27c36ba3ea` records that success before any real staged-byte read. Final no-network preflight SHA-256 `6060a52bc293ce4005bf0bc1a73df806a77fd51338784eb4e66b3b5151a9abbc` then re-hashed the exact preserved staging file, confirmed the destination and attempt outputs were absent, and released only the single local action.

Local result SHA-256 `9b3e45fe1d8fe0c9c6668287d7bfc2ec0f8e238d6e0730f04a8d99583eef9898` records one validation attempt, zero network requests, the approved one-second tolerance, a measured 0.031829-second final-OSV shortfall, and `pass_orbit_input_only`. The exact 639,533-byte file has SHA-256 `a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4`, provider MD5 `ca7f36b1892073c883c4cff5c0517b9c`, and provider BLAKE3 `ce824099fa812d6c229bd5bef2d4a70d7185d248f91ec3111ce557868ab1269b`. It was promoted by no-replace link semantics and the source staging file was re-read unchanged afterward. External receipt SHA-256 is `2cb5ce849565cffdf14ea211071f347a3c17f431a9f341bd09938f1d6c9df934`.

Terminal reconciliation SHA-256 `6309ee02114a8a59d5c3b46ed29b4f5901dfdb009d47dccb314561664a6254dd` preserves both prior failed attempts, records active orbit counts of one promoted and three authorized, and stops before any other request or processing. Four new outcome tests and the full 437-test suite pass with 3 intentional skips; `scripts/check_project.py` validates 731 required files, and checkpoint derivation matches `M2-ORBIT-REMAINING-SOURCES-REVIEW-PREPARATION`. No orbit application, DEM or radar-pixel processing, baseline, change result, attribution, or scientific result is established.
