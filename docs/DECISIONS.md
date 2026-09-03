# Decision log

## D-001 — Public repository scope

**Decision:** Create a public repository containing methods, controls, small scripts, and lightweight evidence records.
**Reason:** Supports inspectability without placing large or restricted data in Git.
**Status:** Authorized for bootstrap by the owner.

## D-002 — Projected coordinate system

**Decision:** Use WGS 1984 UTM Zone 45N (EPSG:32645) as the master analytical CRS.
**Reason:** The study area lies in UTM zone 45N and projected units support defensible distance and area measurement.
**Status:** Confirmed after owner approval of the M1 search and review AOIs; ArcGIS Pro imported the EPSG:32645 derivative successfully.

## D-003 — Core imagery route

**Decision:** Prefer Sentinel-2 Level-2A and Sentinel-1 GRD for the reproducible public core.
**Reason:** Complementary optical/radar evidence and broadly accessible Copernicus data.
**Status:** Candidate products recorded; pixels and rights not yet verified.

## D-004 — High-resolution imagery

**Decision:** Keep Planet/Vantor or similar noncommercial imagery on a separate gated path.
**Reason:** Account terms and CC BY-NC or asset-specific restrictions may constrain use and redistribution.
**Status:** Deferred pending exact asset and license review.

## D-005 — Data custody

**Decision:** Exclude raw imagery, large rasters, geodatabases, packages, credentials, and licensed assets from Git.
**Reason:** Size, security, reproducibility, and third-party rights require controlled custody.
**Status:** Adopted in `.gitignore` and repository validation.

## D-006 — Repository license

**Decision:** Do not add a license during bootstrap.
**Reason:** Public visibility is not a license, and the owner has not selected terms for original repository content.
**Status:** Owner decision pending.

## D-007 — Scientific wording

**Decision:** Default to “satellite-observed change” and keep observation, interpretation, and attribution separate.
**Reason:** Before/after proximity alone does not prove causation.
**Status:** Adopted as a project rule.

## D-008 — M1 search and review AOIs

**Decision:** Approve the exact three-area geometry bound to SHA-256 `68c406f7f41c301c339e200ccdd75194183c483c65156ab3949e64236072ccde` for M1 source discovery, review, and ArcGIS organization.
**Reason:** The regional overview, source area, and upper corridor provide explicit, reproducible bounds while remaining separate from future mapped change polygons.
**Status:** Approved by the owner through locked human-review response `3e7198c5919fde579bc7864ceba6ce44d5fc91b9920fb0608a6857af54174bb9`; this does not authorize full-product acquisition or scientific conclusions.

## D-009 — Candidate source-manifest route

**Decision:** Propose all six Sentinel-1 GRD records and the two Sentinel-2 RUM records for controlled acquisition planning; defer both Sentinel-2 RUL context records; reject none at metadata/quicklook stage.
**Reason:** RUM and the detailed radar slices intersect the approved event-area AOIs, while RUL contributes only cloud-limited regional context. Inconclusive candidates remain preserved until pixel QA.
**Status:** Approved by the owner for controlled acquisition planning through source-manifest review bundle SHA-256 `dd7d85562134e2c0cc2115eabdf329de56763209918dc65c872ceed911900544` and candidate manifest SHA-256 `6c67a1a6cb3411bd9ccab5f837e2c060757ddc5f1317f171bc5f62f9b1a22eef`. The approval does not authorize authentication, terms acceptance, or downloads.

## D-010 — Proposed M2 controlled-acquisition boundary

**Decision:** Propose a bounded M2 route for a fresh storage preflight, external non-Git custody, use of an owner-controlled existing Copernicus account or authenticated session, and download and verification of only the eight exact M1-approved products.
**Reason:** M1 has fixed source identities and dispositions, but product custody, pixels, masks, rights at access time, checksums, and baseline quality remain untested.
**Status:** Approved by the owner on 3 September 2026 through the exact review bundle SHA-256 `e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d` and acquisition-plan SHA-256 `6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d`. The completed response was locked and reconciled before activation. New or changed terms, account changes, credential disclosure, spending, products outside the exact eight, and scientific publication remain outside the approval.

## D-011 — ArcGIS evidence model

**Decision:** Store direct satellite observations, analyst interpretations, and event-attribution assessments in distinct related datasets, with separate exclusion, stable-control, source-link, and QA structures.
**Reason:** A projected map must preserve the difference between measured change, possible geomorphic meaning, and causal support while retaining failed, rejected, deferred, inconclusive, invalid, and superseded evidence states.
**Status:** Implemented and validated as a metadata-only EPSG:32645 ArcGIS Pro 3.7.1 workspace. Scientific datasets remain empty; no acquisition or scientific claim is implied.

## D-012 — Offline container verification before pixel admission

**Decision:** Require exact local SHA-256, provider-MD5 agreement, catalog-size review, safe ZIP structure, CRC, exact SAFE root identity, and analysis-critical Sentinel-1 or Sentinel-2 members before any acquired product advances to raster and AOI pixel QA.
**Reason:** A successful transfer or present filename does not establish a complete, untampered, analysis-capable product; a complete container still does not establish usable pixels or scientific fitness.
**Status:** Implemented as deterministic controls with synthetic tests. M2 is now active, but the historical pre-acquisition readiness audit remains `defer` because no product bytes have been examined.

## D-013 — Predeclared projected pixel-readiness thresholds

