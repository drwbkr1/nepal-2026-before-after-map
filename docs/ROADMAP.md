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

**Status:** Active with one Sentinel checkpoint, one dependent orbit checkpoint, and two independent DEM review checkpoints. The exact eight-product Sentinel plan is at `M2-ACQUISITION-REVIEW`: three exact Sentinel-1 archives are promoted and container-verified, one partial is retained after exact-length failure, and four products remain unattempted. The exact four-file `AUX_RESORB` amendment is approved, but its acquisition route is at `M2-ORBIT-ACQUISITION-REVIEW` after a test-induced zero-byte failed request. The corrected runner stops before catalogue or token access until the full `M2-VERIFY` unit is complete. The approved four-tile DEM amendment remains at `M2-DEM-VERTICAL-DATUM-REVIEW`, while the completed terrain screen has a separate `M2-DEM-TERRAIN-RESULT-REVIEW`. All four exact DEM tiles are promoted and have passed ArcGIS structural, valid-AOI-coverage, fixed terrain-artifact, seam, slope, projection, manifest, and exported-map checks. Vertical-datum fitness, independent elevation accuracy, pair-specific radar fitness, and scientific fitness remain unresolved.

**Prepared verification:** Deterministic offline controls define exact container identity, checksum, ZIP safety, SAFE structure, required radar/optical members, and the later pixel-readiness gates. The active wrapper refuses archive access until a promoted intake identity and successful-transfer receipt exist. Three exact Sentinel-1 archives have passed container-only verification; real-data readiness remains `defer` because acquisition is incomplete and no raster or pixel QA has passed.

**Prepared pixel QA:** The EPSG:32645 coverage, mask, grid-alignment, and registration thresholds are fixed before product access. The portable core and ArcGIS Pro 3.7.1 Spatial Analyst adapter pass synthetic validation only; real-product readiness remains `defer`.

**Approved dependency amendment:** ArcGIS Pro's terrain-correction tools require a DEM that is absent from the exact eight-product Sentinel approval. The owner approved the separate hash-bound review bundle, accepted the exact Copernicus WorldDEM-30 license, and authorized only four named public Copernicus DEM GLO-30 COG tiles covering the approved AOIs. The required fresh source and custody preflight passed before payload transfer.

**Verified DEM and prepared radar controls:** Four exact rasters totaling 170,302,058 bytes were acquired anonymously and promoted outside Git with per-tile SHA-256, remote-identity, and reconciliation receipts; no transfer failed. ArcGIS Pro 3.7.1 read all four as 3600-by-3600, single-band F32 EPSG:4326 rasters and found 51,840,000 finite non-NoData cells with zero NoData or nonfinite cells. Every approved AOI bound lies inside the continuous verified footprint. The fixed terrain screen then passed four tile checks, four seams, AOI slope, EPSG:32645 projection, 189-file manifest reconciliation, and PNG/PDF visual inspection. Two earlier terrain-wrapper failures remain retained. This establishes gross-artifact and map-surface fitness only. The two-route Sentinel-1 contract keeps linear gamma-nought data, retains native terrain-distortion evidence, and defers rather than guessing when only predicted orbit vectors are available or the EGM2008-to-ArcGIS-EGM96 vertical-datum mismatch is unresolved.

**Vertical-datum review:** A bundle-bound proposal recommends installing ArcGIS's optional EGM2008 one-minute transformation component under owner control, converting verified DEM copies from EPSG:3855 orthometric height to WGS 84 ellipsoidal height, and using `NONE` only for those verified derivatives. The local runtime currently has only the built-in EGM96 grid, so the exact route cannot run. Bundle SHA-256 `9b40e81df766ea866c5bff51cdbc4d83e7e7da6a554fb1709fc553d8221bebbc` awaits a human decision and does not authorize installation or terms acceptance.

**Terrain-quality gate:** The four exact promoted DEM hashes, two east-west and two north-south seams, fixed artifact and slope thresholds, and no-overwrite outputs were bound before observation. Attempt-001 failed before source open because its root omitted the `custody` segment. Attempt-002 created outputs but failed before a stable manifest while opening a transient ArcGIS lock; its metrics were not persisted. Both failures and paths remain preserved. Attempt-003 excluded only `.lock` files, hashed all 189 stable files, reverified unchanged source custody, horizontally projected the mosaic to EPSG:32645 at 30 metres without a vertical transform, calculated AOI slope and hillshade, and exported the external APRX/PNG/PDF. All quantitative and visual criteria passed. The separate readiness audit remains `defer`. Bundle SHA-256 `834ad354fc134b2017afdd3b238c1a6271276e8b1a95776e434180c7283a26d5` now presents the exact terrain result for owner review with zero human decisions. Even approval cannot resolve vertical datum, independent elevation accuracy, pair-specific radar processing, or scientific fitness.

**Activated Sentinel-1 orbit amendment:** Official CDSE metadata produced one deterministic full-coverage S1D `AUX_RESORB` selection for each of the four unique radar acquisition windows. The four files total 2,539,715 bytes and bind exactly to the six approved Sentinel-1 source IDs. The owner approved exact bundle `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1` and proposal `b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292`; the response was locked, reconciled, and activated. A stale production-wrapper test later reached a rejected `M2-ORB-001` request using a tracked nonsecret literal. It received zero payload bytes, created no payload file, and is retained as a terminal failure. The corrected runner now requires the full `M2-VERIFY` milestone unit before catalogue access, token lookup, events, or payload requests. Twenty-nine focused tests pass without further mutation. The exact orbit recovery bundle `df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b` and proposal `ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a` remain blank and cannot release an early retry. No covering `AUX_POEORB` candidate was available at assessment time, and later precise substitution remains separately gated.

**Prepared optical controls:** The exact RUM pair has fixed Level-2A metadata parsing, BOA reflectance scaling, conservative SCL masking, 20 m EPSG:32645 alignment, index formulas, and cross-platform safeguards. Portable tests and ArcGIS synthetic processing pass, while the real high-cloud-risk route remains deferred until acquired pixels prove coverage and registration.

**Prepared materialization controls:** Each exact promoted archive must first pass the offline container gate, after which a collision-safe runner can create one append-only external SAFE attempt with a per-file SHA-256 manifest. Unsafe Windows paths, ambiguous paths, links, collisions, and archive drift fail closed. A stale wrapper test unintentionally materialized exact `M1-SRC-001`; its 26 files and 1,732,324,248 bytes passed independent manifest hashing and remain preserved as materialization-only evidence with unintended-test provenance. No raster readability, pixel usability, baseline, change, or scientific admission is established.

**Prepared optical input gate:** Two exact passing materialization receipts can feed an ArcGIS-native header-readiness runner. It re-hashes ten required members per SAFE, parses Level-2A scaling metadata, opens sixteen JP2 rasters, verifies EPSG:32645 10 m/20 m grids, and compares before/after headers before pixel access. Portable and ArcGIS synthetic tests pass; real input readiness remains deferred.

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
