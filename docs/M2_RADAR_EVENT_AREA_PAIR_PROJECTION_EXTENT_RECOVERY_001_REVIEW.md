# M2 event-area radar projection-extent recovery: proposed single decision

**Status:** Local, unpublished, zero-decision review. This page and the companion proposal authorize no implementation, ArcPy call, new attempt, or Git publication.

## What happened

The approved event-area pair process started M1-SRC-002 and completed orbit application, radiometric steps, despeckling, and geometric terrain correction. Its first 10 m EPSG:32645 `ProjectRaster` output then declared **50,407,536,640 cells** across roughly 2,205 by 2,286 km. The frozen buffered study grid is **78,161,896 cells** across roughly 96.5 by 81.0 km. The declared output area was **644.91 times** the target. The process was stopped to limit compute and storage exposure; the interrupt exited without terminal or cleanup receipts. The zero-byte reservations and partial output remain untouched outside Git. M1-SRC-002 has no terminal QA receipt; M1-SRC-005 and pair QA never started. The frozen SAFE, orbit, DEM, and mosaic identities passed a post-stop read-only check. The attempt is consumed and cannot be reused or retried.

The [sanitized incident record](../records/processing/m2-radar-event-area-pair-001-radar-terminal-indeterminate-reconciliation.json), [publication gate](../records/readiness/m2-radar-event-area-pair-001-terminal-indeterminate-publication-gate.json), and [post-CI reconciliation](../records/readiness/m2-radar-event-area-pair-001-terminal-indeterminate-publication-reconciliation.json) preserve the exact evidence. No useful radar pixel result or scientific outcome was established.

## A testable explanation, not a finding

The current runner supplies its buffered **EPSG:32645 metre** coordinates to ArcPy as a space-delimited extent string, while the saved GTC input declares **EPSG:4326**. [Esri's Extent environment documentation](https://pro.arcgis.com/en/pro-app/3.3/tool-reference/environment-settings/output-extent.htm) says a coordinate-system-free extent uses the first input's coordinate system; the output coordinate system does not change that interpretation. It also says an extent selects cells and is not a strict clip. [ArcPy's Extent class](https://pro.arcgis.com/en/pro-app/3.6/arcpy/classes/extent.htm) supports an explicit spatial reference, and [Project Raster](https://pro.arcgis.com/en/pro-app/3.4/tool-reference/data-management/project-raster.htm) honors the Extent environment.

That mismatch is a plausible cause of the gross output footprint. The exact ArcGIS runtime mechanism remains **unproven**. The proposed recovery first tests a CRS-explicit extent on disposable rasters with analogous broad EPSG:4326 input metadata at a coarse, storage-bounded resolution. A failed or inconclusive installed-runtime test stops before real data access; it does not trigger an alternate method.

## One conditional authority envelope

One owner decision would cover packet publication and public CI; an event-pair-only projection adapter and synthetic tests; installed ArcGIS disposable validation; implementation publication and public CI; a final no-content preflight; then **at most one new, distinct, byte-zero process** at `e1/a2` for exact M1-SRC-002 followed by M1-SRC-005. The same M2-ORB-001/003, eleven-tile ellipsoidal DEM mosaic, approved AOIs, 10 m EPSG:32645 grid, `REFINED_LEE` sequence, mask, registration, and QA thresholds remain fixed. The consumed `e1/a1` attempt and historical runner and contracts remain immutable.

The new process would have an independent durable supervisor guard. If a projected output declares more than **100,000,000 cells** or extends more than **100 m** past any side of the frozen target grid, the guard stops it and records a supervised terminal classification. Those are resource ceilings, not relaxed scientific pass criteria. The production QA predicates remain unchanged. If the guard cannot persist its own receipt, or if any source or QA gate fails, stop without retry or source substitution. No second source begins after first-source failure.

Every publication and implementation gate must pass public default-branch CI before real access. The new attempt requires a fresh no-content preflight proving exact immutable inputs, absent `e1/a2`, adequate disk, and the installed ArcGIS runtime. Terminal reconciliation may publish sanitized identity, QA, or failure evidence only. Even `pass_qa_only` would not admit a baseline or authorize a difference raster, event interpretation, attribution, derived-pixel publication, or a scientific claim.

## Decision and limits

**Requested choice:** approve, revise, or defer the exact proposal and review bundle as **one conditional envelope through sanitized terminal publication**, without intermediate owner reconfirmation. Approval is effective only after the exact packet and approval pass public CI. If the disposable ArcGIS test fails, the real attempt stays blocked under the same decision; no fallback implementation is silently selected.

This packet remains local and undecided. Preparing it does **not** authorize its Git publication, ArcPy execution, new processing, or any scientific action. The machine-readable proposal is [`contracts/milestone-002-radar-event-area-pair-projection-extent-recovery-001-proposal.json`](../contracts/milestone-002-radar-event-area-pair-projection-extent-recovery-001-proposal.json). Its exact SHA-256 and the review-bundle SHA-256 must be verified before an owner decision is recorded.
