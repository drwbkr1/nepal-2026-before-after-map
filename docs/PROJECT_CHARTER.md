# Project charter

## Project

- **Name:** Nepal 2026 Before/After Map
- **Event:** 26 August 2026 Nepal debris avalanche and flash flood
- **Geographic focus:** Langtang source area and the Bhote Koshi–Trishuli corridor
- **Primary working environment:** ArcGIS Pro 3.7 or later
- **Master coordinate reference system:** WGS 1984 UTM Zone 45N, EPSG:32645

## Purpose

Produce a reviewable spatial account of landscape change associated with the event. The map should help a reader understand the source area, the downstream change corridor, and the strength and limits of the satellite evidence. It is a research and communication artifact, not an operational emergency product.

## Proposed long-term goal

Build and maintain a reproducible geospatial evidence package that:

1. identifies credible before/after satellite observations of the event area;
2. measures and maps observable surface change at useful scales;
3. distinguishes sensor observations from analyst interpretation and causal attribution;
4. packages the results for inspection, editing, and export in ArcGIS Pro;
5. preserves source identity, processing history, uncertainty, review decisions, and rejected approaches; and
6. supports future updates without rewriting the history of the original event analysis.

## Intended users

- GIS analysts who need an editable ArcGIS project;
- remote-sensing reviewers who need traceable products and methods;
- researchers and educators evaluating rapid landscape change;
- public audiences viewing clearly qualified map exports.

## Core questions

- Where is the likely source area and what surface change is visible there?
- Which parts of the Bhote Koshi–Trishuli corridor show credible post-event change?
- How consistent are optical and radar observations?
- Where do cloud, snow, terrain, shadow, layover, resolution, or registration prevent a conclusion?
- What can be stated as observation, what remains interpretation, and what evidence would be needed for attribution?

## In scope

- event and study-area geometry;
- Sentinel-2 Level-2A optical comparison;
- Sentinel-1 GRD amplitude-change comparison from both look directions where useful;
- terrain, hydrography, settlements, roads, and administrative context from appropriately licensed sources;
- visual and quantitative change indicators;
- feature-level confidence and review fields;
- ArcGIS Pro maps, layers, layouts, and portable exports;
- source manifests, checksums, processing logs, QA, and limitations.

## Out of scope for the first project

- real-time warning, rescue routing, or safety decisions;
- automated landslide causation;
- legal boundary or property determinations;
- population loss estimates without authoritative exposure data;
- redistribution of data whose license does not permit it;
- treating a news report, catalog footprint, or attractive image as pixel-level validation;
- silently replacing poor observations with better-looking dates.

## Success criteria

The project succeeds when an independent ArcGIS Pro user can open the delivered package, locate every source and derived layer, reproduce the documented core comparisons, inspect the masks and uncertainty, and export the principal layouts without undocumented fixes.

Scientific success requires more than a polished map. Each published feature must have an evidence chain and a stated confidence; unavailable or ambiguous areas must remain visible as such.

## Operating principles

1. **Baseline before interpretation.** Lock study geometry and source candidates before analysis.
2. **Exact identity.** Record product IDs, acquisition times, provider, rights, hashes, and dispositions.
3. **Sensor complementarity.** Use optical imagery for interpretable surface appearance and radar for cloud-tolerant change evidence, while respecting each sensor's artifacts.
4. **Projected analysis.** Perform measurements in EPSG:32645; retain original source CRS and resampling history.
5. **No hidden rescue.** Preserve failed and inconclusive routes.
6. **Small public repository.** Store code and evidence records in Git; store heavy or restricted data elsewhere.
7. **Human review at consequential gates.** Goal activation, source rights, licensed imagery, and scientific publication require explicit decisions.

## Constraints and risks

- The immediate post-event Sentinel-2 scene has substantial cloud, so usable coverage may differ by tile and sub-area.
- Mountain topography creates optical shadow and radar layover/shadow.
- Sentinel-1 acquisitions from different geometries are not interchangeable.
- A one-day post-event image can include ongoing weather and hydrologic effects.
- Product availability can change; custody records and checksums are needed.
- Optional high-resolution imagery may be restricted to noncommercial use.

## Governance state

This charter proposes the project. It does not activate the long-term goal or authorize data acquisition. Milestone contracts and [records/project-control-profile.json](../records/project-control-profile.json) define the current boundary.
