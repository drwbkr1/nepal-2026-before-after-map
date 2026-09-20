# M2 ApplyOrbitCorrection input-resolution diagnostic receipt-persistence recovery-001

## Review status

This is a **local zero-decision review packet**. It has not been staged, committed, published, or validated by public CI. The owner proposal response is closed. Human decision count: **0**.

## What happened

The one authorized read-only diagnostic process `radar-apply-orbit-correction-input-resolution-diagnostic-001-real-001` was started and is consumed. Before external reads, the runner exclusively reserved its terminal and cleanup receipt identities. Both files remain exactly zero bytes with SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

After the ArcGIS phase was initiated, the process reached ordinary terminal construction and failed at `completed_at_utc = now_utc()`. ArcPy had rebound the runner's module-level `datetime` name, producing `AttributeError: module 'datetime' has no attribute 'now'`. The process exited with code 1.

No terminal JSON, cleanup JSON, filesystem observations, or ArcGIS catalog-recognition observations survived. The current input-resolution result is therefore **indeterminate**. This packet does not reconstruct a missing pass, block, candidate presence result, or catalog-recognition result.

## Preserved evidence

- Failure observation: `records/readiness/m2-radar-apply-orbit-correction-input-resolution-diagnostic-001-terminal-receipt-persistence-failure-observation.json`
- Failure observation SHA-256: `e342c0e0c5301d9eee9aa0ce6492fdc9560de96d4001ed47884c54e43396ab17`
- Final preflight SHA-256: `70a8005d3646b06a5d205c829362a2556a77d0ba37901545aed3ffca3ef956a8`
- Original runner SHA-256: `34239fb9669559f1668887c89b08db5f7e213cfea3132ef0eeb3dffebd041d8f`
- Reserved terminal and cleanup SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` each

The consumed attempt, original public implementation, public gates, final preflight, and both reserved receipts remain unchanged.

## Proposed future correction

The proposed recovery would create a **distinct** attempt `radar-apply-orbit-correction-input-resolution-diagnostic-receipt-persistence-recovery-001-real-001`. It would change receipt durability only:

1. Use function-local datetime-module imports for every timestamp.
2. Reserve new terminal and cleanup identities and initialize an append-only fallback journal before any external read.
3. Persist a sanitized original exception before normal terminal assembly.
4. Append later persistence errors without replacing the original error.
5. Record cleanup independently from ordinary terminal serialization.
6. Preserve the exact candidate identities, read-only ArcGIS call set, check order, sanitization, and zero-geoprocessing rule.

The proposed future process would inspect only the same exact SAFE directory, `manifest.safe`, and M2-ORB-001 EOF already frozen by the approved diagnostic contract. It would make no path, source, orbit, DEM, AOI, CRS, threshold, registration, route, or scientific-predicate substitution.

## Result limits

A later passing recovery could establish only current filesystem presence and ArcGIS catalog recognition or nonrecognition for those exact paths at that time. It would not establish the historical ApplyOrbitCorrection failure cause, a corrected ApplyOrbitCorrection call, radar recovery readiness, usable radar pixels, baseline admission, change, interpretation, attribution, or a scientific result.

## Current authority and next gate

The current authorization permits only local packet preparation, rendering, and validation. It authorizes no Git staging, commit, push, public CI, owner proposal response, implementation, ArcPy invocation, project-data or external-custody access, new diagnostic process, retry, reconstruction, receipt mutation, geoprocessing, radar processing, or scientific action.

The next gate is a separate owner authorization to publish this exact zero-decision packet and run public default-branch CI. Only after that public gate may the owner review the proposal as `approve`, `revise`, or `defer` with an attestation.
