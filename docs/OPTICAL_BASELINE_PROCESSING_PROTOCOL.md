# ArcGIS Sentinel-2 optical baseline processing protocol

## Purpose

This protocol fixes how the approved Sentinel-2 RUM pair will be converted from Level-2A product digital numbers into comparable, projected surface-reflectance and index layers. It is declared before product access so cloud masking, scaling, resampling, or normalization cannot be changed merely to make the event look clearer.

The exact route is:

| Role | Source | Product |
|---|---|---|
| Before | `M1-SRC-010`, Sentinel-2C | `S2C_MSIL2A_20260812T045701_N0512_R119_T45RUM_20260812T100317.SAFE` |
| After | `M1-SRC-008`, Sentinel-2B | `S2B_MSIL2A_20260827T045659_N0512_R119_T45RUM_20260827T084453.SAFE` |

Both names declare processing baseline 05.12, tile 45RUM, and relative orbit 119. Those name-derived values must match the internal metadata after acquisition. The pre-event catalog cloud estimate is 18.746611%; the post-event estimate is 78.471315%, so the route may remain partial or inconclusive after real mask inspection.

The machine-readable contract is `config/qa/optical-baseline-processing-contract.json`.

## Reflectance scaling

For every used band, the workflow reads `BOA_QUANTIFICATION_VALUE` and the band-specific `BOA_ADD_OFFSET` from `MTD_MSIL2A.xml`. Processing-baseline 04.00 and later Level-2A products use:

```text
BOA reflectance = (DN + BOA_ADD_OFFSET_band) / BOA_QUANTIFICATION_VALUE
```

DN 0 is changed to NoData before the offset is applied. Missing, duplicate, nonnumeric, or internally inconsistent metadata blocks the route. A hardcoded divide by 10,000 without first checking the metadata is prohibited. Valid negative or above-one reflectance values remain in the quantitative output and are not silently clamped.

## Bands and grid

The quantitative grid is EPSG:32645 at 20 m. It is anchored to the owner-approved AOI union, snapped outward to exact 20 m multiples:

- xmin 273,300 m;
- ymin 3,070,220 m;
- xmax 367,820 m;
- ymax 3,149,220 m;
- 4,726 columns by 3,950 rows.

B02, B03, B04, and B08 are resampled from their native 10 m grids using bilinear interpolation. B11, B12, and SCL use their native 20 m products; categorical masks use nearest-neighbor handling. Grid, origin, extent, rotation, or CRS drift blocks the pair.

The fixed change core contains B02, B03, B04, B08, B11, and B12. Display copies may use B04/B03/B02 true color and B08/B04/B03 false color, but display stretches do not alter quantitative rasters.

## Masking

The primary mask follows `config/qa/pixel-readiness-contract.json`:

- SCL 4 vegetation, 5 nonvegetated surface, and 6 water are initially valid;
- all other SCL classes are excluded;
- DN 0, saturation, defective-pixel, and required quality-mask failures are excluded;
- an unknown SCL class is excluded and sends the route to review;
- excluded area is measured by reason for every AOI.

The primary route does not dilate cloud edges. One-pixel and three-pixel dilations are retained as sensitivity checks and cannot replace the primary route. This preserves the effect of the choice instead of hiding it inside a single mask.

## Derived indices

The masked, scaled bands may produce:

- NDVI: `(B08 - B04) / (B08 + B04)`;
- MNDWI: `(B03 - B11) / (B03 + B11)`;
- NBR: `(B08 - B12) / (B08 + B12)`.

An absolute denominator at or below `1e-6` becomes NoData and is counted. NBR is used as general disturbance context in this project; it does not imply fire.

## Cross-platform comparison

The before image comes from Sentinel-2C and the after image from Sentinel-2B. The raw route remains primary. Spectral-response differences and stable-control bias must be measured before any cross-platform normalization is admitted. Histogram matching over an event AOI and unmeasured harmonization are prohibited. If a stable-control normalization later passes, raw and normalized results remain separate.

## Synthetic ArcGIS validation

ArcGIS Pro 3.7.1 Advanced with Spatial Analyst ran a deterministic 16-by-16 EPSG:32645 fixture. It parsed synthetic processing-baseline, offset, quantification, and NoData metadata; converted five bands to reflectance; applied SCL class-9 and DN-zero exclusions; and calculated NDVI, MNDWI, and NBR. All eight numerical and mask checks passed.

Rerun in a new scratch attempt path and a new receipt path:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" scripts\validate_optical_processing_arcgis.py `
  --output-root scratch\optical-processing-synthetic-arcgis-003 `
  --receipt-output records\surface-receipts\optical-processing-synthetic-arcgis-003.json
```

The tracked receipt is `records/surface-receipts/optical-processing-synthetic-arcgis.json`. Generated synthetic rasters remain under ignored `scratch/` custody.

## Claim boundary

This validation proves only the declared metadata parser and ArcGIS raster math on synthetic inputs. It establishes no real-product metadata, usable AOI coverage, registration, optical baseline, observable change, geomorphic interpretation, attribution, or emergency guidance.

## Official references

- [SentiWiki Sentinel-2 products and Level-2A scaling](https://sentiwiki.copernicus.eu/web/s2-products)
- [Sentinel-2 Product Specification Document 15.1](https://sentinels.copernicus.eu/documents/d/sentinel/sentinel-2-products-specification-document-15_1)
- [CDSE Sentinel-2 Level-2A bands and SCL](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html)
