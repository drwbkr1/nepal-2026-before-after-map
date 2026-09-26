# M2 optical GDAL header and pixel recovery-002 review

**Status:** Local zero-decision proposal after the [native-GTC radar recovery-003 terminal block](../records/readiness/m2-radar-event-area-pair-native-gtc-grid-recovery-003-terminal-publication-reconciliation.json). The approved radar recovery-003 packet has already stopped at its disposable projected-extent guard; it is not an active alternative or reusable approval. This document and its proposal authorize no Git publication, project-data read, new real attempt, baseline, change analysis, or scientific claim.

## Decision in one envelope

Choose whether to approve, revise, or defer **one GDAL-only header and conditional pixel-QA method** for the exact acquired Sentinel-2 pair M2-OPT-001/002. If approved, the [proposal](../contracts/milestone-002-optical-gdal-header-pixel-recovery-002-proposal.json) would cover exact packet and response publication, implementation, portable and installed-runtime disposable parity tests, public CI and final no-pixel gates, at most one fresh offline real process, and sanitized terminal publication without intermediate owner reconfirmation. It would not approve a new date or source, another attempt after failure, radar activation, baseline admission, change analysis, interpretation, attribution, or derived-pixel publication.

## Why this is an alternative

The exact 24 August S2A and 16 September S2B T45RUM archives and their 95-file materializations each passed identity checks at the [last no-pixel preflight](../records/readiness/m2-optical-pair-header-receipt-recovery-001-final-preflight.json). The original optical pilot and its distinct header recovery are both terminal. Recovery-001's child exited after `arcpy-import-started`, without a header or pixel receipt; its cause is unknown. Neither attempt shows whether the source-area or upper-corridor pixels are clear or registered. [Terminal reconciliation](../records/readiness/m2-optical-pair-header-receipt-recovery-001-post-ci-reconciliation.json)

Two [source-free GDAL checks](M2_OPTICAL_GDAL_READER_FEASIBILITY_LOCAL_001.md) show that the installed ArcGIS Pro Python environment can decode generated Sentinel-style JP2 headers and a sparse three-band JP2 mask, and resample that mask exactly to the frozen 4,726 × 3,950 EPSG:32645 grid. They do not open either acquired product, measure its decoding cost, prove XML scaling, cloud clearance, AOI coverage, or registration, or diagnose the ArcPy exit. The proposed new worker would omit ArcPy at the real-data stage but must demonstrate equivalent decisions under the *unchanged* frozen header, SCL/quality-mask, coverage, and B11 registration predicates using generated inputs before any protected read. A separate new source-binding record would name M2-OPT-001/002 without rewriting old M1-SRC-010/008 outcomes. [Existing pair contract](../contracts/m2-optical-pair-pilot-001-execution.json)

## Fixed order and stops

The two verified materializations would be read only. After portable tests, an installed-runtime synthetic parity test, public implementation and execution CI, and a final no-pixel identity and resource preflight, one fresh process could evaluate M2-OPT-001 first and M2-OPT-002 second. It must persist reserved start, terminal, and cleanup evidence even if the child stops early. Header checks must pass for both before pixel decoding. Pixel QA then evaluates AOI-SOURCE, AOI-UPPER-CORRIDOR, and AOI-OVERVIEW separately; the single T45RUM tile cannot be presented as full overview coverage. Missing CRS equivalence, mask semantics, source identity, receipts, or memory bounds stop the process. A failed or indeterminate stage ends the envelope with no automatic retry.

The catalog lists 50.97% tile-wide cloud for the before product and 55.42% for the after product. These percentages do **not** tell us the clear fraction at either event AOI. A real result may be `INVALID`, `BLOCK`, `DEFER`, or localized `PASS_QA_ONLY`. Even a QA pass would still need baseline admission and a separately authorized change analysis before an observed-change map. [Pair assessment](../records/observations/m2-optical-pair-pilot-001-assessment.json) · [Frozen pixel QA](../config/qa/pixel-readiness-contract.json)

## Route comparison

| Candidate | Strength now | Main unresolved condition |
| --- | --- | --- |
| Ascending radar M1-SRC-002/005 | Both catalog footprints cover the source and upper corridor. | The saved GTC output was a 2 × 2 coarse grid. The approved native-GTC recovery-003 stopped at a [disposable projected-extent guard](../records/readiness/m2-radar-event-area-pair-native-gtc-grid-recovery-003-disposable-terminal-reconciliation.json) before another real attempt. A different method needs a new review; actual DEM support and usable pixels remain unproven. |
| Acquired optical M2-OPT-001/002 | Exact archives and materializations exist, and source-free GDAL JP2 mechanics pass. | No real header or pixel result exists; event-AOI cloud, snow, coverage, registration, and memory behavior remain unknown. |

Neither route is presently a scientific before/after observation. The radar recovery-003 packet is already consumed; it cannot be selected again. The owner can approve this exact optical packet, request preparation of a different radar method, or defer. The attached optical review bundle remains blank and unattested until an actual decision is given.
