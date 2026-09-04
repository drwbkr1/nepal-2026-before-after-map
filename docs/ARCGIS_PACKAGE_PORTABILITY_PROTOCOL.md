# Metadata-only ArcGIS package portability fixture

## Purpose

This control tests one narrow delivery mechanism before the scientific map exists: can the already validated, empty ArcGIS evidence workspace be packaged as a `.ppkx`, extracted into a fresh external directory, reopened, and exported again without depending on the original operational layer paths?

The fixture reduces M6 delivery risk. It is not an M6 deliverable, a clean-machine test, a cross-version test, or scientific evidence.

## Exact source

The source is retained workspace attempt 006, already bound by `records/surface-receipts/arcgis-evidence-workspace.json`. It contains three approved AOIs and ten source-product metadata rows. Observation, exclusion, stable-control, observation-source, interpretation, attribution, and analysis-QA datasets all contain zero rows. Its stable 110-file, 1,171,536-byte inventory is fixed in `config/qa/arcgis-package-portability-contract.json`.

No Sentinel archive, SAFE directory, measurement raster, Copernicus DEM tile, orbit file, derived scientific raster, or mapped-change feature is in scope.

## Execution boundary

The one allowed attempt writes only beneath:

`C:\Projects\Active\nepal-2026-before-after-map-data\derived\arcgis-package-portability\attempt-001`

The runner must stop before creating that directory if the contract, source hashes, source inventory, authority, publication commit, remote main ref, or output collision differs. Network requests, authentication, credential access, source-workspace mutation, and Git storage of the package are prohibited.

ArcGIS `PackageProject` uses external sharing, a writable project package, version 3.7 compatibility, no optional toolboxes, and no geoprocessing history. `ExtractPackage` uses a fresh explicit folder with profile caching disabled.

## Passing runtime result

A structural runtime pass requires:

- unchanged source inventory before and after the operation;
- one nonempty package no larger than 50 MB;
- no raster-data suffix in the extracted stable inventory;
- exactly one extracted APRX with one named map and one named layout;
- all operational layer sources present beneath the extraction root and no broken layer;
- EPSG:32645, nine expected datasets, fourteen domains, eight relationships, three AOIs, ten source-product rows, and zero scientific rows;
- new 160 dpi PNG and PDF exports; and
- an exact decoded RGB pixel digest match between the retained overview and the round-trip PNG.

The runtime result remains pending until the exported PNG is visually inspected. A completed local pass establishes only a same-machine ArcGIS Pro 3.7.1 round trip for this metadata-only fixture. The final scientific project still requires real evidence, a true verified scale bar, source-manifest reconciliation, clean-path or clean-machine testing, and release review.

## Invocation after publication gate

Only after the exact contract and runner are on `origin/main` and that commit has a successful `Validate project controls` run:

```powershell
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" scripts\run_arcgis_package_portability_arcgis.py `
  --checked-at-utc <RFC3339-UTC> `
  --publication-commit <40-character-commit> `
  --publication-run-id <successful-GitHub-Actions-run-id>
```

Any failed attempt is retained. Its path may not be reused, and another attempt requires a separately predeclared output identity.
