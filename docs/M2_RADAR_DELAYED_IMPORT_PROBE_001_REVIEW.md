# M2 radar delayed-import probe-001 review

**Proposal SHA-256:** `7d3474eeed2dd679ca1f755d1ebcf6542b977b87418b40f4b40204ae5ac02de9`  
**Consumed recovery terminal SHA-256:** `3bd2a4cc6bd56d7ec5ae95a316ff3f5b3cc788b94d32436b3cf02586d7a391c0`  
**Decision state:** zero decisions; owner review required

## Why this is proposed

The one authorized radar recovery is terminal and cannot be reused or retried. It completed the full 156-file, 10,367,157,634-byte identity scan and then failed before DEM creation or source processing with `The Product License has not been initialized.` Read-only review narrowed the historical failure to ArcPy import, `overwriteOutput`, Image Analyst checkout, or Spatial checkout. Current product and extension checks pass, the earlier disposable raster test passed, and default local logs contain no relevant failure artifact. The only evidenced sequence difference is delayed ArcPy import after the large scan; that difference is not proven causal.

## Proposed diagnostic

Approval would authorize implementation, portable synthetic tests, public CI, one final no-content preflight, and only on all passes one live probe in one fresh process. The probe would create 156 deterministic sparse files totaling exactly 10,367,157,634 logical bytes in a probe-specific local temporary directory, hash all of them before importing ArcPy, then write and flush durable before-and-after stage markers around each candidate setup statement. It would finish with two tiny disposable rasters and one `MosaicToNewRaster` operation, check the extensions back in, persist one terminal receipt, and record cleanup. It would use no source bytes, source names, project data, external custody, network, token, installation, or UAC action.

## Result limits

A pass would show only that the current host completed this sequence at that time. A block would identify the last durable stage and sanitized exception for this probe. Neither result would prove the historical root cause, establish recovery readiness, release another radar attempt, or change any satellite, orbit, DEM, AOI, CRS, threshold, mask, route, or QA contract.

## Still prohibited

No recovery-001 reuse or retry, project-data access, orbit application, DEM action, radar pixel processing, route evaluation, baseline, change analysis, interpretation, attribution, derived-pixel publication, or scientific claim is authorized by this packet.

## Decision

Choose `approve`, `revise`, or `defer` for this exact proposal and attest that the decision is complete.
