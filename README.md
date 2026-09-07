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

This goal is **active as of 7 September 2026**. M1 is complete, and all eight exact Sentinel products are promoted, container verified, and materialized by identity. The optical route remains terminal `INVALID`/`BLOCK` under its fixed criteria. All four approved Sentinel-1D `AUX_RESORB` files are promoted in controlled non-Git custody. The four-source verifier passed public CI, activation, and its no-content preflight, but its first real invocation read and evaluated `M2-ORB-001` before discovering that the public receipt directory was absent. No durable pass or fail result exists; the attempt is terminal indeterminate, external custody remained unchanged, and the other three EOFs were not read. A hash-bound recovery review now proposes only a pre-read receipt-reservation correction and one new `M2-ORB-001` recovery attempt before conditional fixed-order continuation. It contains zero decisions and awaits public CI before owner review. Four approved Copernicus DEM tiles remain independently gated by unresolved vertical-datum and terrain-result reviews. No orbit application, radar-pixel decoding, baseline, change result, attribution, or scientific conclusion has been established.

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

The current operational checkpoint is `M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW-PUBLICATION`. Corrected continuation commit `ac19e1bd818e86b94bbd35ecf53fe93863ca91f5` passed public CI run `34065851960` before activation, final no-payload preflight, and one owner-controlled secret-safe handoff. The supervisor requested exact `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` once each in that order and promoted all three without replacement; their SHA-256 values are `7462fa65549339c09c36338cb690d0b953c665c3c61a397def3cfa7b2d453262`, `c08bf997f1bf02fb25dcf2a4f35643aef4754fbea03c6c2fb0fa9db4a0efe778`, and `281388e94a7a8a708f229fd7d19f93de426bb077699db3aaabdad7125043bd83`. Preserved `M2-ORB-001` remains `a72c93e500a1c09b62b4cd31889837c9d57ccc41542b16397ff9f2c0fccba3f4`.

Four-source verifier commit `308b6d079696a5f5973f7daa02e137e07a14eea3` then passed public CI run `34145814247`, activation, and final no-content preflight. The first invocation evaluated `M2-ORB-001`, but its receipt write stopped at `verification_output_parent_missing`. The result is retained as terminal indeterminate rather than inferred; no receipt was written, external orbit custody was not mutated, and later source reads did not occur. Recovery proposal SHA-256 `0be64071cfe718ca758155ff0422cfee48af342c8a560528746adc653e6a2fcf` and review bundle SHA-256 `d2f0f75f40614c56bc0e62c6eecb1588f7504f50927448192673e6e403b5933f` propose reserving the append-only receipt before each EOF read, without changing any source, checksum, XML, OSV, scene-binding, or one-second endpoint rule. The packet is blank and grants no recovery authority before public CI and one attested owner decision.

The approved dependency-ordered materialization and header-readiness stages are complete. Optical real-001 stopped after its first SCL read because the production grid nests its bounds under `analysis_grid.extent`; it produced no AOI, mask, registration, baseline, or change metric and remains terminal `INVALID`. The owner approved recovery bundle SHA-256 `d137b8ac1d46531ae42e7944955829eb2df37985428431b39863f4a157e83ac2` and proposal SHA-256 `96f0125628e894061fc5da55faff94e92e51b0385293576177c1e15bd009b3da`. Ten portable tests, the exact nested-shape ArcGIS synthetic, commit `395b63e1bd5c53a39ca3e2601768ba5a00f4bcf4`, CI run `33989213698`, and the no-pixel preflight passed. The one recovery invocation then measured the exact pair and ended `BLOCK`: 6.3252 percent of the source AOI and 25.6403 percent of the upper corridor were usable, while registration deferred with 20 accepted controls. Radar pixel decoding, orbit or DEM actions, baselines, before/after change products, retries, source substitution, and scientific publication are excluded.

The two failed `M1-SRC-004` partials remain immutable at 561,593,598 and 1,333,788,672 bytes. Recovery-002 later promoted the exact product at 1,732,332,897 bytes with SHA-256 `a606cac063cc23e60a623f020192fc097d327f3dafadf1115802b2a458eaceab`. Its first detached supervisor then stopped before continuation, so a separate owner decision authorized continuation-001 without another `M1-SRC-004` request. Portable implementation commit `68ac0484d598790cc8c47a8747a674b7d5d9de73` passed public CI run `33942997642` before activation, final no-payload preflight, credential handoff, and the four successful transfers.

