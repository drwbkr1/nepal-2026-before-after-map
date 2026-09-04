# ArcGIS Sentinel-1 materialized-input readiness protocol

## Purpose

This gate sits between SAFE materialization and any Sentinel-1 pixel processing. It verifies exact selected-file identity, parses the native annotation metadata and embedded state-vector structure, and asks the installed ArcGIS runtime to open only the two measurement-raster headers in each available SAFE. It does not decode, summarize, display, or process measurement pixels.

The machine-readable contract is `config/qa/radar-input-readiness-contract.json`. It is limited to the three currently promoted, container-verified, and materialized pre-event sources:

| Source | Route | Role | Product |
|---|---|---|---|
| `M1-SRC-001` | Ascending relative orbit 85 | Before supporting slice | `S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057.SAFE` |
| `M1-SRC-002` | Ascending relative orbit 85 | Before primary slice | `S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB.SAFE` |
| `M1-SRC-003` | Descending relative orbit 121 | Before primary scene | `S1D_IW_GRDH_1SDV_20260819T001036_20260819T001101_004187_007ABD_DC16.SAFE` |

`M1-SRC-001` keeps its unintended-test materialization provenance. Passing this gate does not change that provenance.

## Entry conditions

For each source, the runner requires the exact repository materialization-receipt SHA-256 fixed in the contract. The receipt must remain `pass_materialization_only`, identify the exact product, bind the current materialization contract, and point within the exact non-Git data root. Its external manifest and `completed.json` marker must match. The runner then rehashes every selected member before parsing metadata or importing ArcPy.

The action is inherited from the active M2 authorization as read-only inspection, metadata capture, routine QA, and evidence recording. Network access, authentication, credential access, external-data mutation, pixel decoding, derived-raster output, and receipt replacement are prohibited.

## Required SAFE members

Each SAFE must contain exactly one of each:

- `manifest.safe`;
- VV and VH product annotation XML;
- VV and VH calibration XML;
- VV and VH noise XML;
- VV and VH measurement TIFF.

Missing, duplicate, empty, unsafe, or non-SHA-256-bound required members block the source.

## Annotation and orbit checks

Both polarization annotations must parse without a DTD or entity declaration and agree with the approved source on mission `S1D`, product type `GRD`, mode and swath `IW`, polarization, acquisition times within one second, absolute orbit number, and orbit direction. Dimensions and pixel spacings must be positive. Pixel values must be amplitude encoded as 16-bit unsigned integers.

The embedded orbit list must contain at least two finite position and velocity vectors, agree with its declared count, use strictly increasing times, and bracket the acquisition window. This establishes structural readability of the embedded vectors only. It does not treat predicted vectors as sufficient for controlled baseline processing or replace the separately approved `AUX_RESORB` route.

## ArcGIS raster-header checks

ArcGIS Pro must open each VV and VH measurement TIFF as one-band `U16` data. Its width and height must match the corresponding annotation, and VV and VH must agree on dimensions, band count, and pixel type within each source.

The raw GRD measurement TIFF is not treated as an EPSG:32645 analysis raster. Projection to EPSG:32645 occurs only after the separately gated orbit, DEM vertical-datum, terrain-correction, mask, and registration steps.

## Decision semantics

A per-source pass is `pass_header_readability_only`. If all three available sources pass, the aggregate result is `pass_partial_pre_event_header_readiness_only`. That result remains partial because no post-event radar source is in promoted verified custody.

A pass does not establish pixel values, AOI coverage, layover or shadow fitness, updated-orbit application, terrain correction, registration, a complete pair, a baseline, observable change, interpretation, attribution, or scientific admission. It releases no baseline processing while `M2-VERIFY`, `M2-ORBIT-APPLY`, the DEM vertical decision, terrain-result review, and pixel-readiness gates remain incomplete.

## Synthetic validation and retained attempts

Fourteen portable tests cover contract narrowing, inventory selection, unsafe and duplicate paths, complete-payload XML declaration screening, exact annotation identity, orbit ordering and acquisition bracketing, TIFF header consistency, VV/VH metadata agreement, cross-polarization mismatch, and the partial-result boundary.

ArcGIS Pro 3.7.1 Advanced opened six synthetic U16 TIFFs. Three aligned synthetic sources passed header-readiness only, while a deliberate VH width mismatch blocked. No real materialization receipt, external custody file, or real product byte was read.

The first passing synthetic attempt is retained with its exact prepublication contract because the orbit-time rule was subsequently strengthened to require acquisition-window bracketing. Attempt 002 failed after creating one tiny synthetic TIFF when ArcGIS exposed a `datetime` name collision; its five files, failure receipt, and exact prepublication contract are retained. Attempt 003 was superseded when the production receipt was clarified to distinguish attempted versus completed metadata and header reads. Attempt 004 was superseded when the gate expanded DTD/entity screening to the complete XML payload, added VV/VH annotation agreement, and disabled GDAL PAM sidecar creation before real access. Attempt 005 was superseded when the production runner was refactored so every receipt, manifest, selected-member, and annotation check completes before ArcPy import. Attempt 006 was superseded after publication review found that its pre-ArcGIS block path could evaluate `arcpy.ProductInfo()` while ArcPy was intentionally unavailable. Attempt 007 uses a new output identity, records a pre-ArcGIS block without importing ArcPy, and binds the published contract.

Rerun synthetic validation only to new paths:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" `
  scripts\validate_radar_input_readiness_arcgis.py `
  --output-root scratch/radar-input-readiness-arcgis-<new-id> `
  --receipt-output records/surface-receipts/radar-input-readiness-synthetic-arcgis-<new-id>.json `
  --verified-at-utc <RFC-3339-UTC>
```

After the exact contract and synthetic evidence are published and reverified, run the real read-only inspection once to a new receipt:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" `
  scripts\inspect_radar_inputs_arcgis.py `
  --checked-at-utc <RFC-3339-UTC> `
  --receipt-output records/readiness/radar-input/m2-s1-input-readiness-real-001.json
```

The production runner hashes each materialization-attempt inventory before and after ArcGIS access. Any new sidecar, changed file, missing file, or changed hash blocks the result and remains evidence.