**Decision:** Judge each real-product route against fixed EPSG:32645 AOI-coverage, mask, grid-alignment, and registration rules before admitting satellite observations. Treat a QA pass as fitness evidence only; retain route-level `block`, `defer`, and `invalid` outcomes without automatically rejecting the source identity.
**Reason:** Pixel usability cannot be inferred from catalog coverage or container structure, and thresholds chosen after viewing change could bias the result. A portable core keeps decisions reproducible while an ArcGIS-native adapter proves projected area and raster-grid behavior on the target platform.
**Status:** Contract and core implemented before product access. ArcGIS Pro 3.7.1 Advanced and Spatial Analyst passed deterministic 20 m synthetic coverage for all three approved AOIs, passed an aligned pair, blocked an intentional 0.6-pixel shift, and deferred unmeasured registration. No real pixels or scientific evidence were admitted.

## D-014 — Activated M2 source gate and empty custody initialization

**Decision:** Execute only the approved non-mutating live preflight, then create the exact empty external custody and staging structure after every source, rights, identity, path, collision, and storage check passes.
**Reason:** Catalog approval alone does not establish current availability or a safe destination, and authentication must remain separate from public records and filesystem initialization.
**Status:** Completed on 3 September 2026. All eight exact products were online with unchanged names, UUIDs, sizes, and provider checksums; the source gate passed 64 required criteria; 514.942 GiB was free; and matching repository/external custody receipts have SHA-256 `12812d1c53e13ec287425f74a1988f5c0be7d0638f856c9606fddf1c1431fb09`. No authentication or product transfer occurred. Work stops at `M2-AUTHENTICATION-REFERENCE` pending a secret-safe existing owner-controlled credential or session reference.

## D-015 — Fail-closed one-product transfer state machine

**Decision:** Transfer only one exact approved product per invocation through exclusive staging, append-before-transfer evidence, streamed SHA-256 and provider-MD5 verification, redirect refusal, retained failures, and atomic hard-link no-replace promotion.
**Reason:** An authenticated HTTP response is not custody evidence, and a collision, changed page, changed catalog identity, partial file, or checksum mismatch must remain visible without overwriting existing bytes.
**Status:** Implemented and covered by eleven local fixture tests. The readiness receipt records no network request, authentication, active-intake mutation, or product bytes. Real execution remains at the secret-safe authentication-reference gate.

## D-016 — Active per-product offline container verification

**Decision:** Activate the predeclared container controls for the exact eight M2 products and require a promoted active-intake identity plus successful-transfer receipt before any archive scan.
**Reason:** Candidate checks built before activation must be bound to the current approval and custody, while archive access must remain offline, read-only, non-extracting, and separate from pixel or scientific admission.
**Status:** Active contract and per-product wrapper implemented. Five tests verify authority, exact product controls, custody bindings, offline behavior, and refusal of an unpromoted asset. No real archive bytes were read during activation or testing.

## D-017 — Proposed exact DEM dependency amendment

**Decision:** Prepare, but do not activate, an M2 amendment for the exact four Copernicus DEM GLO-30 COG tiles that cover the approved AOIs and for explicit acceptance of the exact hash-bound Copernicus WorldDEM-30 license.
**Reason:** The installed ArcGIS Pro Sentinel-1 terrain-correction tools accept or require a DEM, while the active M2 approval covers only eight Sentinel products and forbids new terms acceptance or extra products. The anonymous AWS route avoids a new account but does not remove the license-acceptance requirement.
**Status:** Awaiting owner decision through review bundle SHA-256 `caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e` and amendment proposal SHA-256 `92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69`. Metadata-only probes confirmed four exact objects totaling 170,302,058 bytes; no DEM payload, acceptance, authentication, or processing occurred.

## D-018 — Predeclared DEM verification and Sentinel-1 processing boundaries

**Decision:** Derive non-authorizing intake and ArcGIS GeoTIFF verification controls for the exact four proposed DEM tiles, and fix the two independent Sentinel-1 processing routes before real pixels are available.
**Reason:** A reviewed source list does not define safe custody or raster acceptance, and ArcGIS processing defaults could otherwise hide consequential choices about orbit vectors, despeckling, terrain masks, units, or vertical datum.
**Status:** Static controls and thirteen local tests pass. Production processing remains deferred because the DEM amendment is unapproved, the source heights are EGM2008 orthometric while ArcGIS documents EGM96 for its built-in geoid option, and updated orbit files are not authorized auxiliary products. No payload byte, external custody path, or scientific result was created.

## D-019 — Predeclared Sentinel-2 Level-2A processing

**Decision:** Fix the exact RUM pair, metadata-derived BOA scaling, DN-zero treatment, conservative SCL mask, 20 m EPSG:32645 grid, contextual indices, and cross-platform comparison controls before reading product pixels.
**Reason:** Processing baseline 05.12 requires band-specific offsets and metadata verification, while a high-cloud post-event scene and an S2C-to-S2B comparison could otherwise invite hidden mask, scaling, or harmonization changes.
**Status:** Fifteen portable tests and one ArcGIS Pro 3.7.1 synthetic run pass. Five scaled bands and NDVI, MNDWI, and NBR matched declared values with DN-zero and SCL exclusions preserved. Missing and duplicate offset controls are covered. Real metadata, pixels, AOI coverage, registration, optical change, and scientific admission remain unestablished.
