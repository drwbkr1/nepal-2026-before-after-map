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

**Status:** Active at `M2-RADAR-FIRST-PATH-001-REVIEW` after the reconciled terminal optical recovery. All eight exact Sentinel archives are promoted, container-verified, and materialized by identity; both earlier incomplete `M1-SRC-004` partials and the stopped first continuation remain preserved. One full six-source radar and one full two-source optical header inspection passed without measurement-pixel decoding. Optical real-001 remains terminal `INVALID`; recovery-001 completed once as `BLOCK` under the fixed usable-pixel and registration criteria. The exact four-file `AUX_RESORB` amendment is approved, but the old blank orbit-recovery packet is preserved as stale because it requires aggregate `M2-VERIFY`, which cannot complete while optical is blocked. A zero-decision control-only review now asks whether to split route-specific readiness and prepare a corrected orbit packet. The approved four-tile DEM amendment remains at `M2-DEM-VERTICAL-DATUM-REVIEW`, while the completed terrain screen has a separate `M2-DEM-TERRAIN-RESULT-REVIEW`. Vertical-datum fitness, independent elevation accuracy, pair-specific radar fitness, optical pixel usability, and scientific fitness remain unresolved.

**Verification result:** Deterministic offline controls define exact container identity, checksum, ZIP safety, SAFE structure, required radar/optical members, and later pixel-readiness gates. All eight exact archives have passed container-only verification and append-only SAFE materialization, and both full-cohort header routes passed. Optical real-001 is terminal `INVALID`; recovery-001 established exact QA metrics but is terminal `BLOCK`. Radar pixels remain gated.

**Pixel-QA result:** The EPSG:32645 coverage, mask, grid-alignment, and registration thresholds were fixed before product access. Real-001 stopped after its first SCL read because the production grid stores bounds under `analysis_grid.extent`. The approved correction passed portable and ArcGIS tests; recovery-001 then produced QA-only metrics and a classification raster but no spectral indices, baseline, or change product.

**Terminal optical recovery:** Recovery proposal SHA-256 `96f0125628e894061fc5da55faff94e92e51b0385293576177c1e15bd009b3da` and review bundle SHA-256 `d137b8ac1d46531ae42e7944955829eb2df37985428431b39863f4a157e83ac2` preserved real-001 and released only one corrected append-only recovery. Commit `395b63e1bd5c53a39ca3e2601768ba5a00f4bcf4` passed CI run `33989213698`; the preflight then passed and the attempt completed once. `AOI-SOURCE` is fully covered but only 6.3252 percent usable; `AOI-UPPER-CORRIDOR` is fully covered but only 25.6403 percent usable; the overview is 54.1205 percent covered and 7.9392 percent usable. Registration deferred with 20 accepted controls and 0.5087-pixel RMSE. The aggregate result is `BLOCK`, and the recovery authority is consumed. Radar pixel reads, orbit and DEM actions, baselines, change products, retries, substitutions, and scientific publication remain excluded.

**Post-optical route review:** Analysis SHA-256 `19672e1d646b5ee6131f57c99710c2483b9deb17743f833dd662edaa8afd128e` records that the old orbit-recovery review's full-`M2-VERIFY` prerequisite deadlocks the predeclared independent radar branch. Bundle SHA-256 `5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad` binds proposal SHA-256 `ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77` with zero human decisions. Approval would authorize only a route-specific control amendment and preparation of a corrected blank orbit review; it would not authorize DEM or orbit action, radar pixels, a new optical search, baseline, or change analysis.

**Approved dependency amendment:** ArcGIS Pro's terrain-correction tools require a DEM that is absent from the exact eight-product Sentinel approval. The owner approved the separate hash-bound review bundle, accepted the exact Copernicus WorldDEM-30 license, and authorized only four named public Copernicus DEM GLO-30 COG tiles covering the approved AOIs. The required fresh source and custody preflight passed before payload transfer.

