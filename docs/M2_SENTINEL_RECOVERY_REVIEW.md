# M2 Sentinel acquisition recovery review

## Decision requested

Decide whether to authorize one fresh, byte-zero retry of the exact failed `M1-SRC-004` Sentinel-1 product through a new exclusive staging identity.

## What happened

Three before-event Sentinel-1 products completed exact-length and provider-MD5 verification, were promoted without replacement, and passed offline ZIP/SAFE container checks. The first after-event product, `M1-SRC-004`, stopped after 561,593,598 of 1,732,332,897 expected bytes with `transferred_size_mismatch`.

The incomplete bytes remain outside Git with SHA-256 `299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66`. They are failure evidence, not an admissible Sentinel product.

## Why the partial will not be resumed

Safe resumption requires verified byte-range support and an unchanged strong remote-object identity from the original response. The failed attempt did not retain both facts. The proposed recovery therefore starts from byte zero in a distinct staging path and leaves the original partial untouched.

## Approval would authorize only

- implementing and testing a separate recovery control that preserves the failed attempt as terminal history;
- one fresh transfer of the same provider UUID and exact product from byte zero;
- current rights, page, catalog, path, collision, length, checksum, and container checks;
- use of the existing protected owner credential reference without recording its value;
- continuation of the four still-unattempted original products only after the recovery passes, stopping on any later failure.

## Approval would not authorize

- resuming, deleting, modifying, renaming, or overwriting the retained partial or its events;
- hiding the failed attempt or reusing its staging path;
- substituting another product, changing the source manifest, or adding imagery;
- accepting terms, changing an account or MFA, incurring cost, or exposing credentials;
- orbit transfer before its dependencies, radar processing, pixel admission, change mapping, attribution, or scientific publication.

## Current evidence boundary

The current intake contains three promoted products, one failed product, and four authorized unattempted products. Three products pass container-only verification. No Sentinel raster readability, AOI coverage, usable-pixel, registration, or scientific result has been established.

## Decision options

- **Approve:** authorize only the bounded recovery and post-success continuation above.
- **Revise:** return the proposal for changes; no transfer is released.
- **Defer:** retain the current checkpoint and make no further Sentinel transfer.

The review surface is blank by design. A completed decision requires an explicit option and an attestation that the decision is complete.
