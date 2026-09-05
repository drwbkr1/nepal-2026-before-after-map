# M2 optical pixel recovery 001 review

## Decision

Choose **approve**, **revise**, or **defer** for proposal `96f0125628e894061fc5da55faff94e92e51b0385293576177c1e15bd009b3da`. Approval must be an attested owner decision bound to the review bundle hash generated with this package.

## What happened

The single authorized real attempt is terminal `INVALID`. It read the first real SCL raster, then stopped before classification because the runner expected `xmin` at the top of the grid object while the production contract stores it under `analysis_grid.extent`. It created no QA raster or metrics file.

## What approval would release

Only the code correction, exact production-shape tests, fresh public CI, a no-pixel preflight, one new append-only recovery attempt, and reconciliation described in the proposal. The pair, AOIs, masks, 20 m grid, thresholds, and decision semantics remain unchanged.

## What remains prohibited

No reuse or retry of real-001, automatic retry, source substitution, radar pixels, spectral indices, baseline, change analysis, interpretation, attribution, or publication.
