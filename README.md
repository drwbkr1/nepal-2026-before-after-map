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

This goal is **active as of 3 September 2026**. M1 is complete: the search and review AOIs are owner-approved, projected to EPSG:32645, and validated through ArcGIS Pro, and the exact source manifest is approved with eight sources accepted for controlled acquisition and two preserved as deferred context. M2 was activated by an exact owner decision on 3 September 2026. Three exact before-event Sentinel-1 products are now promoted in controlled non-Git custody and have passed offline ZIP/SAFE container verification. The first after-event transfer, `M1-SRC-004`, stopped on an exact-length mismatch after 561,593,598 of 1,732,332,897 bytes; its partial and terminal attempt evidence are retained, and four products remain unattempted. The current checkpoint is `M2-ACQUISITION-REVIEW`, with no automatic retry or further Sentinel transfer permitted before review. Separately, four approved Copernicus DEM tiles totaling 170,302,058 bytes were anonymously acquired outside Git and passed exact-byte, ArcGIS structural, and AOI finite-coverage checks. The owner has also approved four exact S1D restituted orbit files for the six radar scenes, but orbit transfer remains blocked until its bound Sentinel scenes are promoted and offline-verified. No Sentinel pixel usability, orbit payload, vertical-datum conversion, orbit correction, radar result, or scientific change has been established.

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

Milestones 0 and 1 are complete, and the exact M2 activation decision is locked and reconciled. The active Sentinel route covers only the eight reviewed products. At `2026-09-03T17:31:17Z`, the live preflight revalidated the official access and rights pages, confirmed that all eight product identities, catalog sizes, checksums, and online states were unchanged, found 514.942 GiB free, and verified an absent collision-free external root outside Git. The empty root, custody directory, and staging directory were then created with matching append-only receipts. A protected existing owner credential reference was later confirmed and used without recording its value.

At `2026-09-04T03:41:36Z`, a refreshed gate reconciled a rendered CDSE terms-page hash change without accepting terms or touching a credential. The official terms document's structured modification date and six scope-relevant clauses remained current, the linked Sentinel Legal Notice was byte-identical, and all eight exact product identities remained online and unchanged. The transfer runner now distinguishes the normalized legal section from changing page-shell content and still stops before mutation on any legal, account, terms-acceptance, product, path, or storage drift.

The separately approved DEM amendment covered four exact Copernicus GLO-30 tiles. All four were acquired anonymously through exclusive staging and no-replace promotion, then verified in ArcGIS Pro 3.7.1 as 3600-by-3600, single-band F32 EPSG:4326 rasters. A full scan found 51,840,000 finite non-NoData cells, and the continuous four-tile footprint covers all approved AOI bounds. A later fixed terrain screen passed all four tile checks, four seam checks, AOI slope, EPSG:32645 projection, 189-file stable-manifest reconciliation, and PNG/PDF visual criteria. The result establishes gross-artifact and map-surface fitness only. A separate terrain-result review bundle is ready with zero human decisions and can close only its owner-review gate. The EGM2008 one-minute preconversion review remains independently pending; the required optional ArcGIS coordinate-system component is not installed, and independent elevation accuracy, radar processing, and scientific fitness remain unresolved.

The current checkpoint is `M2-ACQUISITION-REVIEW`. A protected owner-controlled credential reference generated fresh process-local CDSE access tokens without recording secret values. `M1-SRC-001`, `M1-SRC-002`, and `M1-SRC-003` were downloaded one at a time, matched exact catalog sizes and provider MD5 values, were promoted without replacement, and passed ZIP/SAFE container verification. `M1-SRC-004` then ended early at 561,593,598 bytes and was preserved as `transferred_size_mismatch`; it was not promoted or retried. Tokens, passwords, cookies, and authorization headers remain excluded from Git, chat, filenames, receipts, and captured command output.

The blank recovery review binds bundle SHA-256 `dffa194cc91636a35b5f55af6ece32bb6eb90d77b65ea3d9865413f912d146e7` to proposal SHA-256 `7b8b5e83265b37962f879ca7dad85ab5f5c04ceb28ee0f15fa774a79df7fd013`. Approval would authorize one fresh byte-zero transfer of the same exact `M1-SRC-004` through a distinct staging identity, preservation of the failed partial, and continuation only of the four still-unattempted products after recovery passes. The bundle contains zero human decisions and releases no action before explicit approval.

