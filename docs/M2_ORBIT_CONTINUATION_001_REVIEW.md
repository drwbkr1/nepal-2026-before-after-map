# M2 orbit continuation-001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `01a2c3521625f8f219909b8d69476dbc3355292ff12e59fd0917ed52bc371e8b`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Current state

Exact `M2-ORB-001` is promoted, input-only verified, and preserved alongside its failed attempts and recovery staging bytes. `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` remain the same exact `AUX_RESORB` identities approved in the original orbit amendment, but none has an attempt, staged byte, or custody file. The current M2-ORB-001 amendment authorizes no request for them.

## Exact continuation under review

Approval would authorize a continuation-only implementation for those three identities in fixed order: `M2-ORB-002`, then `M2-ORB-003`, then `M2-ORB-004`. After synthetic proof, successful public CI, and a final no-payload preflight, the owner could initiate one secret-safe handoff. Each source could receive at most one byte-zero request. The sequence would stop on the first failure and preserve all prior successes, failures, partials, events, and staging paths.

The review also proposes applying the same maximum one-second OSV endpoint-consistency rule prospectively to only those three files. This is declared before their payload bytes or OSV timestamps are observed. All checksum, identity, XML, OSV ordering, units, scene-margin, custody, and no-replace rules remain unchanged.

## Still prohibited

No request or retry for `M2-ORB-001`; no second request or automatic retry for a failed remaining source; no source, date, order, identity, threshold, or orbit-type substitution; no tolerance above one second; no credential exposure or storage; no terms acceptance, account action, or cost; and no orbit application, DEM action, radar-pixel decoding, baseline, change analysis, attribution, or scientific publication.
