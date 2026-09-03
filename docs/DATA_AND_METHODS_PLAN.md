# Data and methods plan

## Analysis frame

All measured outputs will use **EPSG:32645, WGS 1984 UTM Zone 45N**. Source data will retain native metadata, and every reprojection or resampling step will be recorded.

### Approved M1 search and review areas

The owner approved these exact planning bounds for M1 source discovery, review, and ArcGIS organization. They are not mapped change polygons or proof of event geometry:

| AOI | Longitude | Latitude | Purpose |
|---|---:|---:|---|
| Overview | 84.70–85.65 E | 27.75–28.45 N | Regional source-to-downstream context |
| Source area | 85.46–85.58 E | 28.23–28.34 N | Debris-avalanche source and immediate path |
| Upper corridor | 85.28–85.45 E | 28.10–28.38 N | Bhote Koshi–Trishuli change corridor |

The reviewed EPSG:4326 geometry is retained in `config/aoi/draft-study-areas.geojson` with its original SHA-256. The promoted interchange artifact is `config/aoi/approved-study-areas.geojson`, and the ArcGIS FeatureSet derivative is `config/aoi/approved-study-areas-epsg32645.json`. ArcGIS Pro 3.7.1 imported the projected artifact as three nonempty polygons in EPSG:32645.

Independent event-location evidence and later pixel coverage still must be reconciled before interpreting any satellite-observed change.

## Candidate Sentinel-2 Level-2A products

| Role | Tile | Product ID | Catalog cloud |
|---|---|---|---:|
| Before | 45RUM | `S2C_MSIL2A_20260812T045701_N0512_R119_T45RUM_20260812T100317` | 18.75% |
| After | 45RUM | `S2B_MSIL2A_20260827T045659_N0512_R119_T45RUM_20260827T084453` | 78.47% |
| Before | 45RUL | `S2C_MSIL2A_20260812T045701_N0512_R119_T45RUL_20260812T100317` | 27.95% |
| After | 45RUL | `S2B_MSIL2A_20260827T045659_N0512_R119_T45RUL_20260827T084453` | 54.29% |

Catalog cloud percentage applies to an entire tile. It does not establish usable coverage over an AOI. Pixel masks and visual inspection are mandatory.

The owner-approved M1 manifest accepts the RUM pair for controlled acquisition planning and defers the two RUL tiles as regional context. M2 acquisition remains at its separate owner activation gate.

### Optical processing candidates

1. Verify product identity, footprint, rights, checksum, and required bands.
2. Inspect Scene Classification Layer and quality masks.
3. Build true color and SWIR false color composites.
4. Mask cloud, cirrus, cloud shadow, snow/ice, saturation, and invalid pixels.
5. Align dates in EPSG:32645 using an explicitly chosen snap raster and cell size.
6. Test interpretable deltas such as NDVI, NDWI/MNDWI, and NBR only where their physical meaning and valid pixels support use.
7. Preserve no-conclusion areas rather than interpolating through cloud or terrain shadow.

## Candidate Sentinel-1 GRD products

### Ascending, relative path 85

- Before: `S1D_IW_GRDH_1SDV_20260816T122116_20260816T122141_004151_007980_B057`
- Before: `S1D_IW_GRDH_1SDV_20260816T122141_20260816T122206_004151_007980_C3AB`
- After: `S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523`
- After: `S1D_IW_GRDH_1SDV_20260828T122141_20260828T122206_004326_007FA4_01B4`

### Descending, relative path 121

- Before: `S1D_IW_GRDH_1SDV_20260819T001036_20260819T001101_004187_007ABD_DC16`
- After: `S1D_IW_GRDH_1SDV_20260831T001037_20260831T001102_004362_0080EC_2C5B`

The exact 31 August descending product name returned a catalog record during the planning pass. Full archive availability and complete pixel coverage still must be verified before use.

### Radar processing candidates

1. Confirm orbit direction, relative orbit, polarization, slice continuity, timing, and footprint.
2. Apply orbit information, border/thermal noise handling where required, radiometric calibration, and terrain correction.
3. Use a documented DEM and record its version and vertical/horizontal reference.
4. Create VV and VH calibrated backscatter layers and log-ratio or normalized-change candidates.
5. Keep ascending and descending comparisons separate until geometry-specific QA is complete.
6. map layover, shadow, edge effects, water variability, and speckle limitations.

## Supporting data

Potential contextual layers include a DEM, hydrography, roads, settlements, and administrative boundaries. Each source must pass the same identity, rights, coverage, and custody review. Context layers must not be used as unrecorded ground truth.

## Optional high-resolution path

Planet or Vantor event imagery may improve visual interpretation, but candidate public disaster imagery may carry **CC BY-NC 4.0 or other noncommercial restrictions**. It is excluded from the public core until:

- the exact asset and license are recorded;
- the intended use is reviewed;
- redistribution and derivative constraints are understood;
- credentials or account terms are handled through an explicit human gate.

The preferred core remains reproducible Copernicus data.

## Required source-manifest fields

`source_id`, provider, collection, exact product ID, acquisition start/end, processing level, orbit/tile, footprint, query and query time, catalog URL/API, access method, rights/license, local custody path, byte size, checksum, coverage status, pixel-inspection status, mask status, disposition, rejection reason, and reviewer.

## Interpretation scheme

Every final feature will separate:

- **Observation:** a measured or visually identified change in valid pixels;
- **Interpretation:** a reasoned class such as fresh debris, channel expansion, inundation, or vegetation loss;
- **Attribution:** a claim that the change resulted from this event.

Attribution is withheld unless timing, spatial continuity, sensor agreement, and independent event evidence support it.