**Verified DEM and prepared radar controls:** Four exact rasters totaling 170,302,058 bytes were acquired anonymously and promoted outside Git with per-tile SHA-256, remote-identity, and reconciliation receipts; no transfer failed. ArcGIS Pro 3.7.1 read all four as 3600-by-3600, single-band F32 EPSG:4326 rasters and found 51,840,000 finite non-NoData cells with zero NoData or nonfinite cells. Every approved AOI bound lies inside the continuous verified footprint. The fixed terrain screen then passed four tile checks, four seams, AOI slope, EPSG:32645 projection, 189-file manifest reconciliation, and PNG/PDF visual inspection. Two earlier terrain-wrapper failures remain retained. This establishes gross-artifact and map-surface fitness only. The two-route Sentinel-1 contract keeps linear gamma-nought data, retains native terrain-distortion evidence, and defers rather than guessing when only predicted orbit vectors are available or the EGM2008-to-ArcGIS-EGM96 vertical-datum mismatch is unresolved.

**Vertical-datum review:** A bundle-bound proposal recommends installing ArcGIS's optional EGM2008 one-minute transformation component under owner control, converting verified DEM copies from EPSG:3855 orthometric height to WGS 84 ellipsoidal height, and using `NONE` only for those verified derivatives. The local runtime currently has only the built-in EGM96 grid, so the exact route cannot run. Bundle SHA-256 `9b40e81df766ea866c5bff51cdbc4d83e7e7da6a554fb1709fc553d8221bebbc` awaits a human decision and does not authorize installation or terms acceptance.

**Terrain-quality gate:** The four exact promoted DEM hashes, two east-west and two north-south seams, fixed artifact and slope thresholds, and no-overwrite outputs were bound before observation. Attempt-001 failed before source open because its root omitted the `custody` segment. Attempt-002 created outputs but failed before a stable manifest while opening a transient ArcGIS lock; its metrics were not persisted. Both failures and paths remain preserved. Attempt-003 excluded only `.lock` files, hashed all 189 stable files, reverified unchanged source custody, horizontally projected the mosaic to EPSG:32645 at 30 metres without a vertical transform, calculated AOI slope and hillshade, and exported the external APRX/PNG/PDF. All quantitative and visual criteria passed. The separate readiness audit remains `defer`. Bundle SHA-256 `834ad354fc134b2017afdd3b238c1a6271276e8b1a95776e434180c7283a26d5` now presents the exact terrain result for owner review with zero human decisions. Even approval cannot resolve vertical datum, independent elevation accuracy, pair-specific radar processing, or scientific fitness.

**Activated Sentinel-1 orbit amendment:** Official CDSE metadata produced one deterministic full-coverage S1D `AUX_RESORB` selection for each of the four unique radar acquisition windows. The four files total 2,539,715 bytes and bind exactly to the six approved Sentinel-1 source IDs. The owner approved exact bundle `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1` and proposal `b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292`; the response was locked, reconciled, and activated. A stale production-wrapper test later reached a rejected `M2-ORB-001` request using a tracked nonsecret literal. It received zero payload bytes, created no payload file, and is retained as a terminal failure. The corrected runner now requires the full `M2-VERIFY` milestone unit before catalogue access, token lookup, events, or payload requests. Twenty-nine focused tests pass without further mutation. The exact orbit recovery bundle `df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b` and proposal `ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a` remain blank and cannot release an early retry. No covering `AUX_POEORB` candidate was available at assessment time, and later precise substitution remains separately gated.

**Prepared optical controls:** The exact RUM pair has fixed Level-2A metadata parsing, BOA reflectance scaling, conservative SCL masking, 20 m EPSG:32645 alignment, index formulas, and cross-platform safeguards. Portable tests and ArcGIS synthetic processing pass, while the real high-cloud-risk route remains deferred until acquired pixels prove coverage and registration.

