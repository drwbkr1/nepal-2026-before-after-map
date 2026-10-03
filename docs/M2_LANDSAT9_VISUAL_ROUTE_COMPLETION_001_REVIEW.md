# M2 Landsat-9 remaining visual route — local review

**Local proposal only; no decision or execution is released.** The [recovery-001 terminal record](../records/readiness/m2-landsat9-pixel-visual-recovery-001-terminal-reconciliation.json) and [public closure](../records/readiness/m2-landsat9-pixel-visual-recovery-001-post-ci-reconciliation.json) establish that the single new worker stopped in the August 10 metadata parser. Ten exact members were materialized and verified; no TIFF header, pixel, August 26 processing, or Landsat map ran. Durable supervisor, worker, and cleanup receipts exist. Both earlier attempts remain consumed and immutable.

## The concrete correction

The existing parser flattens every matching metadata line into one dictionary. It includes structural `GROUP` declarations and cannot distinguish repeated field names belonging to different groups. The official [USGS file format](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1328_Landsat8-9_OLI-TIRS-C2-L2_DFCB-v7.pdf) and [science guide](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1619_Landsat8-9-Collection2-Level2-Science-Product-Guide-v6.pdf) place acquisition date/time in `IMAGE_ATTRIBUTES` and surface-reflectance coefficients in `LEVEL2_SURFACE_REFLECTANCE_PARAMETERS`. Level-1 rescaling has its own coefficients. The exact field that caused this attempt's stop was not recorded; this is a code-and-format diagnosis, not a new inspection of source metadata.

The [proposal](../contracts/milestone-002-landsat9-visual-route-completion-001-proposal.json) selects fields by their complete group path and requires ODL/XML agreement. It retains the existing product identities, dates, Level-2 scale and offset, 30 m EPSG:32645 grid, AOIs, masks, coverage criteria, and display stretch. Missing or duplicate required groups/fields and wrong coefficients still stop. A bounded metadata-only audit of both exact sources comes before new TIFF or pixel work.

## One approval through the route outcome

Approval covers packet publication and CI, implementation and realistic nested-metadata tests, disposable ArcGIS validation, the metadata audit, fresh append-only processing, a conditional local APRX/PNG/PDF panel and rendered/reopen checks, and sanitized terminal publication. It also covers necessary recovery from specifically classified mechanical defects while the exact sources and scientific predicates stay fixed. Each consumed attempt remains separate and preserved. After two failures without progress, an internal evidence review is required before further work. Unclassified failure, source-integrity drift, or failed scientific QA stops the route. This replaces repeated approval requests for routine receipt, parser, timestamp, path, or interface repairs with one explicit outcome-scoped decision.

A map is produced only if an approved AOI reaches both 99% footprint coverage and the unchanged 20% paired-valid visual floor. Partial areas carry their measured limitations; residual registration remains unmeasured. The proposal permits no new source or download, credential action, source overwrite, changed threshold or mask, mapped change, attribution, public derived pixels, or scientific publication.

## Decision

Approve, revise, or defer the exact local bundle and proposal as one conditional remaining-route envelope. The prior approval cannot release this correction or another content-processing attempt: it expressly allowed at most one worker and no retry, and that worker has been consumed and publicly closed. This request comes from that explicit project boundary, rather than from a skill or an intermediate checkpoint.
