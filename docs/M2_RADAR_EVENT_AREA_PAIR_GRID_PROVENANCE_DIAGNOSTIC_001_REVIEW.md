# M2 radar event-area pair: grid provenance diagnostic-001

## Decision

Approve, revise, or defer one bounded **read-only metadata diagnostic** of five exact saved M1-SRC-002 rasters in the preserved `e1/a1` attempt. Approval would cover the packet, implementation and synthetic tests, public CI gates, one final no-content preflight, at most one distinct ArcGIS diagnostic process, and sanitized terminal publication without intermediate owner reconfirmation. It would not authorize another radar-processing attempt.

## Why this is the next gate

The consumed event-pair attempt's [published reconciliation](../records/processing/m2-radar-event-area-pair-001-radar-terminal-indeterminate-reconciliation.json) says that a saved GTC input *declared* EPSG:4326 bounds `[80, 10, 100, 30]` and pixel size `[10, 10]` degrees. If those values describe an internally consistent grid, they imply only two cells per side. That is an inference from the record, **not** an independent measurement of the readable CRF, its valid pixels, or the stage that introduced the declaration. Resampling such a source to a 10 m grid cannot create missing spatial detail; [Esri's cell-size guidance](https://pro.arcgis.com/en/pro-app/3.6/tool-reference/environment-settings/cell-size.htm) cautions that finer output cells do not create new data.

The later projected-clip disposable test [stopped](../records/readiness/m2-radar-event-area-pair-projected-clip-recovery-002-disposable-validation-terminal.json) because the projected intermediate began 900 m east of the frozen western target boundary. Its terminal publication and CI are reconciled. It did not establish the cause of that geometry, the actual GTC grid, or radar fitness. `e1/a2` was not started. The failed method remains closed.

## Proposed read-only boundary

After packet approval and public CI, a diagnostic-only implementation would inspect, in order, `gamma0_linear_slant.crf`, `gamma0_linear_despeckled.crf`, `gamma0_linear_gtc_raw.crf`, `gamma0_db_gtc_raw.crf`, and `geometric_distortion_mask_gtc_raw.crf` under the exact preserved `e1/a1/s/2` root. It would compare ArcPy `Raster` and `Describe` width, height, band count, CRS, cell size, and extent. Before interpreting the saved GTC input's CRF configuration, it must match the published SHA-256 `eff271e62660d4ae2fe64d614c9051a953c750f167926b946dcf3cb5e9c7d419`; a mismatch stops the process. This can identify whether the declaration is consistently reported and which saved stage first shows it. The diagnostic would read **no pixels** and call no geoprocessing or raster function. Missing, inconsistent, or ambiguous metadata stops the process.

The attempt root and old zero-byte receipts remain immutable. A new, distinct append-only terminal and cleanup receipt must be reserved before any exact metadata read. Only sanitized metadata and hashes may enter Git. No source replacement, reprojection, clipping, new radar attempt, baseline, change analysis, attribution, or scientific publication follows automatically, whatever the diagnostic says.

## Decision requested

Approve the exact proposal and review bundle by their SHA-256 hashes, revise the scope, or defer. This local packet contains **zero owner decisions** and grants no access or execution by itself.
