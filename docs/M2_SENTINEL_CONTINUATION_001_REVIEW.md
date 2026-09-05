# M2 Sentinel continuation review

## Decision requested

Decide whether to authorize a corrected continuation-only detached worker and, only after its tests and public CI pass, one bounded attempt for each of the four exact Sentinel products that have never been attempted.

## What completed

The approved `M1-SRC-004` recovery-002 transfer succeeded from byte zero. The resulting 1,732,332,897-byte archive has local SHA-256 `a606cac063cc23e60a623f020192fc097d327f3dafadf1115802b2a458eaceab`, matches the provider MD5, and passed the existing ZIP/SAFE container-only verification. Both earlier failed partials remain unchanged. The active intake now records `M1-SRC-004` as satisfied only through the successful recovery-002 identity.

This establishes four promoted and container-verified products. It does not establish readable rasters, usable AOI pixels, registration, change, or scientific fitness.

## Where the run stopped

After the recovery and container check passed, the detached supervisor entered `continuation_live_preflight` and wrote a terminal failure with code `unexpected_supervisor_failure`. It stopped before any `M1-SRC-005` attempt, staging directory, event directory, destination, or payload request existed. `M1-SRC-005`, `M1-SRC-006`, `M1-SRC-008`, and `M1-SRC-010` remain authorized and unattempted.

The supervisor did not retain a safe underlying exception category. The exact cause is therefore unknown. A later successful read-only source check cannot prove what failed at the terminal time.

## Proposed correction

The new worker would be continuation-only: it cannot invoke the `M1-SRC-004` recovery path. It would accept one fresh owner token through the same single-use in-memory broker boundary and process only these exact source IDs in this order:

1. `M1-SRC-005`
2. `M1-SRC-006`
3. `M1-SRC-008`
4. `M1-SRC-010`

Before any real credential or payload request, synthetic tests must prove the exact allowlist and order, one-attempt ceiling, stop-on-first-failure behavior, secret exclusion, safe error classification, exclusive staging, byte-zero requests without `Range`, redirect refusal, path containment, checksum and length verification, atomic no-replace promotion, and container gating. The exact implementation must then be public on `origin/main` with successful public CI.

For future failures, approved acquisition-control exceptions would retain only their existing nonsecret code. Unexpected exceptions would remain generic and may not write exception text, tracebacks, credentials, or credential-bearing URLs.

## Approval would authorize only

- the continuation-only implementation and synthetic tests;
- exact publication and public-CI verification before activation;
- a final no-payload preflight and one fresh token handoff through the tested anonymous pipe;
- at most one attempt for each of the four named products, in the fixed order;
- current legal, source-identity, path, byte-zero, length, MD5, SHA-256, atomic-promotion, and ZIP/SAFE controls;
- continuation to the next named product only after the current product has passed transfer and container verification;
- exact intake reconciliation if the receipts pass.

## Approval would not authorize

- another `M1-SRC-004` transfer, retry, replacement, deletion, or mutation;
- resume or reuse of any partial, staging path, attempt, event, receipt, or supervisor identity;
- token storage in process arguments, environment variables, files, logs, records, events, exception messages, or tracebacks;
- retrying a continuation source or continuing after a failure;
- substitute or additional products, source-manifest changes, terms acceptance, account changes, MFA changes, cost, or credential disclosure;
- orbit or DEM acquisition, SAFE extraction, pixel decoding, baseline processing, terrain correction, change mapping, attribution, or scientific publication.

## Decision options

- **Approve:** authorize only the correction, tests, public-CI gate, final preflight, and four-source one-attempt continuation described above.
- **Revise:** return the proposal for changes; no implementation or transfer is released.
- **Defer:** preserve the current four-of-eight checkpoint and make no additional Sentinel request.

The review surface is blank by design. A completed decision requires an explicit option and an attestation that the decision is complete.
