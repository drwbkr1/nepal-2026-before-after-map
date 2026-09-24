# M2 event-area radar projected-clip recovery: proposed single decision

**Status:** Local, unpublished, zero-decision review. This document and its proposal authorize no Git publication, ArcPy call, project-data access, or new radar attempt.

## Why the previous recovery stopped

The approved projection-extent recovery ended at its disposable ArcGIS gate. At a 50 m test cell size, an EPSG:32645 extent applied to a generated EPSG:4326 raster produced 3,591,576 cells, but its declared bounds reached approximately **4.6 km south, 4.0 km east, and 4.5 km north** of the frozen target. The allowed extension was 100 m. The result, its earlier validator-development errors, the public CI gates, and the retained generated-only OS temporary files are preserved in the [terminal record](../records/readiness/m2-radar-event-area-pair-projection-extent-recovery-001-disposable-validation-terminal.json). No `e1/a2` root or new real radar process was created. The consumed `e1/a1` attempt remains untouched.

The disposable validator did **not** include the snap raster used by the frozen production projection call. Its failure blocks the approved attempt but does not establish that every snap-aligned approach fails. [Esri documents](https://pro.arcgis.com/en/pro-app/3.3/tool-reference/environment-settings/output-extent.htm) that an Extent environment selects cells rather than strictly clipping an output. [Snap Raster](https://pro.arcgis.com/en/pro-app/3.5/tool-reference/environment-settings/snap-raster.htm) aligns raster cells but can also expand an output by a row or column. Neither setting alone proves the final extent or pixels.

## The proposed method and its test

The proposed event-pair-only method would project each existing gamma-linear, dB display, and categorical distortion-mask GTC raster to a **bounded intermediate** using an EPSG:32645 extent, the frozen snap origin, 10 m cells, and the unchanged BILINEAR or NEAREST resampling choice. The intermediate would have resource ceilings of 100 million declared cells, 10 km extension on any target side, and 10 GiB of logical output bytes. An independent supervisor would have to enforce and durably record those ceilings. These are stop limits, not scientific acceptance criteria.

Only a passing intermediate could be clipped to the frozen buffered EPSG:32645 target rectangle with `NO_MAINTAIN_EXTENT`. [Esri's Clip documentation](https://pro.arcgis.com/en/pro-app/3.6/tool-reference/data-management/clip.htm) says this option retains input cell alignment, while `MAINTAIN_EXTENT` can resample; the latter is excluded. The final output must still pass the frozen 10 m grid, band, mask, coverage, registration, and QA checks. A disposable runtime test must demonstrate exact retained-pixel and mask-class agreement between the intermediate and final clip. This behavior is a **testable proposal**, not a validated scientific result. The packet now binds the owner-approved recovery-specific `REFINED_LEE` amendment and the later event-pair approval; the older six-source contract alone would not establish that exact filter choice.

The disposable validation would use generated broad EPSG:4326 two-band continuous and one-band categorical rasters, the production-equivalent snap setting, a storage-bounded coarse test, and a small 10 m window. If the projected intermediate exceeds any resource ceiling, the clip resamples or shifts the grid, pixels or classes differ unexpectedly, a receipt cannot be persisted, or the final output extends more than 100 m beyond any frozen target side, this envelope stops. It does not silently select another method.

## One conditional authority envelope

One owner decision would cover publication of the exact packet and approval; implementation and portable tests; disposable installed-ArcGIS validation; public CI gates; a final no-content preflight; then, **only if every gate passes**, at most one fresh byte-zero `e1/a2` radar worker for M1-SRC-002 followed by M1-SRC-005, with a separate non-radar supervisor. The exact M2-ORB-001/003, eleven-tile ellipsoidal DEM mosaic, AOIs, EPSG:32645 10 m grid, `REFINED_LEE` sequence, masks, registration, and QA predicates remain fixed. The independent supervisor must stop and preserve a terminal record on oversize or extent drift. There is no automatic retry or source substitution. The old `e1/a1` attempt, its zero-byte receipts, and partial output remain immutable.

Sanitized terminal evidence and public CI are inside the proposed single envelope; no intermediate owner reconfirmation is requested. Even `pass_qa_only` would **not** admit a baseline or authorize change analysis, event interpretation, attribution, derived-pixel publication, or a scientific claim.

## Decision and limits

**Requested choice:** approve, revise, or defer this exact proposal and its hash-bound review bundle as one conditional envelope through sanitized terminal publication. Approval would be effective only after the exact packet and approval pass public default-branch CI. Any failed implementation, disposable, preflight, resource, source, or QA gate stops without retry or another method.

The machine-readable proposal is [`contracts/milestone-002-radar-event-area-pair-projected-clip-recovery-002-proposal.json`](../contracts/milestone-002-radar-event-area-pair-projected-clip-recovery-002-proposal.json). Its SHA-256 and the review-bundle SHA-256 must be verified before a decision is recorded. This local preparation is **not** approval.
