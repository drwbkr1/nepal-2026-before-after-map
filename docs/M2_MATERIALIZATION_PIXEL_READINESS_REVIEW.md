# M2 materialization and pixel-readiness review

## Decision before the owner

Review exact proposal SHA-256 `3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c` and choose `approve`, `revise`, or `defer` for the single item `M2-MATERIALIZATION-PIXEL-READINESS-001`.

The proposal is inactive. This blank packet contains zero human decisions and authorizes no extraction, implementation, metadata or raster access, or pixel decoding.

## Current evidence

- All eight exact Sentinel archives are promoted and passed container-only verification.
- `M1-SRC-001`, `M1-SRC-002`, and `M1-SRC-003` are already materialized. The unintended-test provenance of `M1-SRC-001` remains explicit.
- Five exact products remain unmaterialized: radar `M1-SRC-004`, `M1-SRC-005`, and `M1-SRC-006`, followed by optical `M1-SRC-010` and `M1-SRC-008`.
- Their container receipts report 198 members and 7,268,266,717 total uncompressed bytes. The read-only preflight found 537,446,526,976 free bytes and no planned path or receipt collision.
- Both failed `M1-SRC-004` partials and all previous acquisition, materialization, input-readiness, and CI failures remain preserved.

The preflight is evidence for review, not execution. Free space, archive identity, and collisions must be checked again immediately before any approved run.

## What approval would authorize

Approval would release one dependency-ordered, fail-closed sequence:

1. Publish the exact activation controls and require successful public CI.
2. Materialize the five named sources once each in the fixed order, using the exact no-replace attempt identities in the proposal. Stop the sequence on the first non-pass and preserve every partial or failed attempt.
3. If all five pass, implement and publish a six-source radar header gate and refreshed two-source optical header gate. Require portable tests, ArcGIS synthetic tests, and successful public CI before one real inspection per route.
4. If the optical header gate passes, implement and publish an optical pixel-readiness runner bound to the existing thresholds. After public CI and a final no-pixel preflight, run it once on `M1-SRC-010` and `M1-SRC-008` for `AOI-OVERVIEW`, `AOI-SOURCE`, and `AOI-UPPER-CORRIDOR`.
5. Record only coverage, conservative mask usability, EPSG:32645 grid compatibility, and registration metrics. Preserve `pass_qa_only`, `defer`, `block`, or `invalid` without retry or threshold changes.

## What approval would not authorize

Approval would not permit new downloads, source or date substitution, credential access, terms acceptance, cost, archive modification, automatic retries, or deletion of any failure. It would not permit radar pixel decoding, orbit recovery or application, DEM vertical conversion, calibration, terrain correction, a radar baseline, an optical change-index baseline, candidate extraction, interpretation, attribution, emergency guidance, raster publication, or a scientific claim.

The 27 August optical scene is high-cloud-risk. A `defer` or `block` is an acceptable terminal result for the exact attempt; another date cannot be substituted under this proposal.

## Decision instructions

Return exactly one completed response for the bound item. Select one allowed decision and attest that it is your completed decision. Notes are optional and limited to 2,000 characters.

- `approve`: authorize only the exact dependency-ordered actions and limits in the proposal.
- `revise`: authorize no execution and request a new exact proposal and review bundle.
- `defer`: leave the five products unmaterialized and perform no new real header or pixel access.

Do not edit the evidence hash or item identity. Codex will lock the returned response before reading the decision and will reconcile only an unambiguous completed payload.
