# M2 DEM PROJ25 metadata recovery-001 review

## Decision requested

Choose **approve**, **revise**, or **defer** for proposal SHA-256 `729d36da013a9bf987486e18f7c6bac75865eda5b75dc963e8fd31ff4ddb13cd`.

The one authorized request is terminal. It downloaded the exact approved 80,585,622 bytes with SHA-256 `4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a`, but the first implementation rejected the official file because it looked for generic `source_crs` and `target_crs` metadata keys that the file does not contain.

The exact official file instead carries:

- `TIFFTAG_IMAGEDESCRIPTION`: `WGS 84 (EPSG:4979) to EGM2008 height (EPSG:3855). Converted from egm08_25.gtx (last modified at 2018/10/08)`
- `target_crs_epsg_code`: `3855`
- `TYPE`: `VERTICAL_OFFSET_GEOGRAPHIC_TO_VERTICAL`
- `area_of_use`: `World`

All byte-identity, raster-structure, extent, type, area, and public-domain tag checks passed. No destination was promoted and no DEM pixel or conversion was attempted.

## Exact proposed correction

Replace only the failed literal-key requirement with an exact check of the embedded description and `target_crs_epsg_code`. Keep the approved EPSG:4979-to-EPSG:3855 relation and every other predicate unchanged.

If approved, the project may implement and publicly validate that correction, then perform one offline verification of the preserved bytes with no network request. Only on pass may it promote those exact bytes without replacement and continue the unchanged sign check and fixed-order, one-attempt conversion of the four approved DEM tiles.

## Boundaries

Approval would authorize no network request, reacquisition, resume, automatic retry, alternate source, alternate grid, CRS or threshold change, software installation, account or terms action, PROJ network fetch, source DEM overwrite, orbit application, radar-pixel processing, baseline, change analysis, attribution, derived-pixel publication, or scientific claim.

This is a post-observation correction. It is expected to address the observed metadata representation mismatch and is not blind or independent validation.

## Required attestation

An approval must cite the exact review-bundle and proposal SHA-256 values and state that the decision is completed and attested.
