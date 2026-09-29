# M2 Landsat-9 MTL identity diagnostic-001 — local review

**Status: zero decision, local only.** This packet has not been published or approved. Preparing it did not reopen the terminal archive, inspect MTL bytes, change custody, or click EarthExplorer.

## Why the Landsat route stopped

The approved [local-download recovery-001 terminal reconciliation](../records/readiness/m2-landsat9-local-download-recovery-001-terminal-reconciliation.json) records a clean public-CI gate and no-payload preflight. Both existing 10 August files had matching full SHA-256 digests, and one 1,126,565,376-byte copy was staged under a new attempt. The frozen verifier then returned `mtl_text_identity_mismatch`. The attempt is terminal and consumed; the copy was retained outside Git, neither Downloads original was altered, and no file was promoted. The 26 August request never started. [Post-CI reconciliation](../records/readiness/m2-landsat9-local-download-recovery-001-post-ci-reconciliation.json) closes that envelope.

The failure code does not identify which text-MTL key was missing, repeated, malformed, or different. It does not prove the archive is the intended scene or prove that the parser is wrong. [USGS documents](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products) both ODL-based MTL text and XML metadata for Collection 2 Level-2 products; their existence is a reason to compare the two bounded identity representations, not to weaken the frozen identity check.

## One proposed decision

Approve, revise, or defer the exact [diagnostic-only proposal](../contracts/milestone-002-landsat9-mtl-identity-diagnostic-001-proposal.json) and review bundle. One approval would cover its dependency-ordered packet publication, secret-safe implementation and disposable tests, public CI, final no-content preflight, **at most one distinct read-only process** over the exact retained staging file, and sanitized terminal publication without another confirmation while the frozen conditions hold.

That process would first rehash all staged bytes and require the terminal SHA-256 and length. Only on a match would it inspect TAR headers and read the exact product-named `_MTL.txt` and `_MTL.xml` members, each capped at 2 MiB. It would classify presence, syntax, and exact equality for `LANDSAT_PRODUCT_ID` and `LANDSAT_SCENE_ID`; only syntactically valid allowlisted IDs may appear in receipts. It would read no TIFF payload or pixel, write no extracted data, and use a new append-only diagnostic identity. Any mismatch, ambiguity, changed bytes, or receipt failure stops. The [risk screen](../records/readiness/m2-landsat9-mtl-identity-diagnostic-001-risk-screen-local.json) records the remaining provenance and source-fitness limits.

The diagnostic cannot itself authorize a parser correction, acceptance of another scene, custody promotion, a retry, or the 26 August download. Those would require a later evidence-bound decision. No ArcGIS raster map, change analysis, interpretation, attribution, or scientific publication is released.

## Review outcome needed

An approval must name the exact proposal and bundle SHA-256 values after the local bundle is finalized. This local draft grants **zero** access, implementation, publication, or real diagnostic authority on its own.
