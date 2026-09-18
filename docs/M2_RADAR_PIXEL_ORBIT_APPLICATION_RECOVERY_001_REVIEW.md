# M2 radar inventory-normalization recovery-001 review

**Proposal SHA-256:** `cacda42d4eba2d60f3725bf2933fa00ea5ede6f33e6fed4133ca4d3e1476cd04`
**Terminal reconciliation SHA-256:** `5696ab1542b386260eff7b3c0591891abe0a907c4c62342e4aa411abd9b73300`
**Decision state:** zero decisions; owner review required

## Terminal evidence

Real-001 is consumed. It stopped on the first `M1-SRC-001` identity guard before source processing. The diagnostic confirms 26 expected and 26 actual files, no additions or omissions, and zero size or SHA-256 differences after projection and sorting. Direct list equality failed because manifest entries include `zip_crc32` and archive order while the runtime inventory uses three fields and case-insensitive path order.

## Proposed bounded recovery

Approval would authorize one exact comparator correction: project both inventories to `relative_path`, `size_bytes`, and `sha256`, reject duplicates or any byte-identity difference, then sort case-insensitively before equality. It would also move identity verification under durable terminal-error handling, add synthetic and ArcGIS-safe tests, require public CI and one final no-content preflight, and only then allow one fresh recovery-001 attempt with the same six sources and two routes in the same order.

## Unchanged restrictions

Real-001 cannot be retried or reused. No source, orbit, DEM, AOI, CRS, threshold, mask, or route substitution is proposed. No network or credential action, baseline admission, change analysis, interpretation, attribution, derived-pixel publication, or scientific claim is authorized.

## Decision

Choose `approve`, `revise`, or `defer` for the exact proposal above and attest that the decision is complete.