The orbit route now uses the approved six-source radar custody, materialization, and header-readiness branch instead of aggregate `M2-VERIFY`. The exact decision for review bundle SHA-256 `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1` and proposal SHA-256 `b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292` activated four approved `AUX_RESORB` identities. A stale production-wrapper test later crossed its assumed per-orbit custody guard, used a tracked nonsecret test literal, and reached a rejected exact `M2-ORB-001` request. It received zero payload bytes and left no staging or destination payload. The attempt and both external events remain terminal evidence. The ordinary orbit wrapper now stops with `orbit_recovery_002_unit_not_complete` before catalogue access, token lookup, events, or payload requests.

The old blank orbit recovery review binds bundle SHA-256 `df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b` to proposal SHA-256 `ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a`. It remains exact historical evidence but is classified `stale_unapproved_preserved_not_actionable`. The corrected recovery-002 review is narrower: it covers only `M2-ORB-001`; the other three orbit files remain unattempted and are not released by that review. Later `AUX_POEORB` substitution remains separately gated.

The active intake contract fixes sibling staging and custody paths, fail-on-collision and atomic no-replace promotion rules, secret references, and attempt retention. The reviewed proposal, acquisition plan, review bundle, and public blank response remain unchanged historical evidence.

A one-product transfer runner handled each source attempt. It revalidated the official controls and exact catalog record before each started event, used exclusive staging, streamed SHA-256 and provider-MD5 checks, retained failed partials, refused replacement, and promoted only complete archives. Its synthetic readiness evidence remains historical; the real attempt and container receipts provide the current operational evidence.

The active intake now preserves nine append-only Sentinel attempts: eight succeeded and one initial transfer failed. The separate recovery-001 failed partial is also retained under its own recovery evidence. Continuation-001 made exactly four new attempts, stopped only after all four succeeded, and did not request `M1-SRC-004`.

The activation-time intake is preserved separately as an immutable snapshot so later append-only progress cannot erase its starting identity. A read-only acquisition-progress validator accepts only the authorized, staging, failed, and promoted states emitted by the runner; binds terminal receipts and promoted byte identity; rejects secret-bearing fields and product drift; and can reconcile external paths and bytes locally without requiring them in public CI. The current live result is eight promoted products across nine attempts, with eight matching passing container receipts and both earlier failed partials retained externally. Two post-success validation failures are also retained because stale tests and controls initially assumed the earlier acquisition state; neither affected product custody.

A separate checkpoint derivation tool converts only validated eight-product state counts and bound control evidence into explicit checkpoints. It can emit no-replace candidate profile and goal controls under ignored scratch custody, but it never silently replaces tracked project truth. Its earlier recovery-003 review route is retained as history; current live truth comes from the terminal recovery-003 reconciliation and the separately hash-bound OSV precision amendment packet.

The offline verification contract is also active for the exact eight products. Its per-product wrapper requires a promoted intake record and matching successful-transfer receipt, reads the archive without extraction, and checks catalog size, local SHA-256, provider MD5, ZIP safety and CRC, exact SAFE root, and the required radar or optical members. All eight exact archives have passed this container-only verification.

The active offline materialization contract requires an exact promoted intake and passing container receipt, rechecks archive identity and the complete ZIP namespace, and writes one immutable external SAFE attempt plus a per-file hash manifest. A stale production-wrapper test unintentionally materialized `M1-SRC-001` under attempt ID `fixture-must-not-run`; that provenance remains explicit. The two other eligible archives, `M1-SRC-002` and `M1-SRC-003`, were then materialized deliberately one at a time under distinct planned identities. Across all three attempts, 78 files and 5,183,550,209 extracted bytes independently match their manifests. These append-only outputs establish materialization only: no raster readability, usable pixels, baseline, change, or scientific admission is established, and materialization alone releases no downstream processing.

A separate Sentinel-1 input-readiness gate was published for only those three materialized pre-event sources and passed public CI before one real inspection. All nine required members per source passed identity checks, all six annotations parsed with valid acquisition and embedded-orbit structure, and ArcGIS Pro 3.7.1 opened all six one-band U16 TIFF headers with matching dimensions. The exact gate still **blocked** all three sources because their annotations report `pixelValue` as `Detected`, while the frozen contract required `AMPLITUDE`. The receipt and unchanged 78-file custody inventory are retained; the result cannot be reinterpreted or retried under the current contract, and no pixel, baseline, or scientific action is released.

An exact owner-approved versioned amendment later corrected only that schema label after official Sentinel-1 review. The amendment passed focused and synthetic checks, then public CI, before one read-only real-002 invocation. Real-002 passed the same three sources for member, annotation, embedded-vector, and TIFF-header readiness, with the 78-file custody inventory unchanged. This was a post-observation confirmation rather than blind validation. The original block remains retained, no measurement pixels were decoded, no before-after pair is complete, and the result releases no baseline or scientific processing.

