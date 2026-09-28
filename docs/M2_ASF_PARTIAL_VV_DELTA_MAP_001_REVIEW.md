# Proposed next map: registered, partial VV backscatter difference

**Status:** Local zero-decision review. No publication, new pixel read, processing attempt, or map is authorized by this document.

## Why a new decision is needed

The exact 16 August and 28 August ASF HyP3 RTC products now have a [verified local before/after panel](../records/readiness/m2-asf-hyp3-rtc-partial-panel-001-terminal-reconciliation.json). Their same-cell common-valid fractions are **54.6721%** in `AOI-SOURCE` and **75.7928%** in `AOI-UPPER-CORRIDOR`. Both dates remain `defer` under the unchanged 80% full-area usability rule. The panel is on a common 10 m EPSG:32645 grid, but residual image registration has **not** been measured. It cannot support a difference claim yet.

The current [M4 change contract](../config/qa/change-evidence-contract.json) requires `pass_qa_only` and at least 80% usable area before scientific candidate screening. This proposal leaves that rule unchanged. It requests a distinct **exploratory observation product**: one continuous VV backscatter difference over the cells valid on both dates, labeled as partial and unclassified. It would not enter M4 `ObservedChange`, create candidate polygons, or claim landslide or flood causation.

## Exact route and safeguards

The [proposal](../contracts/milestone-002-asf-partial-vv-delta-map-001-proposal.json) reuses only the two immutable staged VV gamma0 dB rasters already used for the panel. No ASF request, credit, ZIP read, new date, or source substitution is proposed. An independent local-display rights check must cover the derivative before real processing. The provider says its RTC products are geocoded gamma0 power by default and documents layover/shadow and imperfect DEM matching; this is why a common projected grid alone cannot substitute for measured registration. [ASF RTC product guide](https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/)

After generated-data and installed ArcGIS tests, public CI, and one no-content preflight, a **single fresh append-only real attempt** would measure residual registration using at least 30 control windows selected by a documented deterministic rule outside the event corridor before examining the difference signal. The unchanged pixel-QA pass bounds apply: RMSE at most 0.5 pixel and absolute bias at most 0.5 pixel in each axis. No spatial shift or resampling is allowed. If control selection or registration fails, the attempt stops without a delta.

Only on pass would the attempt calculate `after VV dB − before VV dB` on the exact common-valid cells, retain continuous values and exclusions, and build a local three-panel ArcGIS layout. The difference panel would use a signed quantitative legend and warnings about partial coverage, unfiltered speckle, terrain geometry, moisture, vegetation, and unknown event causation. NASA provides a log-difference workflow for Sentinel-1 RTC as a method example; that does **not** validate this pair or identify debris. [NASA Earthdata log-difference tutorial](https://www.earthdata.nasa.gov/learn/tutorials/identify-change-using-log-difference-tool)

The APRX, rasters, and exports would stay outside Git. A separate ArcGIS process would reopen and export the project; sanitized receipts and public CI would record success or failure. The consumed source, pair-stage, and panel attempts remain immutable. No automatic retry is requested.

## What this can and cannot deliver

If every gate passes, the result would be a reviewable local **backscatter-change visual** in EPSG:32645, with unknown areas visible and no categorical interpretation. It would move the project beyond two separate dates while preserving the full-area `defer` findings. It would **not** be an M4 scientific candidate map, prove a landslide boundary, establish event attribution, or satisfy final M6 clean-machine delivery. Those require later evidence and decisions.

If this route fails registration, the useful outcome is a durable reason that the current partial pair cannot support a pixelwise difference. An alternative source route, such as archived 30 m OPERA RTC-S1 or a new optical date, would then need its own source identity, rights, coverage, and pixel-QA review. ASF describes OPERA RTC-S1 as a near-global preprocessed archive, but no exact event-area granule has been searched, selected, or validated here. [ASF OPERA RTC-S1 guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/)

**Decision requested:** Approve, revise, or defer the exact proposal as one conditional envelope through sanitized terminal publication. This is one new decision because it authorizes real derived-pixel reading and a new change visual outside the prior visual-only envelope; routine implementation and testing inside it would not require repeated approval.
