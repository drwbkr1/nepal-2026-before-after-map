# M2 radar Esri-sequence recovery-005 review

## Decision requested

Approve one bounded authority envelope for `M2-RADAR-ESRI-SEQUENCE-RECOVERY-005`. The decision adopts Esri's documented Sentinel-1 processing order for this recovery, changes the recovery-specific primary despeckle policy from `NONE` to exact `REFINED_LEE`, and covers implementation through sanitized terminal publication without intermediate reconfirmation.

Exact proposal SHA-256: `5e7ca67eedecba76746e7c3862b691d0e954425cadadd0782ff90ed3f95ab217`

Official-method audit SHA-256: `1237c8e8cc6d3905228dd7797782782b0262d634489c62d56d6850c213e7f4eb`

## What recovery-004 established

The single recovery-004 attempt is terminal and consumed. M1-SRC-001 completed ApplyOrbitCorrection, RemoveThermalNoise, ApplyRadiometricCalibration, and ApplyRadiometricTerrainFlattening. ArcGIS then returned `ERROR 000425` inside the gamma ApplyGeometricTerrainCorrection call before a Raster was returned or saved. No later source or route ran, no retry occurred, and external custody was unchanged.

That evidence locates the failure boundary. It does not establish why ArcGIS could not create the orthorectified raster.

## New official-method evidence

Current official Esri documentation says to run Despeckle before Apply Geometric Terrain Correction. Esri's Sentinel-1 GRD workflow places Despeckle after Apply Radiometric Terrain Flattening and before Apply Geometric Terrain Correction. Its integrated RTC tool documents the same stages.

The installed ArcGIS Pro 3.7.1 interface was inspected without project data or geoprocessing. `arcpy.ia.Despeckle` returns a Raster, accepts `REFINED_LEE`, and supports the same save pattern already corrected in recovery-004. Esri documents filter size as inapplicable to Refined Lee, so the proposed call omits it:

```python
despeckled = arcpy.ia.Despeckle(gamma_slant, "VV;VH", "REFINED_LEE")
despeckled.save(gamma0_linear_despeckled_output)
```

The official sources are public vendor documentation used only as cited method guidance. No page content is redistributed, no account or credential is needed, and no executable payload or external dataset is adopted. Their current mutable content is recorded by exact URL and retrieval time, not content-hash locked.

## Why owner judgment is required

The existing frozen primary route says `no despeckle`. Inserting Refined Lee changes the scientific processing method and may change pixel values and downstream comparability. It therefore needs an explicit owner decision even though it also aligns the pipeline with Esri's documented prerequisite.

Approval will not mutate the historical contracts or recovery-004 evidence. Recovery-005 will use a new overlay contract, new code and receipt namespace, and a new absent attempt root.

## Exact proposed correction

The recovery-specific chain will insert one step after radiometric terrain flattening and before gamma geometric terrain correction:

1. Call `arcpy.ia.Despeckle(gamma_slant, "VV;VH", "REFINED_LEE")` with no output-path or filter-size argument.
2. Require a Raster-like return value with `save`.
3. Save exactly once to the predeclared absent `gamma0_linear_despeckled.crf`.
4. Require that output to exist.
5. Pass that exact output to gamma ApplyGeometricTerrainCorrection.

All recovery-004 call shapes and every source, orbit, DEM, AOI, CRS, grid, mask, threshold, registration, and route predicate remain unchanged. The mask GTC route remains unchanged and will stop the attempt if it fails.

## Single bounded attempt

- Attempt ID: `radar-pixel-orbit-application-esri-sequence-recovery-005-real-001`
- New absent root: `C:\Projects\Active\nepal-2026-before-after-map-data\r5\a1`
- One process and at most one real attempt
- Exact source order: M1-SRC-001 through M1-SRC-006
- Exact route order: PAIR-S1-ASC-R085-IW, then PAIR-S1-DESC-R121-IW
- Stop on the first failure
- No automatic retry, overwrite, network request, or credential action

Before that attempt, the approved implementation would require portable tests, an installed ArcGIS signature-only validation, public default-branch CI gates, and one final no-content preflight. The attempt root must still be absent at that preflight.

## What one approval covers

One approval covers the exact method-guidance adoption and recovery-specific scientific amendment, local implementation, packet and implementation publication, tests, public CI, one final no-content preflight, at most one fresh real attempt, exact reconciliation, and sanitized terminal publication. No intermediate owner reconfirmation will be requested while the scope remains unchanged.

## Limits

Approval does not authorize a second attempt; changes to the filter, source, orbit, DEM, AOI, CRS, grid, mask, threshold, registration, or route; credentials or network actions; baseline admission; change analysis; interpretation; attribution; derived-pixel publication; or scientific publication.

Neither this documentation audit nor a later recovery-005 result proves the historical cause of recovery-004. A full pass would mean only that the six sources and two routes passed the amended QA processing contract.

## Current state

This packet is local and has zero decisions. It authorizes no publication, implementation, project-data or external-custody access, ArcPy processing call, geoprocessing, or new real attempt.
