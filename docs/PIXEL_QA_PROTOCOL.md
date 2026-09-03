# Pixel-readiness QA protocol

## Purpose

This protocol predeclares how raster coverage, masks, grids, and registration will be judged before any approved Sentinel product pixels are opened. It converts the general spatial, optical, and radar requirements in the project charter into deterministic decisions that can be inspected in ArcGIS Pro and reproduced by a dependency-free Python core.

The protocol does not activate M2. It does not authorize custody-root creation, credentials, network access, downloads, extraction, or processing of real products.

## Decision meanings

The machine-readable contract is `config/qa/pixel-readiness-contract.json`. Results use four states, in descending precedence:

| State | Meaning |
| --- | --- |
| `invalid` | Inputs are malformed, non-finite, impossible, or internally inconsistent. |
| `block` | The tested analytical route fails a predeclared minimum. The source identity is retained and is not automatically rejected. |
| `defer` | Evidence is missing or is adequate only for a bounded partial route that still requires review. |
| `pass_qa_only` | The measured QA property meets its threshold. This does not admit a scientific observation or establish change or causation. |

## Projected grid

All analytical area and distance measurements use WGS 1984 UTM Zone 45N, EPSG:32645, in meters. A before/after pair must have:

- EPSG:32645 on both rasters;
- positive, square, unrotated cells;
- matching cell sizes within 0.000001 m;
- origins aligned to an integer number of cells within 0.000001 pixels; and
- positive spatial overlap.

The optical multispectral change grid is 20 m. Ten-meter optical bands may be retained for display but are not silently substituted for the 20 m change grid. The candidate radar grid is 10 m and remains subject to confirmation after terrain correction.

## AOI coverage and masks

For each approved AOI, a result retains total AOI area, raster-covered area, valid area, excluded area by reason, coverage fraction, usable fraction of the whole AOI, and valid fraction within coverage.

| Metric | Pass | Defer | Block |
| --- | ---: | ---: | ---: |
| Raster coverage fraction | at least 0.99 | 0.20 to below 0.99 | below 0.20 |
| Usable fraction of the AOI | at least 0.80 | 0.20 to below 0.80 | below 0.20 |

Area totals must reconcile within 2% of AOI area. Negative, non-finite, zero-AOI, or inconsistent totals are `invalid`.

For Sentinel-2 Level-2A SCL, vegetation (4), non-vegetated surface (5), and water (6) are valid surface classes. Nodata, saturation/defects, dark or topographic shadow, cloud shadow, unclassified pixels, medium/high cloud, cirrus, and snow/ice are exclusions. Unknown classes are excluded and force review. A later real-product run must also retain the processing baseline, quantification value, BOA offset, and saturation/quality-mask evidence.

For Sentinel-1, class 1 is the proposed valid class. Nodata, layover, radar shadow, border noise, residual speckle or unstable background, water variability, and registration exclusions remain explicit mask classes. A real radar result also requires orbit direction, relative orbit, calibration, terrain correction, and layover/shadow records.

## Registration

Registration is `pass_qa_only` only with at least 30 stable-control pairs, RMSE no greater than 0.5 pixels, and absolute x and y bias no greater than 0.5 pixels. Measured RMSE from above 0.5 through 1.0 pixels is deferred unless another pass condition is met; RMSE above 1.0 pixels blocks the comparison. A missing measurement is `defer`, not a silent pass.

## Portable validation

The decision core has no third-party Python dependency:

```powershell
python -m unittest tests.test_pixel_qa_core -v
```

The tests exercise passing, partial, blocked, and invalid AOI routes; aligned, shifted, wrong-CRS, and non-overlapping grids; registration boundaries; and contract-mutation rejection.

## ArcGIS-native synthetic validation

ArcGIS Pro 3.7.1 Advanced and Spatial Analyst created deterministic 20 m synthetic rasters covering the three approved EPSG:32645 AOIs. The SCL fixture uses nine columns of class 4 followed by one column of class 9, producing about 90% usable area. The adapter uses `TabulateArea` to derive class areas for each AOI and passes those measurements to the portable decision core.

Run a new no-overwrite attempt with:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" scripts\validate_pixel_qa_arcgis.py `
  --output-root scratch\pixel-qa-synthetic-NEW-ATTEMPT `
  --receipt-output scratch\pixel-qa-synthetic-NEW-ATTEMPT-receipt.json
```

The validated receipt is `records/surface-receipts/pixel-qa-synthetic-arcgis.json`. Its ignored scratch rasters are local runtime evidence, not project data or release deliverables. A clean clone can verify the contract, core, receipt bindings, and decisions, but cannot reproduce the ArcGIS execution without ArcGIS Pro and Spatial Analyst.

## Future real-product boundary

After an exact M2 activation, successful intake, and container verification, a separate no-overwrite real-product runner may apply this contract to controlled rasters. It must bind source IDs and local checksums, preserve class-area details and all adverse outcomes, write results outside raw custody, and keep observation, interpretation, and attribution separate. No `pass_qa_only` result may be promoted into a mapped scientific observation without the later evidence and review gates in the roadmap.
