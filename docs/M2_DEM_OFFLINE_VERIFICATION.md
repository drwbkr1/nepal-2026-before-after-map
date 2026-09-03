# M2 DEM intake and offline verification

## Purpose

This packet fixes how the four proposed Copernicus DEM GLO-30 tiles would enter controlled custody and how their GeoTIFF structure would be checked. It is preparation only. The DEM amendment remains unapproved, so the packet cannot accept the license, request payload bytes, mutate external custody, inspect DEM pixels, or activate radar processing.

The candidate controls are:

- `contracts/m2-dem-intake-candidate.json`
- `contracts/m2-dem-offline-verification-candidate.json`
- `scripts/prepare_m2_dem_controls.py`
- `scripts/verify_m2_dem_geotiff.py`

They are derived from the exact four-tile candidate manifest and the immutable DEM amendment proposal. They are not part of the already published human review bundle and do not change its hash or scope.

## Intake boundary

The intake packet names only `M2-DEM-001` through `M2-DEM-004`, totaling 170,302,058 bytes according to the observed remote metadata. Each tile has one anonymous HTTPS source, one unique `.part` staging path, and one final custody path beneath `dem/copernicus-glo30/`.

The following controls apply:

- fail on any destination collision, unsafe path, symlink, redirect, or remote identity drift;
- require a fresh match for URL, byte length, ETag, last-modified value, access mode, and no-cost route before transfer;
- do not resume unless byte ranges and the same remote identity are freshly verified;
- compute local SHA-256 after transfer because the source does not publish one;
- promote only through atomic no-replace handling;
- keep every partial, failed, corrupt, superseded, and inconclusive attempt.

The standard intake validator accepts the candidate structure when the project root is `C:\Projects\Active`, but that structural result is not authority to run it.

## Offline GeoTIFF checks

An activated future verifier must run in the ArcGIS Pro 3.7.1 Python environment and must make no network request. For each promoted tile it will capture and compare:

- local SHA-256 and exact file size;
- TIFF byte-order signature;
- 3,600 by 3,600 dimensions, one band, and `F32` pixel type;
- EPSG:4326 coordinate system;
- exact cell size and raster extent derived from the reviewed transform;
- ArcGIS-readable NoData properties;
- minimum and maximum raster statistics.

The candidate verifier refuses to run unless a future active verification contract records an approved DEM amendment and explicit DEM-pixel authority. It also refuses to replace an existing receipt.

## What a pass would mean

A structural pass would establish only that the local file identity and basic ArcGIS-readable raster metadata match the reviewed tile. It would not establish valid-pixel coverage inside the AOIs, absence of voids or artifacts, suitability for terrain correction, correct vertical-datum treatment, or scientific fitness.

Valid-pixel fractions, seams, terrain plausibility, and AOI coverage remain later pixel gates. The proposed files store geometric AOI coverage separately so a footprint intersection cannot be mistaken for usable elevation data.

## Current disposition

`DEFER`. The exact intake and verification procedures are ready for deterministic activation, but no DEM approval, license acceptance, transfer, custody mutation, or pixel inspection has occurred.
