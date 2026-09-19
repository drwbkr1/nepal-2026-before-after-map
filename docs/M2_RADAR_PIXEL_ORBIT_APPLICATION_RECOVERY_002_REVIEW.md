# M2 radar pixel and orbit application recovery-002 review

**Proposal SHA-256:** `86366bca8681bbe90dfdd19d6c5b676e490e6dd87c8e04c2900e9fb1df4b29ca`  
**Consumed radar terminal SHA-256:** `3bd2a4cc6bd56d7ec5ae95a316ff3f5b3cc788b94d32436b3cf02586d7a391c0`  
**Disposable probe outcome SHA-256:** `7d7028afdca5b880b2d4d1da69d404db72adf3b5210234cb2a88403c541696b3`  
**Decision state:** zero decisions; prepared locally; publication is not authorized

## Evidence reviewed

The exact `recovery-001` radar attempt is terminal and consumed. It verified the six source inventories, four orbit files, and four DEM derivatives, then stopped during ArcGIS setup with `The Product License has not been initialized.` before the first source-processing receipt. The durable record does not identify the exact failing ArcPy statement. No route evaluation or derived raster began.

A later, separately controlled disposable probe reproduced the observed sequence difference without project data: it fully hashed 156 files totaling 10,367,157,634 logical bytes before ArcPy import, matched aggregate SHA-256 `dd56f8b28a1ed1c6e2b4b1d7d8f5db4fd86dab80a910fe79c8d018d58942430b`, reported `ArcInfo`, checked out Image Analyst and Spatial Analyst, created two disposable rasters and one mosaic, persisted terminal and cleanup receipts, and removed all payload children.

That pass is evidence that the installed runtime completed the delayed-import disposable sequence on the current host at that later time. It does not establish the earlier failure's cause, prove project-data processing, or establish radar recovery readiness.

## Proposed bounded recovery-002

The proposed implementation would preserve both consumed attempts and all existing scientific contracts. It would create a new recovery-002 wrapper around the unchanged strict recovery-001 inventory comparator and base radar-processing functions. Before any project-data content read, it would reserve the new attempt, terminal and cleanup identities, a durable stage journal, and an append-only fallback journal.

Durable markers would surround the exact identity scan, delayed ArcPy import, product query, extension checkouts, DEM mosaic, analysis-support creation, every fixed-order source, both fixed-order routes, postattempt identity verification, terminal persistence, and cleanup. The first sanitized failure would be appended before ordinary terminal construction; later persistence failures could not replace it, and cleanup would run independently.

After separate packet-publication authority, successful public CI, exact attested owner approval, bounded implementation and synthetic validation, successful implementation CI, and one final no-content preflight, the project could run at most one fresh attempt: `radar-pixel-orbit-application-recovery-002-real-001`. It would use the same six sources `M1-SRC-001, M1-SRC-002, M1-SRC-003, M1-SRC-004, M1-SRC-005, M1-SRC-006` and routes `PAIR-S1-ASC-R085-IW, PAIR-S1-DESC-R121-IW` in the unchanged order, with no substitution or automatic retry.

## Claim and release limits

A pass would establish only that the exact radar input-processing and two frozen QA routes completed for later owner review. It would not admit a baseline or authorize change analysis. A block would identify the new attempt's durable boundary only. Neither outcome would establish the historical root cause, causal attribution, or a scientific result.

The current authority permits only local packet preparation and validation. It does not permit Git publication, public CI, implementation, ArcPy, project-data or external-custody access, a new attempt, radar processing, baseline or change analysis, attribution, or scientific publication.

The next required decision is whether to commit and publish this exact zero-decision packet and run public default-branch CI. The later `approve`, `revise`, or `defer` proposal decision remains closed until that public gate passes.
