# Nepal 2026 Before/After Map

An evidence-first geospatial project to produce a reproducible, ArcGIS-ready before-and-after map of the 26 August 2026 debris avalanche and flash flood in Nepal's Langtang–Bhote Koshi–Trishuli corridor.

## Active long-term goal

Build and maintain a defensible geospatial evidence package that shows where the event altered the landscape, distinguishes direct satellite observations from interpretation, and can be opened, reviewed, updated, and exported in ArcGIS Pro without relying on undocumented analyst state.

The project should ultimately deliver:

- a projected ArcGIS Pro project in **WGS 1984 UTM Zone 45N (EPSG:32645)**;
- registered before/after optical and radar imagery with source manifests and checksums;
- mapped change features with confidence, method, date, and source attributes;
- overview, source-area, and corridor map layouts;
- portable ArcGIS layer and project packages plus GeoTIFF, GeoPackage/File Geodatabase, PDF, and PNG exports;
- a public, reproducible method record that preserves limitations and failed or inconclusive analytical routes.

This goal is **active as of 1 September 2026**. M1 is complete: the search and review AOIs are owner-approved, projected to EPSG:32645, and validated through ArcGIS Pro, and the exact source manifest is approved with eight sources accepted for controlled acquisition and two preserved as deferred context. M2 was activated by an exact owner decision on 3 September 2026. Its live source and custody preflight passed, and the approved empty external custody structure was initialized. No product bytes have been downloaded, no authentication occurred, and no usable pixels or scientific change have been established.

## Why this is useful

Emergency maps often mix source discovery, visual interpretation, and final cartography in ways that are hard to audit later. This project separates those stages. A reviewer should be able to trace a mapped change back to an exact satellite product, processing step, observation date, and confidence statement.

## Initial study design

| Component | Initial choice |
|---|---|
| Event | 26 August 2026 Nepal debris avalanche and flash flood |
| Study corridor | Langtang source area through the Bhote Koshi–Trishuli corridor |
| Master CRS | EPSG:32645, WGS 1984 UTM Zone 45N |
| Core optical | Sentinel-2 Level-2A, 12 Aug and 27 Aug 2026 |
| Core radar | Sentinel-1 GRD, ascending and descending before/after pairs |
| GIS target | ArcGIS Pro 3.7+ |
| Public core | Copernicus products and reproducible metadata |
| Optional high resolution | Separate, license-gated, noncommercial path only |

The product identifiers currently under consideration are recorded in [docs/DATA_AND_METHODS_PLAN.md](docs/DATA_AND_METHODS_PLAN.md). They are candidates until coverage, rights, pixels, masks, and event relevance are verified.

## Repository boundaries

This public repository stores project controls, methods, small scripts, source manifests, and lightweight review evidence. It does **not** store raw satellite archives, extracted SAFE products, large rasters, geodatabases, ArcGIS project packages, credentials, access tokens, or licensed imagery. Those belong in controlled local or external data custody.

Public visibility does not grant reuse rights to third-party data. No repository license has been selected yet.

## Current checkpoint

Milestones 0 and 1 are complete, and the exact M2 activation decision is locked and reconciled. The active M2 contract covers only the eight reviewed Sentinel products. At `2026-09-03T17:31:17Z`, the live preflight revalidated the official access and rights pages, confirmed that all eight product identities, catalog sizes, checksums, and online states were unchanged, found 514.942 GiB free, and verified an absent collision-free external root outside Git. The empty root, custody directory, and staging directory were then created with matching append-only receipts.

The current checkpoint is `M2-AUTHENTICATION-REFERENCE`. Preflight found no credential reference in the process environment, so no login or transfer was attempted. Continuation requires a secret-safe reference to an existing owner-controlled CDSE access token or authenticated session. Tokens, passwords, cookies, and authorization headers must not be placed in Git, chat, filenames, receipts, or captured command output.

The active intake contract fixes sibling staging and custody paths, fail-on-collision and atomic no-replace promotion rules, secret references, and attempt retention. The reviewed proposal, acquisition plan, review bundle, and public blank response remain unchanged historical evidence.

A one-product transfer runner is prepared but has not contacted the authenticated service. Eleven local fixture tests cover the missing-reference stop, exclusive staging, streamed SHA-256 and provider-MD5 checks, size/checksum failure retention, redirect refusal, path containment, receipt no-replacement, and Windows-tested atomic hard-link promotion. A real run must revalidate all four official pages and the exact catalog record before writing its started-attempt event.

