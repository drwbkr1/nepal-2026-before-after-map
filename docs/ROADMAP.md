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

**Status:** Active at `M2-AUTHENTICATION-REFERENCE`. The exact eight-product acquisition plan is owner-approved, the live source and storage preflight passed, and the empty external custody structure is initialized. No product bytes have been transferred because the secret-safe existing CDSE authentication reference is still pending.

**Prepared verification:** Deterministic offline controls define exact container identity, checksum, ZIP safety, SAFE structure, required radar/optical members, and the later pixel-readiness gates. The active wrapper refuses archive access until a promoted intake identity and successful-transfer receipt exist. The real-data readiness decision remains `defer` because custody contains no product bytes.

**Prepared pixel QA:** The EPSG:32645 coverage, mask, grid-alignment, and registration thresholds are fixed before product access. The portable core and ArcGIS Pro 3.7.1 Spatial Analyst adapter pass synthetic validation only; real-product readiness remains `defer`.

**Pending dependency amendment:** ArcGIS Pro's terrain-correction tools require a DEM that is absent from the exact eight-product approval. A separate, non-authorizing review bundle identifies four exact public Copernicus DEM GLO-30 COG tiles covering the approved AOIs and binds the license that requires owner acceptance. No DEM payload was requested; the amendment must be approved before DEM acquisition or terrain correction.

**Prepared DEM and radar controls:** A four-tile intake candidate, offline ArcGIS GeoTIFF verifier, and two-route Sentinel-1 processing contract are fixed without activation. The primary radar route keeps linear gamma-nought data, retains native terrain-distortion evidence, and defers rather than guessing when only predicted orbit vectors are available or the EGM2008-to-ArcGIS-EGM96 vertical-datum mismatch is unresolved.

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

**Preparatory status:** A metadata-only EPSG:32645 evidence schema, File Geodatabase, APRX, and overview export have passed local ArcGIS Pro 3.7.1 validation. Heavy outputs remain in ignored scratch custody, scientific layers are empty, and this does not satisfy M6 packaging or clean-machine exit evidence.

**Deliverables:** `.aprx`, `.gdb`, `.lyrx`, GeoTIFF, PDF/PNG layouts, metadata, and optionally `.ppkx` after size and license review.

**Exit gate:** Clean-machine/package validation and export test.

## M7 — Public release and maintenance

**Outcome:** Versioned methods, small reproducibility assets, qualified map exports, and a release record.

**Exit gate:** Source rights, privacy, scientific claims, public surfaces, GitHub release, and downloadable artifacts are all verified independently.

## Long-term maintenance

Future versions may add later imagery, field reports, or higher-resolution observations. They must be appended as new evidence with dates and provenance. They must not silently replace the original event-window record.