The parallel orbit route is at `M2-ORBIT-ACQUISITION-REVIEW`. The exact decision for review bundle SHA-256 `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1` and proposal SHA-256 `b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292` activated four approved `AUX_RESORB` identities. A stale production-wrapper test later crossed its assumed per-orbit custody guard after `M1-SRC-001` and `M1-SRC-002` became eligible. It used a tracked nonsecret test literal, made a public catalogue request and a rejected download request for exact `M2-ORB-001`, received zero payload bytes, and left no staging or destination payload. The attempt and both external events are retained as a terminal failure. The runner now requires the entire `M2-VERIFY` unit to be complete before catalogue access, token lookup, events, or payload requests.

The blank orbit recovery review binds bundle SHA-256 `df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b` to proposal SHA-256 `ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a`. It contains zero human decisions. Approval would permit only one fresh byte-zero `M2-ORB-001` recovery after full `M2-VERIFY` completion, using the existing protected owner credential reference and preserving the failed attempt and events. The other three orbit files remain authorized and unattempted; later `AUX_POEORB` substitution remains separately gated.

The active intake contract fixes sibling staging and custody paths, fail-on-collision and atomic no-replace promotion rules, secret references, and attempt retention. The reviewed proposal, acquisition plan, review bundle, and public blank response remain unchanged historical evidence.

A one-product transfer runner handled the four recorded attempts. It revalidated all four official pages and the exact catalog record before each started event, used exclusive staging, streamed SHA-256 and provider-MD5 checks, retained the truncated failure, refused replacement, and promoted only the three exact complete archives. Its synthetic readiness evidence remains historical; the real attempt and container receipts now provide the current operational evidence.

The Sentinel runner was corrected before first use so its generated attempt IDs satisfy the lowercase intake identifier grammar while its event timestamps remain RFC 3339. The active intake now preserves four append-only attempts: three succeeded and one failed.

The activation-time intake is preserved separately as an immutable snapshot so later append-only progress cannot erase its starting identity. A read-only acquisition-progress validator accepts only the authorized, staging, failed, and promoted states emitted by the runner; binds terminal receipts and promoted byte identity; rejects secret-bearing fields and product drift; and can reconcile external paths and bytes locally without requiring them in public CI. Nine focused tests cover those transitions. The current live result is four authorized, one failed, and three promoted products, with three matching passing container receipts and one retained external partial.

A separate checkpoint derivation tool converts only validated eight-product state counts into four explicit outcomes: authentication reference, acquisition in progress, retained-failure review, or container verification. It can emit no-replace candidate profile and goal controls under ignored scratch custody, but it never silently replaces tracked project truth. Eleven tests cover every transition, ambiguous counts, source immutability, candidate-output collision, and the exact blank recovery envelope.

The offline verification contract is also active for the exact eight products. Its per-product wrapper requires a promoted intake record and matching successful-transfer receipt, reads the archive without extraction, and checks catalog size, local SHA-256, provider MD5, ZIP safety and CRC, exact SAFE root, and the required radar or optical members. Five active-wrapper tests pass, and the three promoted radar archives have each passed this container-only verification.

The active offline materialization contract requires an exact promoted intake and passing container receipt, rechecks archive identity and the complete ZIP namespace, and writes one immutable external SAFE attempt plus a per-file hash manifest. A stale production-wrapper test unintentionally materialized `M1-SRC-001` under attempt ID `fixture-must-not-run`; that provenance remains explicit. The two other eligible archives, `M1-SRC-002` and `M1-SRC-003`, were then materialized deliberately one at a time under distinct planned identities. Across all three attempts, 78 files and 5,183,550,209 extracted bytes independently match their manifests. These append-only outputs establish materialization only: no raster readability, usable pixels, baseline, change, or scientific admission is established, and materialization alone releases no downstream processing.

A separate Sentinel-1 input-readiness gate was published for only those three materialized pre-event sources and passed public CI before one real inspection. All nine required members per source passed identity checks, all six annotations parsed with valid acquisition and embedded-orbit structure, and ArcGIS Pro 3.7.1 opened all six one-band U16 TIFF headers with matching dimensions. The exact gate still **blocked** all three sources because their annotations report `pixelValue` as `Detected`, while the frozen contract required `AMPLITUDE`. The receipt and unchanged 78-file custody inventory are retained; the result cannot be reinterpreted or retried under the current contract, and no pixel, baseline, or scientific action is released.

Official SentiWiki format evidence now confirms that the Sentinel-1 schema permits `Complex` or `Detected` and that GRD pixels physically represent detected amplitude. A review-only one-field amendment proposal is ready at SHA-256 `ebdcb763afd99ea23090c9bd83fd9e9cb6cb8dfbb2b5fed60edb80f1fa61c731`, bound into review bundle SHA-256 `831df5d5aae06862514667ad861c815154085fa3c546039e60f517d38ee442ff`. Its response is blank and contains zero human decisions. No corrected contract or rerun is authorized yet.

