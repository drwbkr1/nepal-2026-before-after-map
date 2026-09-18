# M2 DEM vertical-datum alternate method review 001

## Decision

Choose **approve**, **revise**, or **defer** for proposal `dd920e205cb34f812dbbed422909acd9d3357d2f7b53f6843eccf03259e226d7`. Approval must be an attested owner decision bound to the exact review-bundle hash generated with this package.

## Why this review exists

The owner approved an Esri EGM2008 one-minute preconversion route, but the required ArcGIS Coordinate Systems Data component is absent and Purdue reports it cannot supply the component. The historical approval remains valid evidence; it is not silently rewritten. A replacement source and implementation require a new owner decision.

## Recommended replacement

Use exact `us_nga_egm08_25.tif` from the official PROJ CDN. The PROJ-data record identifies it as an NGA-derived, public-domain, worldwide EGM2008 2.5-minute grid. The catalog binds 80,585,622 bytes and SHA-256 `4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a`.

The existing ArcGIS Pro Python environment already supplies GDAL 3.12.2e and PROJ 9.8.1, understands EPSG:3855, EPSG:4979, and EPSG:9518, and has PROJ network access disabled. No software installation, login, license click-through, or UAC action is required.

## Material scientific change

The source vertical reference, height equation `h = H + N`, no-overwrite custody, ellipsoidal output, and later `NONE` rule stay unchanged. The grid spacing changes from the unavailable Esri one-minute grid to a 2.5-minute grid. GeographicLib reports a conservative 0.135 m maximum and 0.0032 m RMS bilinear interpolation error for EGM2008 2.5-minute data relative to the EGM2008 model. The route must be described as a 2.5-minute substitution, not as identical to the Esri method.

## What approval would authorize

Approval would authorize bounded implementation and synthetic tests, public CI, a final no-payload preflight, one exact no-retry grid request and verification, then one fixed-order append-only conversion attempt for each of the four verified DEM tiles if all prior gates pass. All processing stays local and uses only the promoted grid bytes.

## What approval would not authorize

No retry or alternate source, no GeographicLib partial reuse, no software install, no provider account or terms action, no source DEM overwrite, no orbit application, no radar measurement-pixel access, no baseline or change analysis, and no scientific or emergency publication.
