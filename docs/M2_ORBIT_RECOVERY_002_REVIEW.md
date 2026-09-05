# M2 orbit recovery-002 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `d30208c07deb66ef2c7487f8c901abd4fb5ff04aa56766bca8066d4c8d4f0db8`. A completed decision must bind the exact review-bundle hash and include the owner's attestation.

## Corrected prerequisite

The approved radar-first control amendment now binds the six exact Sentinel-1 sources to verified custody, materialization identity, and passing header readiness. This replaces the stale aggregate `M2-VERIFY` prerequisite for the independent radar route. It does not establish pixel usability or a baseline.

## Exact recovery under review

The review concerns only one future fresh byte-zero attempt for `M2-ORB-001`, UUID `d4fdc474-0069-459b-9534-b5999dec5aab`, named `S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF`. The prior attempt and its zero-byte failure remain immutable evidence.

Approval would release a separately tested recovery-only implementation, successful public CI, one final no-payload preflight, and at most one exact recovery attempt through the owner-controlled anonymous token broker. Any failure is terminal for that new identity.

## Still prohibited

No request for `M2-ORB-002` through `004`; no automatic retry or precise-orbit substitution; no DEM action, orbit application, radar pixel decoding, baseline, change analysis, attribution, or scientific publication. The two DEM reviews and any future radar pixel-readiness review remain separate.
