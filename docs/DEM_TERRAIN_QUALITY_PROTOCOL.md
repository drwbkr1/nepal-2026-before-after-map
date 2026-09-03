# DEM terrain-quality protocol

## Purpose

This gate examines the four exact Copernicus GLO-30 tiles for gross elevation artifacts, discontinuities at their native boundaries, implausible local spikes, AOI terrain morphology, and ArcGIS usability. It is independent of the pending vertical-datum decision.

The gate may establish only **terrain QA fitness**. It cannot establish vertical accuracy, an ellipsoidal-height DEM, Sentinel-1 readiness, mapped change, event causation, or emergency guidance.

## Fixed inputs and thresholds

`config/qa/dem-terrain-quality-contract.json` binds:

- the exact active DEM intake and four promoted SHA-256 identities;
- the completed ArcGIS structural-verification summary;
- the owner-approved EPSG:32645 study areas;
- four explicit east-west and south-north native tile seams;
- elevation, local-curvature, seam-residual, plateau, and slope thresholds fixed before this inspection;
- the implementation, pure NumPy metric core, and synthetic tests;
- one exclusive external output path.

Tile-seam residuals compare the cross-boundary elevation step with the average immediately adjacent within-tile step. This detects gross tile offsets without treating normal mountain relief as a seam by itself. Numeric thresholds screen for obvious defects; they do not replace visual inspection or comparison with independent terrain control.

## ArcGIS outputs

The ArcGIS Pro runner creates a new external, non-Git attempt containing:

- a File Geodatabase;
- the native four-tile mosaic;
- a 30 m horizontal reprojection in EPSG:32645;
- an AOI-only DEM, slope, and hillshade;
- approved AOI and native seam feature classes;
- an editable ArcGIS Pro project;
- PNG and PDF review exports;
- a SHA-256 output manifest.

Source elevation values remain **EGM2008 orthometric metres**. No vertical transformation is applied. Horizontal reprojection does not make the DEM ellipsoidal and does not resolve the separate method review.

DEM-derived rasters and exports remain outside Git. The public repository may retain only scripts, contracts, tests, metrics, hashes, and claim-bounded receipts.

## Run command

Run only after the predeclaration commit is published:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" `
  scripts\inspect_m2_dem_terrain_quality_arcgis.py `
  --contract config\qa\dem-terrain-quality-contract.json `
  --output-root C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-001 `
  --candidate-receipt scratch\dem-terrain-quality-attempt-001\candidate-receipt.json `
  --executed-at-utc <current UTC timestamp>
```

The runner refuses a changed contract, source hash, authority record, AOI, implementation, existing output path, or receipt path. A runtime failure leaves its unique attempt directory in place for retention; it must not be reused or silently cleaned up.

## Decision rules

- **Block** on source or custody drift, output collision, nonfinite cells, physically impossible elevation bounds, gross local curvature, a gross seam residual, invalid CRS, or source mutation.
- **Defer** when a review-level quantitative flag, visual criterion, independent accuracy evidence, or vertical-datum decision remains unresolved.
- **Pass terrain QA only** when every quantitative and visual criterion passes. That pass can satisfy one prerequisite already authorized for later radar terrain processing; it creates no new authority.

Visual review must confirm that the AOI is present and unclipped, the map has no obvious rectangular fill, striping, checkerboard, or tile-edge step artifact, the terrain is spatially coherent at the displayed scale, and the CRS, source-height semantics, seam lines, and claim boundary are legible.
