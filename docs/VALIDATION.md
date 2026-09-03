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
python C:\Users\drewb\.codex\skills\gate-external-sources\scripts\validate_source_gate.py records/source-gates/m2-live-source-gate.json --as-of 2026-09-03T17:31:17Z
python C:\Users\drewb\.codex\skills\intake-controlled-data\scripts\validate_intake_contract.py contracts/m2-intake.json --project-root C:\Projects\Active --json
python C:\Users\drewb\.codex\skills\run-controlled-milestone\scripts\validate_milestone.py contracts/milestone-002.json --project-profile records/project-control-profile.json --as-of 2026-09-03T17:35:43Z
```

The live record proves only the source and custody preflight at its stated timestamp. It does not prove an authenticated transfer, current future availability, local bytes, valid product containers, usable pixels, or scientific fitness.

The transfer state machine has a separate network-free suite:

```powershell
python -m unittest tests.test_m2_transfer_core -v
```

The suite verifies missing-reference refusal without intake mutation, exclusive staging, streamed hashes, mismatch retention, redirect refusal, path containment, receipt no-replacement, failed-attempt history, destination collision preservation, and atomic no-replace promotion. The passing readiness receipt is synthetic/local evidence only and does not establish real CDSE behavior or product integrity.

The active offline-verification binding and wrapper stop are tested separately:

```powershell
python -m unittest tests.test_m2_active_verification -v
```

These tests verify exact inheritance from the M2 approval, preservation of all eight candidate container profiles, offline/read-only behavior, and refusal before custody access when an asset has not been promoted.

## M2 DEM amendment preparation validation

The DEM amendment remains non-authorizing and can be validated without requesting a DEM payload:

```powershell
python C:\Users\drewb\.codex\skills\gate-external-sources\scripts\validate_source_gate.py records/source-gates/m2-dem-source-gate.json --validate-only
python C:\Users\drewb\.codex\skills\conduct-human-review\scripts\prepare_review_bundle.py reviews/m2-dem-amendment/review-bundle.json --project-root .
python -m unittest tests.test_m2_dem_amendment -v
```

The source-gate validator must report a structurally valid **blocked** result with exact license acceptance and scope authority still unresolved for all four tiles. The tests require the exact four-item set, the 170,302,058-byte remote total, live metadata-only claim boundary, immutable proposal bindings, blank human response, and exact review-bundle hashes. ArcGIS tool presence proves only local capability; no DEM or Sentinel processing has run.

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

The SAFE materialization control has a separate portable suite:

```powershell
python -m unittest tests.test_m2_materialization -v
python scripts/prepare_m2_materialization.py --created-at-utc 2026-09-03T18:55:04Z --verify-only
```

It checks exact-product derivation, executable bindings, synthetic per-file extraction hashes, cross-platform and Windows path hazards, collision refusal, and the production wrapper's stop before custody access when a product is not promoted. The tests do not establish that any real archive has been extracted or that any raster is readable or usable.

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
