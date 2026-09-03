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
**Status:** Proposed for owner review in bundle SHA-256 `e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d`. No M2 authority exists until an exact completed decision is locked and reconciled. New or changed terms, account changes, spending, and scientific publication remain outside the proposal.

## D-011 — ArcGIS evidence model

**Decision:** Store direct satellite observations, analyst interpretations, and event-attribution assessments in distinct related datasets, with separate exclusion, stable-control, source-link, and QA structures.
**Reason:** A projected map must preserve the difference between measured change, possible geomorphic meaning, and causal support while retaining failed, rejected, deferred, inconclusive, invalid, and superseded evidence states.
**Status:** Implemented and validated as a metadata-only EPSG:32645 ArcGIS Pro 3.7.1 workspace. Scientific datasets remain empty; no acquisition or scientific claim is implied.

## D-012 — Offline container verification before pixel admission

**Decision:** Require exact local SHA-256, provider-MD5 agreement, catalog-size review, safe ZIP structure, CRC, exact SAFE root identity, and analysis-critical Sentinel-1 or Sentinel-2 members before any acquired product advances to raster and AOI pixel QA.
**Reason:** A successful transfer or present filename does not establish a complete, untampered, analysis-capable product; a complete container still does not establish usable pixels or scientific fitness.
**Status:** Implemented as deterministic, non-authorizing controls with synthetic tests. The product-readiness audit remains `defer` because M2 is not active and no product bytes have been examined.

## D-013 — Predeclared projected pixel-readiness thresholds

**Decision:** Judge each real-product route against fixed EPSG:32645 AOI-coverage, mask, grid-alignment, and registration rules before admitting satellite observations. Treat a QA pass as fitness evidence only; retain route-level `block`, `defer`, and `invalid` outcomes without automatically rejecting the source identity.
**Reason:** Pixel usability cannot be inferred from catalog coverage or container structure, and thresholds chosen after viewing change could bias the result. A portable core keeps decisions reproducible while an ArcGIS-native adapter proves projected area and raster-grid behavior on the target platform.
**Status:** Contract and core implemented before product access. ArcGIS Pro 3.7.1 Advanced and Spatial Analyst passed deterministic 20 m synthetic coverage for all three approved AOIs, passed an aligned pair, blocked an intentional 0.6-pixel shift, and deferred unmeasured registration. No real pixels or scientific evidence were admitted.