The materialized optical pair now has a separate ArcGIS header-readiness gate. It requires exact materialization receipts and per-file hashes, selects ten required SAFE members, parses baseline 05.12 scaling metadata, and checks native JP2 format, EPSG:32645, dimensions, cell sizes, and pair alignment. The PB 05.12 `MSK_CLASSI_B00.jp2` is modeled separately as a three-band 60 m Boolean mask. Twelve portable tests and an ArcGIS Pro 3.7.1 run on sixteen synthetic JPEG2000 rasters pass, including an expected block for a shifted after grid. No real materialization or pixel value was read.

A deterministic offline verification packet defines exact archive, checksum, ZIP-safety, SAFE-structure, band, polarization, and post-container pixel-readiness checks for the same eight products. Three real Sentinel-1 archives pass the container-only stage. Dataset readiness remains **DEFER** because the failed and unattempted products are incomplete and no real raster readability, AOI pixel coverage, masks, or registration result exists.

A metadata-only ArcGIS evidence workspace has also been built and validated in ArcGIS Pro 3.7.1 Advanced. Its EPSG:32645 File Geodatabase contains nine datasets, fourteen coded-value domains, eight relationship classes, three approved AOIs, and ten source-product metadata rows. The observation, interpretation, attribution, exclusion, stable-control, and QA structures are empty by design. The retained APRX, geodatabase, and PDF remain outside Git; the repository contains the schema, builder, validator, receipt, and a reviewed PNG preview.

Pixel-readiness thresholds are now fixed before product access in `config/qa/pixel-readiness-contract.json`. A dependency-free decision core and ArcGIS Pro 3.7.1 Spatial Analyst adapter have passed synthetic validation for all three approved AOIs, including an expected block for a 0.6-pixel grid shift and a required defer for unmeasured registration. These are control and runtime tests only; no real satellite pixels or scientific observations were admitted.

ArcGIS Pro's installed Sentinel-1 terrain-correction tools also expose a required DEM input. On 3 September 2026 the owner approved the exact four-tile Copernicus DEM GLO-30 amendment and accepted the hash-bound Copernicus WorldDEM-30 license. The fresh preflight confirmed the license bytes, all four official STAC identities and anonymous objects, 519.029 GiB free space, safe paths, and no collisions. The four exact tiles were then acquired, promoted, structurally verified, and processed through the fixed terrain-only ArcGIS screen. The external attempt-003 APRX, geodatabase, PNG, PDF, and rasters remain outside Git. The formal readiness audit is still `defer`, and the parallel workstream remains at `M2-DEM-VERTICAL-DATUM-REVIEW`; the original eight-product acquisition is independently paused at its retained-failure recovery review.

The Sentinel-1 baseline contract fixes independent ascending and descending processing routes, beta-nought calibration, gamma-nought terrain flattening, retained terrain-distortion masks, linear quantitative outputs, and EPSG:32645 delivery. Production processing still defers because the Copernicus DEM uses EGM2008 orthometric heights while ArcGIS's built-in geoid correction is documented as EGM96, the approved Sentinel scenes are not yet in verified custody, and the authorized restituted orbit files have not been transferred or verified.

The Sentinel-2 RUM route now has an equally explicit optical-processing contract. It reads processing baseline 05.12, per-band BOA offsets, and the quantification value from product metadata; keeps DN zero as NoData; applies the conservative SCL and quality masks; and produces a fixed 20 m EPSG:32645 grid. ArcGIS Pro 3.7.1 passed a synthetic runtime exercise of the reflectance and NDVI/MNDWI/NBR calculations. The real route remains deferred because product bytes, AOI usability, registration, and Sentinel-2C-to-2B stable-control behavior are still unmeasured, and the post-event scene remains high-cloud-risk.

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
- [M2 controlled SAFE materialization](docs/M2_SAFE_MATERIALIZATION.md)
- [M2 DEM dependency amendment review](docs/M2_DEM_AMENDMENT_REVIEW.md)
- [M2 DEM intake and offline verification](docs/M2_DEM_OFFLINE_VERIFICATION.md)
- [ArcGIS Sentinel-1 baseline processing protocol](docs/RADAR_BASELINE_PROCESSING_PROTOCOL.md)
- [ArcGIS Sentinel-2 optical baseline processing protocol](docs/OPTICAL_BASELINE_PROCESSING_PROTOCOL.md)
- [ArcGIS Sentinel-2 materialized-input readiness](docs/OPTICAL_INPUT_READINESS_PROTOCOL.md)
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
