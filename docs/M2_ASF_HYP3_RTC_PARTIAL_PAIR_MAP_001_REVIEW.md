# M2 ASF HyP3 partial-pair local map: owner review

**Status:** local zero-decision packet. No public packet publication, second job, product access, or map execution is released by this document.

## What the first product established

The exact before product, `M1-SRC-002` (16 August 2026), passed archive identity, provider metadata, and six real 10 m EPSG:32645 GeoTIFF-header checks. Its one authorized event-AOI pixel attempt is now terminal. Raster footprint coverage is nearly complete, but valid VV/VH area after the actual HyP3 layover/shadow mask and NoData exclusions is **55.135%** in `AOI-SOURCE` and **76.0829%** in `AOI-UPPER-CORRIDOR`. Both are `defer` under the frozen **80%** usable-area pass rule, though both exceed the frozen **20%** partial-evidence floor. No undocumented mask values appeared. The [terminal reconciliation](../records/readiness/m2-asf-hyp3-rtc-product-pixel-001-terminal-reconciliation.json) binds the immutable result; the old attempt cannot be retried or relabeled.

The approved ASF route required a stop on the first source's QA failure. Accordingly, **no `M1-SRC-005` after-scene job was submitted** and no before/after map, registration, change analysis, or attribution exists. High layover/shadow loss in Nepal's terrain is a measured limitation of this product and these event AOIs, not a software fault or reason to tune the existing threshold.

## Proposed map-oriented choice

The [exact proposal](../contracts/milestone-002-asf-hyp3-rtc-partial-pair-map-001-proposal.json) asks whether to make one narrow exception to the sequence stop **for a visual-only partial pair**. It would keep the before-source `defer` and the 80% scientific QA rule intact, but permit at most one free-credit job for the already selected 28 August `M1-SRC-005` scene, then separately gated archive, metadata, header, and pixel checks. It would not request the two adjacent context-strip scenes.

If both dates share at least 20% valid area in **each** event AOI, mask classes are understood, projected grids match, and image-display rights remain clear, the result could be a **local ArcGIS Pro EPSG:32645 side-by-side panel**. Its masked gaps and actual dates would be visible; it would carry the exact ASF/ESA product credit, DOI references, and an explicit warning that full-area QA failed and registration is not validated. A fresh ArcGIS process would reopen and export it. It would contain no difference raster, swipe comparison, change polygons, or event-causation claim. The provider's DEM raster would not be displayed or exported because its XML carries separate rights language.

This route might deliver the practical visual map sooner, but it could still stop: the after product may fail, have worse masked coverage, lack a 20% common valid footprint, or not align sufficiently for even a clearly qualified panel. A partial panel would illustrate observations where both dates have valid pixels; it would not convert the deferred observations into a scientific before/after change result. ASF's [RTC guide](https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/) describes layover/shadow NoData behavior, and its [citation guidance](https://hyp3-docs.asf.alaska.edu/usage_guidelines/) directs users to each product's README for acknowledgement and DOIs.

The alternative is to keep the current stop. That spends no further credits and preserves the full-coverage standard, but leaves this ASF route without a two-date imagery panel. A new optical, descending-orbit, commercial, narrower-AOI, or threshold-changing route would require its own source and method review; none is silently substituted here.

**Decision requested:** approve, revise, or defer the exact single conditional envelope for one `M1-SRC-005` free Basic RTC job and a conditional **local partial-data visual map**. Approval includes public packet and implementation gates and sanitized terminal publication without repeated owner reconfirmation, but not account credentials, paid credits, automatic retries, changed QA thresholds, baseline admission, change analysis, attribution, public pixels, or scientific publication.
