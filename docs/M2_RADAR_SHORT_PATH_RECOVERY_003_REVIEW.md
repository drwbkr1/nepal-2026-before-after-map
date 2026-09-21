# M2 radar short-path recovery-003 review

## Decision

Decide once whether to authorize the complete bounded recovery sequence: publish the reviewed packet, implement and test the short-path correction, require public CI, run one final no-content preflight, execute at most one fresh real attempt, reconcile the terminal result, and publish only sanitized terminal evidence. No intermediate owner reconfirmation would be required inside that unchanged envelope.

## Why a new decision is still necessary

The earlier recovery authority fixed inventory handling and receipt durability, but it expressly prohibited path substitution and any additional real attempt. A new append-only attempt at a different path is therefore a material processing action. Routine coding, tests, CI, evidence recording, and terminal publication are bundled with that one decision rather than split into separate gates.

## Evidence

- Consumed recovery-002 stopped on `M1-SRC-001` at `ApplyOrbitCorrection` with ArcGIS `ERROR 999999` and “The system cannot locate the object specified.” It was not retried.
- The later read-only diagnostic confirmed that ArcGIS Pro 3.7.1 recognizes the copied SAFE directory as a `Folder`, its exact `manifest.safe` as a `RasterDataset`, and M2-ORB-001 as a `File`.
- The failed runner already passed `manifest.safe`, matching Esri’s documented stand-alone example. A folder-to-manifest correction is therefore unsupported.
- The exact failed manifest path contains 260 characters.
- Esri documents a 260-character maximum file-system path length for ArcGIS Pro SAR data. See [Apply Orbit Correction](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-orbit-correction.html) and the [Synthetic aperture radar FAQ](https://pro.arcgis.com/en/pro-app/3.4/help/analysis/image-analyst/synthetic-aperture-radar-faq.htm).

This supports a testable short-path hypothesis. It does not prove the historical failure cause. Success or failure of a later attempt must not be rewritten as proof of the past error’s cause.

## Proposed recovery

The fresh attempt would use the exact new append-only root:

`C:\Projects\Active\nepal-2026-before-after-map-data\r3\a1`

The root is 57 characters. The first copied `manifest.safe` would be 148 characters instead of 260. Exact SAFE directory names and all member bytes remain unchanged. The six sources use fixed one-digit aliases only to shorten their parent directories.

Before any copy or ArcPy import, the runner must project every destination SAFE-member path, declared output path, and attempt-control path from the exact verified inventories. Every path must be no more than 240 characters. A 241-character path stops the attempt terminally before data copying or ArcPy import. No junction, reparse point, `subst` drive, alternate data root, or long-path bypass is permitted.

If the precheck passes, processing retains the six exact sources, four exact orbits, four exact converted DEM tiles, AOI, EPSG:32645 grid, masks, thresholds, registration rules, source order, and route order. The runner stops on the first failure. It never retries.

## Verification before the real attempt

- Portable tests cover the 240/241 boundary, the observed 260-character path, one-to-one source aliases, path traversal and collision refusal, receipt isolation, fixed order, stop-on-failure, and secret/path sanitization.
- An installed ArcGIS runtime test may verify only tool signatures and licenses with disposable inputs. It may not read project data or external custody and may not call `ApplyOrbitCorrection` or another geoprocessing tool.
- Public default-branch CI must pass.
- One final no-content preflight must confirm exact code identities, absence of every new attempt/receipt path, free space, and all public gates.

## Result boundary

A full pass would establish only that all six exact radar sources and both frozen radar routes completed their unchanged QA contracts. It would not establish historical root cause, event-related change, geomorphic interpretation, event attribution, derived-pixel publication authority, or scientific publication authority.

A failure is retained as terminal evidence. The consumed attempt cannot be resumed, reused, deleted, overwritten, or retried.

## Requested single authorization

Approval covers only:

- public packet and implementation publication;
- implementation and bounded reversible correction;
- portable and installed-runtime disposable tests;
- public CI and exact post-CI reconciliation;
- one final no-content preflight;
- at most one fresh short-path real attempt;
- exact terminal reconciliation and sanitized terminal publication.

It authorizes no second attempt, automatic retry, source or scientific-contract substitution, credentials, network requests, installation, baseline admission, change analysis, interpretation, attribution, derived-pixel publication, or scientific publication.
