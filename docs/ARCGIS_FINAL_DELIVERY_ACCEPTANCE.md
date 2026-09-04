# Final ArcGIS delivery acceptance

## Purpose

The metadata-only ArcGIS package exercise proved one same-machine project-package round trip. It did not define or test the final scientific delivery. `config/qa/arcgis-final-delivery-contract.json` closes that control gap before real change features exist.

The contract is additive and predeclared. It does not change the active M2 checkpoint, authorize data access, admit scientific evidence, complete M6, or authorize public release.

## Required final package

Final M6 acceptance requires an ArcGIS Pro project, File Geodatabase, at least five layer files, one or more analysis GeoTIFFs, an interoperable GeoPackage, a project package, paired PNG/PDF exports for five maps, a complete SHA-256 artifact manifest, and a delivery README.

The five required maps are:

1. regional overview;
2. source-area comparison;
3. upper-corridor comparison;
4. reviewed evidence map;
5. limitations and exclusions map.

Every final layout must visibly include the before/after dates, legend, functioning scale bar, north arrow, EPSG:32645 statement, source credits, limitations, review state, and attribution disclaimer.

## Scientific evidence requirements

The package cannot pass with an empty scientific workspace. Every admitted observation must retain exact before and after source links, acquisition dates, uncertainty, limitations, QA, and owner review. Interpretations must remain linked but distinct from direct observations, while attribution assessments remain a third linked record with their own status and limitation.

Failed, deferred, and inconclusive routes must be reconciled into the delivered evidence history. The evaluator blocks a report that hides them, merges observation with interpretation or attribution, omits visible exclusions, or packages an unregistered or nonprojected result.

## Spatial and portability requirements

All scientific vectors and analysis rasters must report EPSG:32645. Grid metadata, registration QA, and visible exclusion masks are mandatory. The final project package must be extracted, reopened, and re-exported from either a clean machine or clean local profile where the original workspace is absent. Broken sources, operational paths outside the package, unsafe paths, missing artifacts, unverified hashes, and rights conflicts all block acceptance.

## Decision outcomes

- `invalid` means the contract or supplied report is malformed or overclaims publication or emergency authority.
- `block` means a required artifact, evidence relationship, spatial control, source, path, hash, rights, or failure-history condition failed.
- `defer` means scientific evidence, M5 review, clean-environment execution, or visual review is incomplete without proving the delivery invalid.
- `pass_m6_delivery_only` means the final ArcGIS delivery conditions passed. It does not authorize M7 publication or emergency guidance and cannot replace M5 scientific review.

## Current state

Only the portable evaluator and synthetic reports are exercised now. A passing synthetic report proves the decision logic behaves as declared. It is not evidence that real satellite pixels, reviewed change features, final maps, a clean-environment package, or M6 completion exist.
