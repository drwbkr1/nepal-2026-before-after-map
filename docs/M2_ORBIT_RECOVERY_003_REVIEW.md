# M2 orbit recovery-003 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `5aa4a0042024634a7ade191e0c5f36614216d8581a9c0535c0042be20583bfa3`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Terminal recovery-002 outcome

The secret-safe owner handoff launched supervisor `m2-orbit-recovery-002-20260906t172858z-42bace7e`. The exact public catalog revalidation returned and the new payload-parent directory was created, but the supervisor stopped before an attempt event root, attempt ID, active-intake mutation, authenticated download request, destination, or payload byte. The safe journal recorded `orbit_recovery_002_supervisor_unexpected_failure`; it did not retain exception text or the catalog response hash. Those facts remain unknown.

Recovery-002 is consumed because its approved failure policy made any failure terminal for that identity and prohibited automatic retry.

## Exact recovery-003 under review

Approval would release only a new recovery implementation for the same exact `M2-ORB-001` product. It would predeclare the attempt identity, create event storage before the payload parent, persist a separate catalog-revalidation event, map pretransfer stages to fixed nonsecret codes, use a distinct recovery-003 staging root, pass public CI, and pass a fresh no-payload preflight. The owner could then initiate one secret-safe handoff and at most one byte-zero download request.

## Still prohibited

No request for `M2-ORB-002` through `004`; no deletion, reuse, or rewriting of prior evidence; no automatic retry or precise-orbit substitution; no DEM action, orbit application, radar pixel decoding, baseline, change analysis, attribution, or scientific publication. The independent DEM and future radar-pixel gates remain unresolved.
