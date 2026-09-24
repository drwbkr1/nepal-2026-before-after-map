# Map-oriented route review after native-GTC recovery-003

**Status:** Local zero-decision preparation. This note grants no publication, data access, ArcPy execution, source/date change, new radar attempt, or scientific admission.

## What changed

The owner-approved recovery-003 kept the ascending M1-SRC-002/005 pair and tried one bounded grid method before any new SAR attempt. Generated-raster ArcGIS tests showed that clearing four inherited grid settings can be restored and that a small categorical mask keeps its classes under nearest-neighbor projection. Those mechanics do not test SAR-specific terrain correction. The broad generated fixture then projected to 83,107,486 cells in EPSG:32645, but its bounds extended 950–1,550 m beyond the frozen target. The approved limit was 100 m per side. The method stopped at the disposable gate; e1/a2, real-data DEM assessment, source QA, registration, baseline admission, and change analysis did not start. [Terminal evidence](../records/readiness/m2-radar-event-area-pair-native-gtc-grid-recovery-003-disposable-terminal-reconciliation.json)

Esri's [Extent environment documentation](https://pro.arcgis.com/en/pro-app/3.3/tool-reference/environment-settings/output-extent.htm) says the extent selects input data for processing and does not itself clip the output to that rectangle. This is consistent with the disposable overshoot; the experiment does not prove which internal ArcGIS step produced it. Esri's [Clip Raster documentation](https://pro.arcgis.com/en/pro-app/3.4/tool-reference/data-management/clip.htm) distinguishes pixel-preserving input alignment from `MAINTAIN_EXTENT`, which adjusts rows/columns and resamples. A new method must make that tradeoff explicit and measure it on generated continuous and categorical rasters before a SAR attempt.

## Route implications

| Route | Map potential | Current obstacle |
| --- | --- | --- |
| Ascending radar M1-SRC-002/005 | Best existing catalog overlap for both event AOIs and a same-orbit before/after candidate. | The previous real GTC result is unusably coarse. Recovery-003 has not tested SAR GTC; its single approved projection method failed the disposable target-extent guard. A different method requires new review. |
| Descending radar M1-SRC-003/006 | Independent source-area perspective. | Catalog coverage of the upper corridor is only partial, and the same GTC/grid uncertainty remains. It cannot silently replace a complete event-area pair. |
| Existing optical pair | Independent spectral observation if usable. | The frozen real optical results are INVALID/BLOCK. Preserve them; no retry or substituted date is authorized. |
| New optical search | Could provide a more direct path to an ArcGIS before/after layer if a comparable low-cloud scene exists. | Requires a new bounded source, rights, timing, and pixel-fitness review before acquisition or analysis. Availability and usability are unknown. |

## Recommended next decision design

Prepare one **map-route feasibility packet**, not another isolated diagnostic approval. It should compare a coverage-verified `ProjectRaster` then aligned `Clip` candidate and a bounded alternate optical *metadata* search against the same map deliverable: exact EPSG:32645 coverage of the approved AOIs, source dates, exclusion masks, real pixel QA, registration, exportable ArcGIS layers, and uncertainty. The new candidate differs from the closed Clip test by requiring the projected intermediate to cover every frozen target boundary before clipping; recovery-003's generated intermediate did, while the old Clip intermediate missed the west edge by 900 m. That geometric contrast supports a new disposable test, not a method pass. A descending source-only layer may be considered separately, labeled as incomplete upper-corridor coverage. Do not infer that any candidate will work from these disposable results.

The decision packet should request one coherent conditional envelope, with independent gates and stop-on-failure behavior, rather than repeated owner confirmations for unchanged work. It must not authorize baseline admission, change detection, geomorphic interpretation, attribution, derived-pixel publication, or scientific publication until real pixels and the frozen QA contract support those later stages.
