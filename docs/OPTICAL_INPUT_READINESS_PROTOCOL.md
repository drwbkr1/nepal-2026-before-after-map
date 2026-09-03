# ArcGIS Sentinel-2 materialized-input readiness protocol

## Purpose

This gate sits between completed SAFE materialization and pixel processing. It proves that the exact before/after Sentinel-2 inputs can be identified, reverified, and opened by the installed ArcGIS runtime with the expected metadata and raster headers. It deliberately stops before reading or interpreting pixel values.

The exact route remains:

| Role | Source | Product |
|---|---|---|
| Before | `M1-SRC-010` | `S2C_MSIL2A_20260812T045701_N0512_R119_T45RUM_20260812T100317.SAFE` |
| After | `M1-SRC-008` | `S2B_MSIL2A_20260827T045659_N0512_R119_T45RUM_20260827T084453.SAFE` |

Both must report processing baseline 05.12, tile 45RUM, relative orbit 119, and EPSG:32645. The machine-readable contract is `config/qa/optical-input-readiness-contract.json`.

## Entry conditions

The production runner requires two explicit repository-relative materialization receipts. Each must:

- be `pass_materialization_only` for the correct exact source and product;
- bind the current materialization contract;
- point to a complete external manifest and SAFE root within the exact non-Git data root;
- have a matching external `completed.json` marker;
- preserve the selected member sizes and SHA-256 values when re-read.

The runner validates its bound controls and active M2 `data_processing` authority before importing ArcPy. Missing receipts currently stop the command before external custody access.

## Exact required inventory

Each SAFE manifest must contain exactly one member for each of ten roles:

- product and tile metadata: `MTD_MSIL2A.xml` and `GRANULE/*/MTD_TL.xml`;
- 10 m B02, B03, B04, and B08 JPEG2000 rasters;
- 20 m B11, B12, and SCL JPEG2000 rasters;
- the classification quality mask `GRANULE/*/QI_DATA/MSK_CLASSI_B00.jp2`.

Missing, duplicate, empty, unsafe, or non-SHA-256-bound selected members block the route.

## Metadata and ArcGIS header checks

The product metadata must contain one BOA quantification value, one offset for every used band, DN zero as NoData, and internal processing baseline 05.12. The baseline parsed from the exact product name must agree.

ArcGIS Pro must open every selected JP2 in EPSG:32645. B02, B03, B04, and B08 must be single-band unsigned reflectance DNs on a 10 m grid; B11, B12, and SCL must be single-band on a 20 m grid. Every raster's dimensions multiplied by its cell size must reproduce its reported extent. The quantitative band and SCL extents must agree within 0.001 m inside each product, and matching roles must have the same dimensions, cell sizes, pixel types, and extents across the before/after pair.

For PB 05.12, `MSK_CLASSI_B00.jp2` must be a three-band 60 m Boolean mask: band 1 opaque cloud, band 2 cirrus cloud, and band 3 snow/ice. It must be readable, projected to EPSG:32645, nonempty, dimensionally consistent with its extent, and aligned across the exact pair. It remains separate from the 20 m SCL layer and is not resampled at this header gate.

## Decision semantics

`pass_header_readability_only` permits the later pixel-coverage, mask, and registration QA. Any missing identity, metadata, member, raster, CRS, cell-size, or grid condition produces `block`. A pass does not establish:

- pixel validity or AOI coverage;
- cloud, shadow, snow, saturation, or SCL usability;
- registration residuals or stable-control behavior;
- an optical baseline or observable change;
- interpretation, attribution, or scientific admission.

## Synthetic ArcGIS validation

ArcGIS Pro 3.7.1 Advanced opened sixteen deterministic JPEG2000 fixtures generated through its bundled GDAL 3.12.2 `JP2OpenJPEG` driver. The corrected fixture contains matching 10 m and 20 m single-band grids plus a three-band 60 m `MSK_CLASSI`, all in EPSG:32645, with baseline 05.12 metadata, one quantification value, and all six required band offsets. The aligned pair passes header readiness and a deliberate 10 m shift of the complete after grid produces sixteen cross-pair extent errors and `block`.

Two earlier attempts to create JP2 fixtures directly with ArcGIS `CopyRaster` failed with `No raster store is configurated.` They remain recorded. Five prepublication passing receipts were superseded in sequence: the first omitted detailed headers, the second preceded runner hardening for retained metadata and header failures, the third preceded the dimension-to-extent consistency rule, the fourth followed a failed portable fixture expectation in the same chained invocation, and the fifth preceded explicit attempted-versus-complete header-open activity fields. The attempt published in commit `df3e93a` is retained as superseded because it modeled `MSK_CLASSI_B00.jp2` as one-band 20 m instead of three-band 60 m. The first corrected run is retained as failed because ArcGIS exposes multiband width, cell size, and pixel type on its child band descriptions rather than on the dataset-level object. No attempt used real source data.

Rerun only to new scratch and receipt paths:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" `
  scripts\validate_optical_input_readiness_arcgis.py `
  --output-root scratch\optical-input-readiness-arcgis-009 `
  --receipt-output records\surface-receipts\optical-input-readiness-synthetic-arcgis-009.json `
  --verified-at-utc <RFC-3339-UTC>
```

After the two real SAFE materializations pass, invoke the production runner with their exact receipt paths and a new output receipt:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" `
  scripts\inspect_optical_inputs_arcgis.py `
  --before-materialization-receipt records/acquisition/materialization/<before-receipt>.json `
  --after-materialization-receipt records/acquisition/materialization/<after-receipt>.json `
  --checked-at-utc <RFC-3339-UTC> `
  --receipt-output records/readiness/optical-input/<new-receipt>.json
```

The production command has not been run because neither approved optical archive is in custody.

## Official ArcGIS reference

[Esri documents JPEG2000 (`.jp2`) as a supported ArcGIS raster dataset format](https://pro.arcgis.com/en/pro-app/latest/help/data/imagery/supported-raster-dataset-file-formats.htm). [Copernicus SentiWiki documents the multiband mask encoding](https://sentiwiki.copernicus.eu/web/s2-processing), and [Sentinel-2 PSD 15.1 lists the three `MSK_CLASSI` components](https://sentinels.copernicus.eu/documents/d/sentinel/sentinel-2-products-specification-document-15_1). The project nevertheless validates the installed runtime directly because format support and specification metadata do not prove the identity, CRS, grid, or readability of these event products.