Official SentiWiki format evidence confirmed that the Sentinel-1 schema permits `Complex` or `Detected` and that GRD pixels physically represent detected amplitude. The owner approved the exact one-field amendment, and one publication-gated real-002 header inspection passed for the three materialized pre-event scenes. The original block remains part of the evidence, real-002 cannot be rerun, and the result releases no pixel decoding or baseline work.

The materialized optical pair now has a separate ArcGIS header-readiness gate. It requires exact materialization receipts and per-file hashes, selects ten required SAFE members, parses baseline 05.12 scaling metadata, and checks native JP2 format, EPSG:32645, dimensions, cell sizes, and pair alignment. The PB 05.12 `MSK_CLASSI_B00.jp2` is modeled separately as a three-band 60 m Boolean mask. Twelve portable tests and an ArcGIS Pro 3.7.1 run on sixteen synthetic JPEG2000 rasters pass, including an expected block for a shifted after grid. No real materialization or pixel value was read.

A deterministic offline verification packet defines exact archive, checksum, ZIP-safety, SAFE-structure, band, polarization, and post-container pixel-readiness checks for the same eight products. All eight archives pass the container-only stage. Dataset readiness remains **DEFER** because five products are not materialized and no complete real before/after route has passed raster readability, AOI pixel coverage, masks, or registration.

A metadata-only ArcGIS evidence workspace has also been built and validated in ArcGIS Pro 3.7.1 Advanced. Its EPSG:32645 File Geodatabase contains nine datasets, fourteen coded-value domains, eight relationship classes, three approved AOIs, and ten source-product metadata rows. The observation, interpretation, attribution, exclusion, stable-control, and QA structures are empty by design. The retained APRX, geodatabase, and PDF remain outside Git; the repository contains the schema, builder, validator, receipt, and a reviewed PNG preview.

A bounded `.ppkx` portability fixture for that exact metadata-only workspace passed one publication-gated ArcGIS Pro 3.7.1 package, extraction, reopen, and re-export round trip. All three operational layers resolve inside the extraction tree, the nine-dataset schema retains zero scientific rows, the source inventory is unchanged, and the PNG is pixel-identical and visually approved. A later post-run verification mistake created a second unplanned extraction directory; it is preserved as a process-conformance failure. The qualified pass establishes same-machine package mechanics only, not clean-machine portability or M6 completion.

Pixel-readiness thresholds are now fixed before product access in `config/qa/pixel-readiness-contract.json`. A dependency-free decision core and ArcGIS Pro 3.7.1 Spatial Analyst adapter have passed synthetic validation for all three approved AOIs, including an expected block for a 0.6-pixel grid shift and a required defer for unmeasured registration. These are control and runtime tests only; no real satellite pixels or scientific observations were admitted.

ArcGIS Pro's installed Sentinel-1 terrain-correction tools also expose a required DEM input. On 3 September 2026 the owner approved the exact four-tile Copernicus DEM GLO-30 amendment and accepted the hash-bound Copernicus WorldDEM-30 license. The four exact tiles were acquired, promoted, structurally verified, and processed through the fixed terrain-only ArcGIS screen. The external attempt-003 APRX, geodatabase, PNG, PDF, and rasters remain outside Git. The formal readiness audit is still `defer`, and the parallel workstream remains at `M2-DEM-VERTICAL-DATUM-REVIEW`; Sentinel transfer and container verification are complete at the independent `M2-VERIFY` checkpoint.

The Sentinel-1 baseline contract fixes independent ascending and descending processing routes, beta-nought calibration, gamma-nought terrain flattening, retained terrain-distortion masks, linear quantitative outputs, and EPSG:32645 delivery. Production processing still defers because five relevant products remain unmaterialized, real pixel readiness is incomplete, the Copernicus DEM uses EGM2008 orthometric heights while ArcGIS's built-in geoid correction is documented as EGM96, and the authorized restituted orbit files have not been transferred or verified.

The Sentinel-2 RUM route now has an equally explicit optical-processing contract. It reads processing baseline 05.12, per-band BOA offsets, and the quantification value from product metadata; keeps DN zero as NoData; applies the conservative SCL and quality masks; and produces a fixed 20 m EPSG:32645 grid. ArcGIS Pro 3.7.1 passed a synthetic runtime exercise of the reflectance and NDVI/MNDWI/NBR calculations. The real optical archives are in verified container custody but remain unmaterialized; AOI usability, registration, Sentinel-2C-to-2B stable-control behavior, and the high-cloud-risk post-event scene remain unmeasured.

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
