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
**Status:** Proposed and bound for owner review; not yet approved and no download is authorized.
