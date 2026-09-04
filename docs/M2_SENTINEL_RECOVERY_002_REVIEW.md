# M2 Sentinel supervised recovery review

## Decision requested

Decide whether to authorize a secret-safe detached-worker implementation and, only after its tests and public CI pass, one fresh byte-zero recovery of the exact failed `M1-SRC-004` Sentinel-1 product.

## What happened

Three before-event Sentinel-1 products remain promoted and container-verified. The original `M1-SRC-004` transfer stopped after 561,593,598 of 1,732,332,897 bytes. Its separately approved byte-zero recovery later stopped after preserving 1,333,788,672 bytes. In that second attempt, both the Python transfer process and the token-entry PowerShell process were observed absent before the runner wrote a terminal event. The cause is unknown, no destination was promoted, and both partials remain failure evidence outside Git.

The previous one-attempt authority is consumed. No retry or further Sentinel transfer is currently authorized.

## Proposed control change

The token-entry console would act only as a broker. It would hand a fresh token through a single-use in-memory process channel to a separate detached supervisor that owns the transfer, heartbeat, and terminal evidence. The token may not appear in a command line, environment variable, file, log, event, heartbeat, or repository record.

Before any real credential or product request, synthetic tests must prove that:

- closing the broker console does not end the detached supervisor;
- the supervisor reaches a terminal success or failure record after broker termination;
- ordinary worker exits create terminal evidence, and an absent worker can be reconciled from nonsecret heartbeat and process-state evidence;
- synthetic credentials do not appear in process metadata, files, logs, events, or Git changes;
- the new path remains exclusive, starts at byte zero without `Range`, refuses redirects and unsafe paths, preserves failures, and promotes only by atomic no-replace;
- the exact implementation commit is public, the remote ref matches, and public CI passes.

The design reduces dependence on a transient console window. Because the earlier cause is not known, it does not claim to prevent every possible process termination.

## Approval would authorize only

- implementing and testing the exact broker and detached-supervisor design;
- publishing that implementation and requiring a successful public-CI gate before a real attempt;
- a final no-payload preflight that rehashes both retained partials and reconfirms the exact source and absent destination;
- one fresh transfer of the same provider UUID and exact product from byte zero into the new `m1-src-004-recovery-002` namespace;
- use of a fresh owner-controlled token only through the tested in-memory handoff;
- current rights, catalog, path, interruption, length, checksum, and ZIP/SAFE controls;
- continuation of only the four still-unattempted original products after recovery success, stopping on any later failure.

## Approval would not authorize

- resuming, deleting, modifying, renaming, or overwriting either retained partial or prior evidence;
- reuse of either prior staging path, concealment of either failure, or more than one recovery-002 attempt;
- storing a token in a command line, environment variable, file, log, event, heartbeat, or repository record;
- product substitution, source-manifest changes, or added imagery;
- terms acceptance, account or MFA changes, cost, or credential disclosure;
- orbit transfer outside its own gate, radar processing, pixel admission, change mapping, attribution, or scientific publication.

## Current evidence boundary

The active intake still contains three promoted products, one failed source, and four authorized unattempted products. Two incomplete `M1-SRC-004` byte streams are retained and are not admissible products. No Sentinel raster readability, AOI coverage, usable-pixel, registration, or scientific result has been established.

## Decision options

- **Approve:** authorize only the implementation, tests, public-CI gate, one fresh recovery-002 attempt, and success-only continuation described above.
- **Revise:** return the proposal for changes; no implementation or transfer is released.
- **Defer:** preserve the current checkpoint and perform no further Sentinel transfer.

The review surface is blank by design. A completed decision requires an explicit option and an attestation that the decision is complete.