The offline verification contract is also active for the exact eight products. Its per-product wrapper requires a promoted intake record and matching successful-transfer receipt, reads the archive without extraction, and checks catalog size, local SHA-256, provider MD5, ZIP safety and CRC, exact SAFE root, and the required radar or optical members. Five active-wrapper tests pass; no real archive has been read.

A deterministic offline verification packet now defines exact archive, checksum, ZIP-safety, SAFE-structure, band, polarization, and post-container pixel-readiness checks for the same eight products. Its independent dataset-readiness result is **DEFER** because no product bytes, access-time rights evidence, AOI pixel coverage, masks, or registration results exist. The packet made no external-custody access or network request.

A metadata-only ArcGIS evidence workspace has also been built and validated in ArcGIS Pro 3.7.1 Advanced. Its EPSG:32645 File Geodatabase contains nine datasets, fourteen coded-value domains, eight relationship classes, three approved AOIs, and ten source-product metadata rows. The observation, interpretation, attribution, exclusion, stable-control, and QA structures are empty by design. The retained APRX, geodatabase, and PDF remain outside Git; the repository contains the schema, builder, validator, receipt, and a reviewed PNG preview.

Pixel-readiness thresholds are now fixed before product access in `config/qa/pixel-readiness-contract.json`. A dependency-free decision core and ArcGIS Pro 3.7.1 Spatial Analyst adapter have passed synthetic validation for all three approved AOIs, including an expected block for a 0.6-pixel grid shift and a required defer for unmeasured registration. These are control and runtime tests only; no real satellite pixels or scientific observations were admitted.

ArcGIS Pro's installed Sentinel-1 terrain-correction tools also expose a required DEM input. The active M2 approval contains no elevation source, so a separate non-authorizing amendment review now binds four exact public Copernicus DEM GLO-30 COG tiles, their live metadata, the anonymous access route, and the exact license document. No DEM payload was requested and the license has not been accepted. The original eight-product acquisition remains independently paused at the secure authentication handoff.

The four-tile intake and ArcGIS GeoTIFF verification controls are now predeclared without activation. The Sentinel-1 baseline contract also fixes independent ascending and descending processing routes, beta-nought calibration, gamma-nought terrain flattening, retained terrain-distortion masks, linear quantitative outputs, and EPSG:32645 delivery. It deliberately defers production processing because the Copernicus DEM uses EGM2008 orthometric heights while ArcGIS's built-in geoid correction is documented as EGM96, and because updated Sentinel orbit files would be additional products outside the active acquisition boundary.

See:

- [Project charter](docs/PROJECT_CHARTER.md)
- [Roadmap](docs/ROADMAP.md)
- [Data and methods plan](docs/DATA_AND_METHODS_PLAN.md)
- [Source register](docs/SOURCES.md)
- [M1 AOI review bundle](docs/M1_AOI_REVIEW.md)
- [M1 source-manifest review](docs/M1_SOURCE_MANIFEST_REVIEW.md)
- [M2 controlled-acquisition review](docs/M2_CONTROLLED_ACQUISITION_REVIEW.md)
- [M2 controlled-intake execution runbook](docs/M2_EXECUTION_RUNBOOK.md)
- [M2 offline product verification](docs/M2_OFFLINE_VERIFICATION.md)
- [M2 DEM dependency amendment review](docs/M2_DEM_AMENDMENT_REVIEW.md)
- [M2 DEM intake and offline verification](docs/M2_DEM_OFFLINE_VERIFICATION.md)
- [ArcGIS Sentinel-1 baseline processing protocol](docs/RADAR_BASELINE_PROCESSING_PROTOCOL.md)
- [ArcGIS delivery plan](docs/ARCGIS_DELIVERY_PLAN.md)
- [ArcGIS evidence model](docs/ARCGIS_EVIDENCE_MODEL.md)
- [Validation plan](docs/VALIDATION.md)
- [Current status](docs/STATUS.md)
- [Decision log](docs/DECISIONS.md)

## Validate the repository

From the repository root:

```powershell
python scripts/check_project.py
```

The check verifies required control files, parses the JSON records, validates the portable ArcGIS schema and receipt bindings, and rejects tracked secrets and large geospatial artifacts.
