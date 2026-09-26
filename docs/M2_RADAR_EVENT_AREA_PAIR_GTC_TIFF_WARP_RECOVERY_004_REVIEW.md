# M2 map route: radar GTC–TIFF–Warp recovery-004 review

**Status:** Local zero-decision packet. Reading this document or the proposal grants no Git publication, disposable execution, protected-data access, or new radar attempt.

## Decision in one envelope

Approve, revise, or defer the [exact proposal](../contracts/milestone-002-radar-event-area-pair-gtc-tiff-warp-recovery-004-proposal.json) as one conditional route for the approved ascending M1-SRC-002/005 pair. An approval would cover packet and response publication, implementation, source-free portable and installed-runtime tests, public CI gates, final no-content preflight, actual-extent DEM assessment, at most **one** new e1/a3 real process, frozen pixel QA, and sanitized terminal publication. Each dependent stage starts only if its preceding gate passes. No intermediate owner reconfirmation is requested for unchanged work inside this envelope.

## Why a new method is needed

The acquired M2-OPT-001/002 pair is no longer an unassessed fallback. Both headers passed, but frozen pixel QA **blocked all three AOIs**. Paired usable fractions were 16.6696% at the source and 9.7665% at the upper corridor, below the frozen 20% partial floor; only 9 B11 registration controls passed versus 30 required. Its real-001 attempt is terminal and cannot be retried, remasked, or threshold-relaxed under the old approval. [Optical terminal reconciliation](../records/readiness/m2-optical-gdal-header-pixel-recovery-002-post-ci-reconciliation.json)

The exact ascending radar pair has the strongest **catalog-footprint** event-AOI coverage, but no real usable pair has been established. The earlier saved M1-SRC-002 GTC output is EPSG:4326 at 2 × 2 ten-degree cells. Recovery-003 then stopped on a broad generated raster before any new real processing: its ProjectRaster output extended 950–1,550 m beyond the target where the approved maximum was 100 m. That old method and attempt authority are closed. The historical coarse-grid cause remains unknown. [Disposable terminal](../records/readiness/m2-radar-event-area-pair-native-gtc-grid-recovery-003-disposable-terminal-reconciliation.json)

## Proposed bridge and exact output

Keep the exact ascending source and orbit order, eleven approved ellipsoidal DEM tiles, `GEOID NONE`, approved `REFINED_LEE` sequence, AOIs, mask, registration, and QA contract. Isolate the native GTC environment, and inspect its returned raster **before save**. A 2 × 2, coarse, missing-metadata, oversized, nonintersecting, or invalid-DEM-supported native result blocks. A valid-looking cell size remains only a gross screen, not proof of native information or geolocation.

The new step is an ArcGIS native-CRF-to-TIFF copy followed by GDAL Warp to the **exact** frozen EPSG:32645 frame: bounds `[272300, 3069230, 368820, 3150210]`, 9,652 columns, 8,098 rows, 10 m cells. The installed GDAL runtime did not report a CRF driver. [Esri Copy Raster](https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/copy-raster.htm) documents TIFF output, and [GDAL WarpOptions](https://gdal.org/en/stable/api/python/utilities.html) exposes explicit target bounds, size, CRS, and resampling. These interfaces support a **testable hypothesis**, not a demonstrated value-preserving bridge. Generated CRF/TIFF tests must compare CRS, transform, dimensions, band count, type, NoData, finite values, and pixels before any actual source reaches this step. Use bilinear sampling for continuous gamma and nearest for categorical masks. Exact output dimensions do not prove coverage; actual finite pixels, masks, DEM support, and AOI/registration QA still decide usability. [Method design](M2_POST_OPTICAL_QA_MAP_ROUTE_DESIGN_001.md)

## Fixed stop and claim boundary

Portable tests, installed ArcGIS disposable tests, public implementation and execution CI, and a final no-content preflight must pass in order. The preflight checks exact identities, resources, old-attempt immutability, and absence of a fresh e1/a3 root. A read-only actual processed-extent DEM proof must pass before real geoprocessing. The sole optional real process begins with M1-SRC-002 and reaches M1-SRC-005 only if the first source passes every independent native, bridge, projected-grid, mask, event-AOI, and persistence gate. Any failure or uncertainty stops; there is no automatic retry, source/date switch, Clip, ProjectRaster fallback, or output enlargement. Prior attempts and private optical QA artifacts stay immutable.

Even a full real-pixel QA pass would mean `PASS_QA_ONLY`. It would not admit a baseline, calculate observed change, justify a landslide interpretation or attribution, publish derived pixels, or finish the ArcGIS map. A block or defer is an acceptable terminal result. The owner can approve this exact bundle and proposal by SHA-256, request revisions, or defer. Until then, **no part of the proposed envelope is active**.
