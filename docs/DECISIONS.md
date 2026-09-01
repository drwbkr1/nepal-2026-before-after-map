# Decision log

## D-001 — Public repository scope

**Decision:** Create a public repository containing methods, controls, small scripts, and lightweight evidence records.
**Reason:** Supports inspectability without placing large or restricted data in Git.
**Status:** Authorized for bootstrap by the owner.

## D-002 — Projected coordinate system

**Decision:** Use WGS 1984 UTM Zone 45N (EPSG:32645) as the master analytical CRS.
**Reason:** The study area lies in UTM zone 45N and projected units support defensible distance and area measurement.
**Status:** Proposed; confirm after final AOI review.

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
