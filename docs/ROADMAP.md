# Roadmap

The roadmap is milestone-based. A later milestone cannot repair missing source or custody evidence from an earlier one.

## M0 — Public project bootstrap

**Outcome:** A public GitHub repository with the charter, controls, roadmap, candidate products, validation script, and explicit data boundaries.

**Exit evidence:**

- required records pass local validation;
- public repository and default branch are independently verified;
- no raw imagery, credentials, or large GIS artifacts are tracked;
- license choice remains explicit rather than implied.

## M1 — Event geometry and source manifest

**Outcome:** Reviewed areas of interest and a locked candidate-source manifest.

**Status:** Complete. The owner approved the exact AOI and source-manifest review bundles; eight sources are accepted for controlled acquisition planning and two are retained as deferred context.

**Work:**

- reconcile reported event location and date against authoritative or independent sources;
- create overview, source-area, and upper-corridor AOIs;
- query candidate Sentinel products using exact geometry and time windows;
- inspect footprints, metadata, quicklooks, access conditions, and rights;
- record accepted, rejected, and deferred products;
- acquire full data only after the custody decision is approved.

**Exit gate:** Human approval of the exact AOIs and acquisition manifest.

## M2 — Controlled acquisition and baseline

**Outcome:** Verified local custody of approved data and a reproducible pre-event baseline.

**Status:** Proposed, not active. The exact acquisition plan is prepared for owner review; no authentication, custody-root creation, download, extraction, or baseline processing is authorized.

**Work:**

- download approved products into non-Git custody;
- compute checksums and record provider receipts;
- validate archive integrity and band availability;
- build pre-event optical and radar reference layers;
- register data to EPSG:32645 and quantify alignment.

**Exit gate:** Source hashes, pixel inspection, coverage, rights, and baseline QA pass.

## M3 — Post-event preprocessing

**Outcome:** Analysis-ready post-event optical and radar layers with masks.

**Work:**

- apply cloud, cirrus, shadow, snow, and invalid-pixel masks;
- calibrate, terrain-correct, filter, and normalize radar data;
- document resampling, resolution, extent, and nodata behavior;
- create exclusion layers for unreliable terrain and sensor geometry.

**Exit gate:** Cross-date registration and mask review pass at each AOI.

## M4 — Change analysis

**Outcome:** Candidate change layers from independent optical and radar routes.

**Candidate methods:**

- true- and false-color visual comparison;
- NDVI, NDWI/MNDWI, NBR or related index deltas where physically meaningful;
- Sentinel-1 VV/VH log-ratio or normalized amplitude change;
- object or feature digitization with evidence attributes;
- agreement and disagreement layers across sensors.

**Exit gate:** Thresholds and interpretations are fixed before final cartography; failures remain recorded.

## M5 — Review and interpretation

**Outcome:** Reviewed change features with confidence and limitation classifications.

**Required fields:** feature ID, observation class, geometry, sensor/date sources, method, confidence, review status, limitations, and attribution status.

**Exit gate:** Human review of the evidence bundle and wording of scientific claims.

## M6 — ArcGIS delivery

**Outcome:** An ArcGIS Pro package that opens without undocumented local dependencies.

**Deliverables:** `.aprx`, `.gdb`, `.lyrx`, GeoTIFF, PDF/PNG layouts, metadata, and optionally `.ppkx` after size and license review.

**Exit gate:** Clean-machine/package validation and export test.

## M7 — Public release and maintenance

**Outcome:** Versioned methods, small reproducibility assets, qualified map exports, and a release record.

**Exit gate:** Source rights, privacy, scientific claims, public surfaces, GitHub release, and downloadable artifacts are all verified independently.

## Long-term maintenance

Future versions may add later imagery, field reports, or higher-resolution observations. They must be appended as new evidence with dates and provenance. They must not silently replace the original event-window record.
