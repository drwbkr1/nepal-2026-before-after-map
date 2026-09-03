# Nepal 2026 Before/After Map

An evidence-first geospatial project to produce a reproducible, ArcGIS-ready before-and-after map of the 26 August 2026 debris avalanche and flash flood in Nepal's Langtang–Bhote Koshi–Trishuli corridor.

## Active long-term goal

Build and maintain a defensible geospatial evidence package that shows where the event altered the landscape, distinguishes direct satellite observations from interpretation, and can be opened, reviewed, updated, and exported in ArcGIS Pro without relying on undocumented analyst state.

The project should ultimately deliver:

- a projected ArcGIS Pro project in **WGS 1984 UTM Zone 45N (EPSG:32645)**;
- registered before/after optical and radar imagery with source manifests and checksums;
- mapped change features with confidence, method, date, and source attributes;
- overview, source-area, and corridor map layouts;
- portable ArcGIS layer and project packages plus GeoTIFF, GeoPackage/File Geodatabase, PDF, and PNG exports;
- a public, reproducible method record that preserves limitations and failed or inconclusive analytical routes.

This goal is **active as of 1 September 2026**. M1 is complete: the search and review AOIs are owner-approved, projected to EPSG:32645, and validated through ArcGIS Pro, and the exact source manifest is approved with eight sources accepted for controlled acquisition planning and two preserved as deferred context. M2 is proposed but not active. Full imagery acquisition, authenticated-session use, terms acceptance, restricted high-resolution imagery, and publication of scientific conclusions remain separately gated.

## Why this is useful

Emergency maps often mix source discovery, visual interpretation, and final cartography in ways that are hard to audit later. This project separates those stages. A reviewer should be able to trace a mapped change back to an exact satellite product, processing step, observation date, and confidence statement.

## Initial study design

| Component | Initial choice |
|---|---|
| Event | 26 August 2026 Nepal debris avalanche and flash flood |
| Study corridor | Langtang source area through the Bhote Koshi–Trishuli corridor |
| Master CRS | EPSG:32645, WGS 1984 UTM Zone 45N |
| Core optical | Sentinel-2 Level-2A, 12 Aug and 27 Aug 2026 |
| Core radar | Sentinel-1 GRD, ascending and descending before/after pairs |
| GIS target | ArcGIS Pro 3.7+ |
| Public core | Copernicus products and reproducible metadata |
| Optional high resolution | Separate, license-gated, noncommercial path only |

The product identifiers currently under consideration are recorded in [docs/DATA_AND_METHODS_PLAN.md](docs/DATA_AND_METHODS_PLAN.md). They are candidates until coverage, rights, pixels, masks, and event relevance are verified.

## Repository boundaries

This public repository stores project controls, methods, small scripts, source manifests, and lightweight review evidence. It does **not** store raw satellite archives, extracted SAFE products, large rasters, geodatabases, ArcGIS project packages, credentials, access tokens, or licensed imagery. Those belong in controlled local or external data custody.

Public visibility does not grant reuse rights to third-party data. No repository license has been selected yet.

## Current checkpoint

Milestones 0 and 1 are complete. The exact AOI and source-manifest decisions are locked and reconciled. The current gate is owner review of a proposed M2 plan covering eight exact Sentinel downloads into non-Git custody. The proposal does not authorize authentication, custody-root creation, downloads, or terms acceptance, and no usable pixels or scientific change have been established.

A deterministic, network-free M2 intake packet is prepared for the eight exact products. It fixes sibling staging and custody paths, fail-on-collision and no-replace promotion rules, secret references, and attempt retention without changing the pending review bundle or creating acquisition authority.

A metadata-only ArcGIS evidence workspace has also been built and validated in ArcGIS Pro 3.7.1 Advanced. Its EPSG:32645 File Geodatabase contains nine datasets, fourteen coded-value domains, eight relationship classes, three approved AOIs, and ten source-product metadata rows. The observation, interpretation, attribution, exclusion, stable-control, and QA structures are empty by design. The retained APRX, geodatabase, and PDF remain outside Git; the repository contains the schema, builder, validator, receipt, and a reviewed PNG preview.

See:

- [Project charter](docs/PROJECT_CHARTER.md)
- [Roadmap](docs/ROADMAP.md)
- [Data and methods plan](docs/DATA_AND_METHODS_PLAN.md)
- [Source register](docs/SOURCES.md)
- [M1 AOI review bundle](docs/M1_AOI_REVIEW.md)
- [M1 source-manifest review](docs/M1_SOURCE_MANIFEST_REVIEW.md)
- [M2 controlled-acquisition review](docs/M2_CONTROLLED_ACQUISITION_REVIEW.md)
- [M2 controlled-intake execution runbook](docs/M2_EXECUTION_RUNBOOK.md)
- [ArcGIS delivery plan](docs/ARCGIS_DELIVERY_PLAN.md)
- [ArcGIS evidence model](docs/ARCGIS_EVIDENCE_MODEL.md)
- [Validation plan](docs/VALIDATION.md)
- [Current status](docs/STATUS.md)
- [Decision log](docs/DECISIONS.md)

## Validate the repository

From the repository root:

```powershell
python scripts/check_project.py
```

The check verifies required control files, parses the JSON records, validates the portable ArcGIS schema and receipt bindings, and rejects tracked secrets and large geospatial artifacts.
