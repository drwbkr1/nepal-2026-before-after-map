# ArcGIS delivery plan

## Target environment

- ArcGIS Pro 3.7 or later
- WGS 1984 UTM Zone 45N (EPSG:32645)
- Spatial Analyst and Image Analyst where licensed
- Project-relative paths wherever ArcGIS supports them

## Planned project structure

The working ArcGIS project will use a dedicated local workspace outside Git for heavy data:

```text
workspace/
  Nepal_2026_Before_After.aprx
  Nepal_2026.gdb/
  imagery/
    source/
    analysis_ready/
    derived/
  layers/
  layouts/
  exports/
  logs/
```

Only small, redistribution-safe layer definitions, scripts, metadata, and manifest records may later be copied into this repository.

## Current verified evidence-workspace scaffold

ArcGIS Pro 3.7.1 Advanced has created and reopened a metadata-only scaffold in ignored scratch custody. The validated surface contains:

- an EPSG:32645 File Geodatabase with nine datasets, fourteen coded-value domains, and eight relationship classes;
- three approved search and review AOIs and ten exact source-product metadata rows;
- distinct empty structures for direct observations, interpretations, attribution assessments, exclusions, stable controls, source links, and QA;
- an editable APRX plus PDF and PNG exports from one overview layout.

The repository retains the declarative schema, ArcGIS builder, independent validator, public PNG preview, and validation receipt. It does not retain the File Geodatabase, APRX, or PDF. See [ARCGIS_EVIDENCE_MODEL.md](ARCGIS_EVIDENCE_MODEL.md).

This scaffold establishes editable GIS structure and export behavior only. No product pixels have been acquired or admitted, and no change feature or event attribution has been mapped.

## Planned maps

1. **Regional overview** — source area, main corridor, settlements, roads, drainage, and event context.
2. **Source-area comparison** — synchronized before/after optical panels plus radar evidence.
3. **Upper-corridor comparison** — channel and valley-floor change.
4. **Evidence map** — reviewed change features, confidence, sensor agreement, and exclusion zones.
5. **Limitations map** — cloud, snow, terrain shadow, radar layover/shadow, missing coverage, and unresolved areas.

## Layer conventions

- Prefix source layers by sensor and date.
- Include acquisition date and processing state in names.
- Keep source, analysis-ready, derived, and interpretation layers in separate groups.
- Store change features in a geodatabase feature class with domains for observation class, confidence, review status, and attribution status.
- Preserve nodata and exclusion masks as visible analytical layers.
- Use scale-dependent symbology and label rules rather than manual layout-only edits.

## Core feature attributes

| Field | Meaning |
|---|---|
| FEATURE_ID | Stable project identifier |
| OBS_CLASS | Satellite-observed change class |
| INTERP | Analyst interpretation |
| ATTRIB | Attribution status |
| SENSOR | Supporting sensor or sensor set |
| BEFORE_DT | Pre-event acquisition |
| AFTER_DT | Post-event acquisition |
| METHOD | Derivation or digitization method |
| CONFIDENCE | High, medium, low, or inconclusive |
| LIMITATION | Principal qualification |
| REVIEW | Review state |
| SOURCE_REF | Manifest or evidence reference |

## Deliverables

| Artifact | Purpose | Git policy |
|---|---|---|
| `.aprx` | Editable ArcGIS Pro project | Track only after size/path review |
| `.gdb` | Analysis and feature database | External/package custody |
| `.lyrx` | Layer definitions | May track if small and rights-safe |
| GeoTIFF | Interoperable rasters | External/package custody |
| GeoPackage | Interoperable vectors/tables | External/package custody |
| `.ppkx` | Portable ArcGIS package | Release storage after review |
| PDF/PNG | Public map layouts | Release storage after claim review |
| metadata + manifest | Provenance and reproduction | Track in Git |

## Export and package verification

Before delivery:

- open the project in a clean path with no analyst-specific drive dependency;
- validate data sources and coordinate systems;
- confirm symbology, labels, legends, scale bars, north arrows, credits, and limitations;
- run layout exports at intended page size and resolution;
- inspect output visually for clipped text and misleading layer order;
- unpack any project package in a separate directory and repeat the open/export test;
- compare packaged source manifests and hashes with the approved records.

The scaffold overview intentionally uses a verified numeric map scale because two retained attempts showed defective native scale-bar labels. Every later scientific layout still requires a true scale bar that passes visual inspection at its final extent.
