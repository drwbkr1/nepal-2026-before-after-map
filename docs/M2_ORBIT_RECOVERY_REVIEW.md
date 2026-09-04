# M2 orbit acquisition recovery review

## Decision requested

Decide whether to authorize one fresh, byte-zero recovery of the exact failed `M2-ORB-001` restituted-orbit file after the full Sentinel `M2-VERIFY` unit is complete.

## What happened

A stale regression test expected `M2-ORB-001` to remain blocked because its two bound Sentinel scenes were absent. Both scenes had since been promoted and container-verified, so the test crossed that guard. It used a tracked nonsecret fixture token value, revalidated the exact public catalog object, created append-only attempt events, and made a download request that was rejected. No orbit payload byte was received, staged, or promoted.

The failed attempt is retained as `m2-orb-001-20260904t050937z-8ed21d05`. Its automatic-retry flag is false. The active milestone's full `M2-VERIFY` dependency was still incomplete, so the attempt did not satisfy the complete execution envelope.

## Corrective control

The production runner now requires the active `M2-VERIFY` unit to be complete before any orbit catalog request, token lookup, event write, or payload request. Twenty-nine focused orbit tests pass without changing the retained orbit receipt, event, or custody inventory.

## Approval would authorize only

- implementing and testing a separate recovery path that preserves the failed attempt and events;
- after `M2-VERIFY` is complete, one fresh transfer of the same exact `M2-ORB-001` provider UUID and `AUX_RESORB` filename;
- a new exclusive attempt identity and byte-zero download using the existing protected owner credential reference;
- exact rights, catalog, path, collision, size, MD5, BLAKE3, SHA-256, XML, OSV, validity, and scene-binding checks;
- continuation of only the three still-unattempted approved orbit files after recovery passes and their prerequisites are met.

## Approval would not authorize

- recovery while `M2-VERIFY` remains incomplete;
- deletion, rewriting, hiding, or reuse of the retained attempt or events;
- a synthetic credential value, credential disclosure, terms acceptance, account or MFA changes, or cost;
- a different orbit object or type, repeated retry, or precise-orbit substitution;
- orbit application, radar processing, pixel admission, change mapping, attribution, or scientific publication.

## Decision options

- **Approve:** authorize only the bounded, dependency-gated recovery above.
- **Revise:** return the proposal for changes; no recovery is released.
- **Defer:** retain the current checkpoint and make no orbit transfer.

The review surface is blank by design. A completed decision requires an explicit option and an attestation that the decision is complete.
