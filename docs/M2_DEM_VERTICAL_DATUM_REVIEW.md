# M2 DEM vertical-datum method review

## Decision in one sentence

Approve, revise, or defer the exact proposal to convert the four verified Copernicus DEM tiles from EGM2008 orthometric height to WGS 84 ellipsoidal height with ArcGIS's EGM2008 one-minute grid, and then use `NONE` in the Sentinel-1 terrain tools only for those verified derivatives.

**Proposal SHA-256:** `bdaa7f9e10840d41c9bc47d65b33bbee3f71e82fe7862069ff1129785047f065`

## Why a method decision is required

The four DEM tiles have passed exact-byte, ArcGIS structural, and valid-AOI-coverage checks. Their elevation reference still matters to radar terrain flattening and geometric terrain correction:

- Copernicus documents its DEM as orthometric height tied to EGM2008.
- ArcGIS documents the SAR `GEOID` switch as an EGM96 conversion.
- ArcGIS says `NONE` is appropriate only when the input DEM is already ellipsoidal.

Using `GEOID` would therefore introduce a known model mismatch. Using the source tiles directly with `NONE` would mislabel orthometric heights as ellipsoidal. Neither should become the production route silently.

## Proposed production route

The proposal selects the exact EGM2008 route:

1. The owner separately obtains and installs the ArcGIS Coordinate Systems Data component matching ArcGIS Pro 3.7.x, with the `world1x1_vert` feature.
2. The project verifies `Dataset_egm2008-1.grd` and the ArcGIS transformation `WGS_1984_To_WGS_1984_EGM2008_1x1_Height` (WKID 110018) over the approved AOI extent.
3. A versioned, no-overwrite ArcGIS process converts copies of the four source rasters from EPSG:3855 EGM2008 orthometric height to WGS 84 ellipsoidal height, preserving the originals.
4. The output is checked against the height relation `h = H + N`, rechecked for finite AOI coverage, and reviewed for void-fill, seams, artifacts, and terrain plausibility.
5. Sentinel-1 terrain tools use `NONE` only with those verified ellipsoidal derivatives.

The built-in EGM96 `GEOID` route remains a labeled sensitivity route. It cannot replace the primary EGM2008 route.

## Current machine evidence

ArcGIS Pro 3.7.1 Advanced is installed. A read-only inspection found the built-in EGM96 grid `WGS84.img`, but neither EGM2008 grid file and no usable EGM2008 transformation over the AOI. The exact route cannot run until the owner installs the matching optional component.

The inspection made no network request, read no credentials or DEM pixels, installed no software, and changed no coordinate-system data.

## What approval would authorize

After exact response lock and reconciliation, approval would authorize the project to record this as the production method and, **only after the owner separately installs the required component**, prepare and run a fail-closed conversion of the four verified tiles into the declared external non-Git derived-data root. It would also authorize setting the SAR `geoid` parameter to `NONE` only when those verified ellipsoidal derivatives are used.

Approval would not authorize Codex to sign in to My Esri, accept license terms, download or install software, approve UAC, obtain a different geoid grid, alter source tiles, download orbit vectors, bypass Sentinel gates, run premature radar processing, or publish a scientific claim.

## Stop conditions

Stop if the installed version, grid identity, transformation name or direction, source hash, AOI coverage, output path, or license state differs; if an owner-controlled sign-in, terms, or privileged prompt appears; or if the conversion writes source data, collides with an existing attempt, creates unexplained sidecars, or produces implausible corrections.

## Official basis

- [ArcGIS Apply Radiometric Terrain Flattening](https://pro.arcgis.com/en/pro-app/latest/tool-reference/image-analyst/apply-radiometric-terrain-flattening.htm)
- [Copernicus DEM documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html)
- [EPSG:3855 EGM2008 height](https://epsg.org/crs_3855/EGM2008-height.html)
- [ArcGIS Coordinate Systems Data](https://pro.arcgis.com/en/pro-app/latest/help/mapping/properties/arcgis-coordinate-systems-data.htm)
- [ArcGIS Pro installation component names](https://pro.arcgis.com/en/pro-app/latest/get-started/arcgis-pro-installation-administration.htm)
- [ArcGIS Project Raster](https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/project-raster.htm)
- [ArcGIS geographic and vertical transformation tables](https://pro.arcgis.com/en/pro-app/latest/help/mapping/properties/pdf/geographic_transformations.pdf)
- [NGA EGM2008 data and applications](https://earth-info.nga.mil/)

## How to decide

- **Approve** if the exact EGM2008 preconversion route and its owner-install prerequisite are acceptable.
- **Revise** if the route, component, verification, or allowed actions should change.
- **Defer** if no vertical-datum method should be activated yet.

The blank response is generated from the review contract. Do not edit the review bundle, proposal, evidence, or contract after the bundle hash is issued.
