# M2 Sentinel-1 input-readiness label amendment review

## Decision requested

Decide whether to authorize a one-field, post-observation correction to the Sentinel-1 GRD input-readiness contract. The current real result remains **BLOCK** and will not be edited, reclassified, or rerun.

## Exact evidence

| Evidence | SHA-256 |
|---|---|
| Amendment proposal | `ebdcb763afd99ea23090c9bd83fd9e9cb6cb8dfbb2b5fed60edb80f1fa61c731` |
| Official-source gate | `0bf61ef4d72444bcba3bd753fe15511cdebc87288d0d4dfeda9a9bbaeaeb2daf` |
| Failed real-001 receipt | `feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c` |
| Failed-result reconciliation | `5e4f703b938f9adaf10a6f37ec5195d1e1fc426197ffa1fa6a712ba0cb4de0a6` |

The exact predeclared gate was published as commit `87aa2610f1a89fe2d612f9cdd6cb88e63e833c8d` and passed public CI run `33905019294` before the real inspection. Its reconciliation was published as commit `05202620b96bd0f712949246dc89bb8ef42b9542` and passed public CI run `33905584334`.

## What failed

All three required-member inventories passed. Six annotations parsed with the correct mission, GRD/IW identity, acquisition times, polarizations, orbit numbers and directions, and finite ordered embedded vectors bracketing each acquisition. ArcGIS Pro 3.7.1 opened all six one-band U16 TIFF headers, whose dimensions matched their annotations. No pixels were decoded and the external attempt inventories remained unchanged.

Every source still blocked because both VV and VH annotations report `pixelValue` as `Detected`, while the frozen contract required `AMPLITUDE`.

## What the official specification says

The current official [Sentinel-1 Product Specification](https://sentiwiki.copernicus.eu/__attachments/1673968/S1-RS-MDA-52-7441-Sentinel-1-Product-Specification-2025-3.16.3.pdf) defines `pixelValueType` as `Complex` or `Detected` and defines the image-information field as `Detected` or `Complex`. The PDF filename and internal issue text differ; the source gate retains both identifiers instead of silently normalizing them.

The official [Sentinel-1 processing page](https://sentiwiki.copernicus.eu/web/s1-processing) describes GRD products as detected and says their pixels represent detected amplitude. `Detected` is therefore the XML schema label; “detected amplitude” is the physical interpretation.

## Approval would authorize only

- preserving the current contract, failed real-001 receipt, reconciliation, commits, CI runs, and prepublication history unchanged;
- creating a new versioned contract that changes `metadata_checks.pixel_value` from `AMPLITUDE` to `Detected` and binds the official-source review;
- changing the portable validator to read that expected label from the new contract, with focused tests that accept `Detected` and reject `AMPLITUDE`;
- running synthetic ArcGIS validation only under new identities and preserving every attempt;
- publishing the amended gate and requiring successful public CI for its exact commit;
- after that CI succeeds, performing one read-only inspection of the same three exact materialized sources to a new no-replace real-002 receipt;
- reconciling the exact pass or block without retry or further threshold changes.

## Approval would not authorize

- deleting, rewriting, hiding, or reclassifying real-001;
- any additional Sentinel acquisition or either pending recovery action;
- orbit acquisition, application, or substitution;
- DEM vertical transformation or terrain-result approval;
- measurement-pixel decoding, calibration, terrain correction, registration, baseline generation, change analysis, attribution, or scientific publication;
- new sources, product substitution, account or terms action, credential disclosure, cost, or redistribution of the official documents.

## Known limitation

This is a post-observation correction and is expected to clear the already observed label mismatch. A later real-002 pass would therefore confirm implementation against the same inputs; it would not be a blind or independent validation. Even a pass could establish only partial pre-event header readiness and would release no pixel or baseline work.

## Decision options

- **Approve:** authorize only the bounded amendment, validation, publication, one real-002 run, and reconciliation described above.
- **Revise:** return the proposal for changes; no amendment action is released.
- **Defer:** preserve the current BLOCK and take no amendment action.

The review surface is blank by design. A completed decision requires an explicit option and an attestation that the decision is complete.
