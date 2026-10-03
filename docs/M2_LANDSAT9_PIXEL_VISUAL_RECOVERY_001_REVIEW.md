# M2 Landsat-9 pixel and visual-panel recovery-001 — local review

**Status: zero decision, local only.** This packet has not been approved or published. Preparing it did not open a promoted TAR, extract a member, read a TIFF header or pixel, invoke ArcPy, create a new map, or touch the consumed attempt.

## What the last attempt established

The approved [pixel and visual-panel method](../contracts/milestone-002-landsat9-pixel-visual-panel-001-proposal.json) passed portable tests, an installed ArcGIS Pro disposable test, public CI, and a final no-content preflight. The single real invocation then created `real-001` and returned a sanitized unexpected-failure code. The directory remains **empty**: it has no started or terminal receipt, materialized member, TIFF/header result, pixel result, or panel. Its precise exception was not retained. Three later disposable write probes succeeded, but they do **not** explain the failure or make `real-001` reusable. The [terminal evidence](../records/readiness/m2-landsat9-pixel-visual-panel-001-terminal-reconciliation.json) and [post-CI closure](../records/readiness/m2-landsat9-pixel-visual-panel-001-post-ci-reconciliation.json) make that one-shot attempt terminal.

The two exact 10 and 26 August 2026 Landsat-9 Level-2 TARs remain promoted in non-Git **container-only local QA custody**. Neither scene has passed TIFF header or pixel QA. There is no Landsat raster panel and no observed-change result from this pair.

## One proposed recovery decision

The [proposal](../contracts/milestone-002-landsat9-pixel-visual-recovery-001-proposal.json) preserves the old directory, frozen source identities, approved projected AOIs, and all scientific mask, threshold, grid, band, and stretch rules. It adds a separate supervisor receipt **before** worker launch and an independent fallback path, with fixed, secret-safe stage codes. A durable failure record is required even if the worker stops after making a directory. This is an evidence-persistence correction; it does not claim a known root cause.

One approval would cover the source-safe packet and implementation, interruption and receipt-failure synthetic tests, installed ArcGIS disposable validation, public CI, final no-content preflight, and **at most one distinct `real-002` worker** over the same two exact archives. The worker would read only the ten already reviewed members per scene in the fixed before/after order, stop on the first failed gate, and perform no automatic retry. If measured paired coverage reaches the unchanged visual floor, it could create one owner-local EPSG:32645 ArcGIS Pro APRX with PNG/PDF exports and verify a fresh-process reopen. If coverage or another gate fails, it would retain the evidence and make no panel claim. The approval would also cover sanitized terminal publication, without another intermediate reconfirmation.

This proposal allows **no new download or account action**, no modification of `real-001`, no source or scientific-method substitution, no difference raster or mapped change, no event attribution, and no public derived-pixel or scientific publication. Passing synthetic tests or seeing an attractive image would not establish a usable Landsat comparison in advance.

## Decision

Approve, revise, or defer the **single conditional envelope** in the exact proposal and local review bundle. The previous approval cannot authorize `real-002` because its one-shot budget was consumed and publicly closed. This packet asks for one new decision at that actual boundary, not separate decisions for each implementation or validation step.
