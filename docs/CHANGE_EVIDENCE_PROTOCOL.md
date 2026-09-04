# Candidate change-evidence protocol

## Purpose

`config/qa/change-evidence-contract.json` freezes how valid optical and radar before/after data can become candidate change evidence. It is written before any real post-event pixel processing so thresholds cannot be adjusted to produce a stronger-looking map.

The contract creates no processing authority. The active M2 acquisition, orbit, DEM, vertical-datum, and review gates still apply.

## Independent routes

The ascending Sentinel-1, descending Sentinel-1, and Sentinel-2 RUM routes remain independent through their own QA dispositions. A missing, cloud-masked, terrain-masked, blocked, or deferred route is **not** treated as disagreement with another route.

Every route must first pass the existing pixel-readiness thresholds: at least 99% AOI coverage, at least 80% usable AOI fraction, registration RMSE no greater than 0.5 pixel, and absolute registration bias no greater than 0.5 pixel.

## Stable-reference normalization

Stable reference areas must be locked before change metrics are evaluated and must exclude the event corridor. Each route requires at least 30 control zones and 10,000 valid reference pixels. Change signals are centered on the stable-reference median and standardized with median absolute deviation multiplied by 1.4826.

A zero or nonfinite stable-reference scale defers the route. Controls may not be reselected after observing the result, and dates may not be changed to rescue a route.

## Radar candidates

For each orbit route, VV and VH retain separate `after dB minus before dB` measurements. A pixel becomes a radar candidate for a polarization only when both conditions hold:

- absolute change is at least 1.5 dB;
- absolute robust z-score is at least 3.5.

Positive and negative changes remain separate observation classes. One polarization may identify a candidate, while matching VV/VH direction is retained as stronger support within that route. Opposite directions are preserved and flagged for review rather than averaged away.

## Optical candidates

The optical route retains three distinct observations:

| Metric | Direction | Minimum change | Minimum robust z | Observation class |
|---|---:|---:|---:|---|
| NDVI | before minus after | 0.20 | 3.5 | vegetation index decrease |
| NBR | before minus after | 0.15 | 3.5 | normalized burn ratio decrease |
| MNDWI | after minus before | 0.20 | 3.5 | modified water index increase |

These are measured index changes. They are not labels for a landslide scar, debris deposition, inundation, or event causation.

## Candidate objects

Eight-neighbor candidate pixels are grouped without result-driven threshold changes. The minimum mapping unit is 5,000 square metres, holes below 400 square metres may be removed, and the fixed simplification tolerance is 10 metres. Candidate raster area must agree with pixel count and route cell size within 1%. Continuous delta rasters and a summary of subthreshold objects remain in evidence even when no polygon passes.

Manual rescue of a subthreshold object is prohibited. A fully testable route with zero candidates receives `pass_no_candidate_observed`, not failure.

## Cross-route synthesis

Route results can be synthesized only after all three independent route dispositions are final. Candidate polygons are labeled spatially coincident when overlap covers at least 25% of the smaller polygon. Radar and optical coincidence may be labeled multisensor support, but it remains spatial coincidence rather than attribution.

Nonoverlapping testable candidates are retained as disagreement. A single passing route remains a single-route candidate. If another route is untestable, the synthesis remains inconclusive instead of manufacturing disagreement.

## Claim boundary

Portable tests exercise robust normalization, optical and radar rules, minimum mapping units, zero-candidate behavior, failure preservation, and synthesis semantics. They do not access satellite data or create scientific observations.

Any future `pass_candidate_only` output must enter the `ObservedChange` structure with exact sources, dates, QA, uncertainty, limitations, and review state. Interpretation and attribution remain separate later human-review steps.
