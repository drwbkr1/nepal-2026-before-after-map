# Validation plan

Validation is staged. Passing repository checks does not validate pixels or scientific conclusions.

## Repository validation

`scripts/check_project.py` verifies:

- required charter, status, contract, and control files exist;
- JSON records parse;
- expected identifiers and project paths agree;
- forbidden large geospatial formats and obvious credential files are not tracked.

GitHub Actions runs the same check on pushes and pull requests.

## Source validation

For each external product:

- exact identity and provider are recorded;
- access and rights are reviewed;
- geometry and acquisition timing match the manifest;
- local bytes match the recorded size and checksum;
- expected bands/polarizations are present;
- AOI coverage is inspected at the pixel level;
- accepted, rejected, or deferred status is explicit.

## Spatial validation

- all analytical layers report the intended CRS;
- grid origin, cell size, resampling, and snap raster are documented;
- stable control points or invariant terrain are used to quantify co-registration;
- misregistration tolerance is chosen before change thresholds;
- area and distance measures use projected geometry.

## Optical QA

- cloud, cirrus, shadow, snow/ice, saturation, and nodata masks are inspected;
- each AOI has a valid-pixel fraction;
- spectral deltas are tested on stable reference areas;
- visual interpretations link to source and mask layers.

## Radar QA

- orbit and viewing geometry match within each comparison;
- calibration and terrain-correction settings are recorded;
- layover, shadow, border noise, water variability, and residual speckle are reviewed;
- ascending and descending results are evaluated independently;
- stable reference areas are used to characterize background change.

## Change-feature QA

- every feature has the required evidence attributes;
- confidence criteria are defined before final classification;
- optical/radar agreement and disagreement are represented;
- inconclusive areas remain in the evidence record;
- causal wording requires a separate review decision.

## ArcGIS package QA

- open and export tests succeed from a clean directory;
- no broken sources or undocumented network paths remain;
- layer scales, metadata, credits, and limitations are visible;
- packaged and source manifests reconcile;
- large or licensed artifacts are stored on an approved release surface, not Git.

## Public release QA

Verify repository state, GitHub release assets, public map files, rights notices, scientific wording, and downloadable package independently. A local export or green script alone is not proof of public release.
