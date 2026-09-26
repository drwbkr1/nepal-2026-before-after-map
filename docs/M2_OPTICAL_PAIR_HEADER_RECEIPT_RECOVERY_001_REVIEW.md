# M2 optical pair header-receipt recovery-001 review

**Status:** Local zero-decision review. The original optical pilot is terminal. This packet does not release publication, another ArcGIS process, project-data access, or pixel decoding. The [exact proposal](../contracts/milestone-002-optical-pair-header-receipt-recovery-001-proposal.json) asks for one conditional decision covering publication through terminal reconciliation, without intermediate owner reconfirmation.

## What happened

The exact 24 August S2A and 16 September S2B T45RUM products were each acquired once, passed their provider size, MD5 and BLAKE3 checks and ZIP CRC, and were materialized into non-Git custody. The first archive has SHA-256 `b8050b4aaaacc2014c8b5dbec7fca8738c8be74f2cf9d65df7dda089ac5114e8`; the second has SHA-256 `0c201b7196b87a9efd79deb5a4c5a5cab6e45cce7e3d2d7bce593c9b3368a1ae`. The approved ArcGIS worker was invoked after materialization but stopped without writing the header receipt. Its exit code and failing statement were not retained. No pixel-QA attempt began. [Terminal reconciliation](../records/readiness/m2-optical-pair-pilot-001-terminal-reconciliation.json) · [public CI reconciliation](../records/readiness/m2-optical-pair-pilot-001-terminal-publication-reconciliation.json)

The [read-only static review](../records/observations/m2-optical-pair-header-stop-static-review-001.json) finds an observability gap: the parent discards child output and does not persist the exit code when the header receipt is missing; the child writes its header receipt only after both product inspections. The evidence does not identify whether the child failed at import, authorization, source verification, metadata inspection, raster description, or receipt persistence. A later successful process would not establish the original failure cause.

## Proposed one-decision recovery

The proposal would first add a distinct offline worker with parent-reserved start, phase, terminal, and cleanup receipts, including safe exit/error codes but no raw errors, paths, credentials, or pixels. Portable and installed ArcGIS tests would use only disposable generated inputs. After public CI and a final offline exact-identity preflight, **at most one new append-only process** could read the two already materialized products without changing them. It would run the frozen header checks in before-then-after order. Only a passing new header receipt could release **at most one new pair pixel-QA attempt** under the unchanged EPSG:32645 20 m grid, masks, coverage and registration rules. Any failure stops; there is no automatic retry or source acquisition.

This route still targets localized source and upper-corridor QA. One T45RUM tile per date cannot prove full regional overview coverage. A `PASS_QA_ONLY` result would establish neither baseline admission nor event change; a blocked or indeterminate result stays visible. No difference raster, interpretation, attribution, derived-pixel publication, or scientific claim is included.

**Decision after review:** approve, revise, or defer the exact proposal and hash-bound bundle as one conditional envelope. Until then, the verified archives remain in custody and the original terminal attempt stays closed.
