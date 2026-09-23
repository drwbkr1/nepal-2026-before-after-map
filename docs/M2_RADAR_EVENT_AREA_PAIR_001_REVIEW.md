# M2 radar event-area pair and DEM scope: one proposed decision

**Status:** Local, unpublished proposal. No decision has been recorded. The controlling machine-readable proposal is `contracts/milestone-002-radar-event-area-pair-001-proposal.json`; this page explains its scope but does not release work.

## Why this is the next route

The approved before/after Sentinel-1 sources M1-SRC-002 (16 August) and M1-SRC-005 (28 August) share ascending relative orbit 85. Their *catalog polygons* jointly cover 100% of both approved event AOIs. The context slices M1-SRC-001/004 do not intersect either event AOI. The separate descending pair covers the source AOI in catalog geometry but only about 58.7% of the upper corridor. These are metadata observations, not usable-pixel or change findings. The successful, consumed DEM-supplied M1-SRC-001 diagnostic cannot establish that 002/005 will process or cover the event.

Four previously approved DEM tile boxes cover the event AOIs, but they do not span the full 002/005 catalog swaths. The frozen radar baseline contract requires DEM coverage of the entire processed SAR extent. Esri documents NoData outside a partial DEM in radiometric terrain flattening and a metadata-tie-point approximation outside a partial DEM in geometric correction; the latter is described for full-ocean scenes, not a Nepal land scene. This proposal keeps the full-extent guardrail rather than treating an AOI box as sufficient.

## The exact source expansion

One owner decision would add only these seven Copernicus DEM GLO-30 COG item IDs, observed in public STAC and anonymous HEAD metadata, in fixed order:

1. `Copernicus_DSM_COG_10_N27_00_E086_00_DEM`
2. `Copernicus_DSM_COG_10_N28_00_E083_00_DEM`
3. `Copernicus_DSM_COG_10_N28_00_E086_00_DEM`
4. `Copernicus_DSM_COG_10_N29_00_E083_00_DEM`
5. `Copernicus_DSM_COG_10_N29_00_E084_00_DEM`
6. `Copernicus_DSM_COG_10_N29_00_E085_00_DEM`
7. `Copernicus_DSM_COG_10_N29_00_E086_00_DEM`

The observed headers total **273,055,703 bytes**. They identify candidates only; no new payload or valid pixels have been verified. The license PDF is the exact document already accepted for the earlier four tiles (SHA-256 `9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd`), but that earlier approval did **not** authorize these seven requests. The source assessment passes its eight source criteria for *candidate acquisition review* and returns **zero authorized next actions**.

## One bounded envelope if approved

The proposed decision covers packet publication and public CI; implementation, portable and disposable ArcGIS tests; fresh no-payload preflight; bounded seven-tile acquisition, verification, non-Git custody, and offline EGM2008 PROJ25-to-ellipsoidal conversion; an append-only eleven-tile DEM mosaic; actual full-extent and valid-elevation checks; then, only if every gate passes, one fresh process over **M1-SRC-002 followed by M1-SRC-005**. The process uses the exact restituted orbit files M2-ORB-001/003, keeps VV/VH separate, and explicitly carries the recovery-specific `REFINED_LEE` step after gamma terrain flattening and before DEM-supplied geometric correction. That filtered output is a **QA candidate**, not an admitted quantitative baseline.

QA retains the frozen EPSG:32645 10 m grid, mask classes, 0.99 AOI coverage and 0.80 usable-fraction pass thresholds, and registration requirements (at least 30 stable control pairs, at most 0.5-pixel RMSE and absolute bias for pass). Every `invalid`, `block`, or `defer` outcome is retained. Even `pass_qa_only` would release no difference raster, baseline admission, geomorphic interpretation, event attribution, derived-pixel publication, or scientific claim.

The seven tiles would be requested in fixed order, with complete byte and GeoTIFF verification before no-replace promotion. A transport interruption permits at most one separately recorded fresh byte-zero request for the *same* exact tile after a new preflight; no partial resume or automatic retry. An integrity, rights, conversion, DEM-coverage, ArcGIS, pixel, or registration failure stops dependent work. No consumed attempt is reused. Agent-created code or receipt defects may be corrected before real access under the same unchanged envelope and fresh public CI, without an intermediate owner reconfirmation.

## What the decision changes, and what it does not

The proposed 002/005 subset and seven-tile scope are **new normative choices**. The historical six-source source order, old attempts, receipts, and baseline contract remain immutable. The previously approved `REFINED_LEE` sequence was recovery-specific and must be expressly selected for this new QA route; it is not silently promoted into a production baseline method. The seven additional tile boxes are only a catalog plan: actual SAR and DEM extent and valid-pixel fitness must pass before processing.

The alternative of keeping the full six-source route involves fourteen additional catalog DEM candidates. Using only the four existing tiles for full-swath 002/005 processing conflicts with the current full-extent guardrail. This review proposes the bounded event-area pair because it targets the approved event AOIs with fewer new source candidates, while retaining independent later review of any baseline or change map.

**Current boundary:** This local page and proposal authorize no Git publication, owner response recording, payload request, conversion, ArcPy invocation, project-pixel read, baseline, change analysis, or scientific publication. One exact owner decision is needed after the packet is frozen and validated.