**Completed materialization controls:** Each exact promoted archive passed the offline container gate before a collision-safe runner created one append-only external SAFE attempt with a per-file SHA-256 manifest. A stale wrapper test unintentionally materialized exact `M1-SRC-001`; the other seven products were later materialized under their released routes, including the final five in the approved order and at most once each. Reconciliation SHA-256 `71013b14363f941d41411dff24e5410a6f8682976f8ac9844ff2b2e9ec772d82` rehashed all materialized files. Materialization establishes no pixel usability, baseline, change, or scientific admission.

**Radar input gate result:** The fixed offline contract passed portable, synthetic ArcGIS, publication, and public-CI preconditions before one real invocation. All exact inventories, annotation structures, embedded vectors, and six ArcGIS U16 TIFF-header reads passed, but the aggregate result is **BLOCK** because the six real annotations use `Detected` where the frozen contract required `AMPLITUDE`. The receipt and unchanged custody are retained. A separately approved one-field amendment later passed one real-002 header inspection for the same three materialized sources, while preserving the original block. The unmaterialized post-event scenes still prevent a radar pair or baseline.

**Radar input amendment:** Official Sentinel-1 documentation resolves the schema semantics in favor of `Detected`, while describing the physical values as detected amplitude. The owner approved a one-field contract correction, new synthetic identities, public CI, and one real-002 read-only inspection. Real-002 passed partial pre-event header readiness; it is post-observation confirmation, real-001 remains preserved as **BLOCK**, and neither result releases pixel decoding or baseline processing.

**Optical input gate result:** The two exact materialization receipts fed the published ArcGIS-native header-readiness runner. It re-hashed ten required members per SAFE, parsed Level-2A scaling metadata, opened sixteen JP2 rasters, verified EPSG:32645 10 m/20 m grids, and compared before/after headers without measurement-pixel decoding. The real header gate passed once. The later pixel route remains invalid and separately gated.

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

**Preparatory status:** `config/qa/change-evidence-contract.json` freezes candidate-screening behavior before real post-event processing. It requires 30 locked stable-control zones and 10,000 valid control pixels per route, median/MAD normalization, two-sided 1.5 dB and robust-z 3.5 radar thresholds, fixed NDVI/NBR/MNDWI delta and robust-z thresholds, a 5,000-square-metre mapping unit, complete accounting for all three routes, and a 25% overlap rule for spatial coincidence. Twelve synthetic tests distinguish candidate, zero-candidate, defer, block, disagreement, and inconclusive outcomes without creating interpretation or attribution. No real M4 processing is authorized or complete.

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

**Preparatory status:** A metadata-only EPSG:32645 evidence schema, File Geodatabase, APRX, and overview export have passed local ArcGIS Pro 3.7.1 validation. One bounded, publication-gated `.ppkx` package, extraction, reopen, and re-export attempt also passed with all operational sources inside the extraction tree and an exact pixel match. A post-run verification mistake created a second unplanned extraction; it is preserved as a process-conformance failure. A distinct final-delivery contract now requires five complete maps, nonempty reviewed scientific evidence, source and uncertainty links, preserved failed/deferred/inconclusive history, projected vectors and GeoTIFFs, visible exclusions, hashes, and a clean-environment package reopen. Eight synthetic evaluator tests pass, but heavy outputs remain outside Git, scientific layers are empty, and neither the same-machine fixture nor synthetic control readiness satisfies M6.

**Deliverables:** `.aprx`, `.gdb`, `.lyrx`, GeoTIFF, GeoPackage, PDF/PNG layouts, metadata, and a `.ppkx` after size and license review.

**Exit gate:** Clean-machine/package validation and export test.

## M7 — Public release and maintenance

**Outcome:** Versioned methods, small reproducibility assets, qualified map exports, and a release record.

**Exit gate:** Source rights, privacy, scientific claims, public surfaces, GitHub release, and downloadable artifacts are all verified independently.

## Long-term maintenance

Future versions may add later imagery, field reports, or higher-resolution observations. They must be appended as new evidence with dates and provenance. They must not silently replace the original event-window record.
