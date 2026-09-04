# M2 DEM terrain-result review

## Decision in one sentence

Approve, revise, or defer the exact attempt-003 terrain-screen result as a bounded owner review of gross terrain artifacts and the ArcGIS review surface, without approving vertical-datum processing, independent elevation accuracy, radar processing, or any scientific claim.

**Proposal SHA-256:** `80855c6859a6a78de5712883f604c4f6f7816e459b44638054c3f6a1e848a90c`

## What the result establishes

Attempt-003 ran under thresholds and processing rules published before the terrain values were observed. The result receipt records:

- four of four exact Copernicus GLO-30 tiles passed the fixed finite-value, elevation-range, curvature, and plateau screens;
- four of four native tile seams passed, with the largest absolute residual at 58.1905517578125 metres and no sample above the 100 metre review level;
- the EPSG:32645 output has a 30 metre cell size and retains EGM2008 orthometric elevation values without a vertical transform;
- the AOI slope surface passed, with 0.001807973 percent of finite cells above 85 degrees, below the 0.1 percent defer threshold;
- 189 of 189 stable external artifacts, totaling 520,668,653 bytes, matched the manifest by path, size, and SHA-256 after ArcGIS exited;
- the four source rasters matched their approved custody identities before, after, and during independent post-exit verification;
- the exported PNG and a 180 dpi rendering of the one-page PDF passed the five predeclared model visual criteria.

The exact terrain receipt is `records/surface-receipts/m2-dem-terrain-quality.json`, SHA-256 `9663c261de37c77fd96896d1fbb37c4c3a970c47966661908673db880e640dd7`.

## External ArcGIS artifacts to inspect

The DEM-derived maps and geodatabase remain outside Git. Review these exact local artifacts:

| Artifact | Local path | SHA-256 |
|---|---|---|
| ArcGIS Pro project | `C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-003\Nepal_2026_DEM_Terrain_QA.aprx` | `08829c97eeb831758573fbfc0146f09e5d1a39d342f313f5adab4ba2c6facc83` |
| PDF map | `C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-003\Nepal_2026_DEM_Terrain_QA.pdf` | `139e4a4f0f5a02018c824cbfc2f85ddcf3b1d1c4b8d477dd7936efc4d0f74d0b` |
| PNG map | `C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-003\Nepal_2026_DEM_Terrain_QA.png` | `39c63525171ae7cd24b540577079467c7efbaedb4aae959086e3f4d1a38ad811` |
| Stable-output manifest | `C:\Projects\Active\nepal-2026-before-after-map-data\derived\dem-terrain-quality\attempt-003\derived-output-manifest.json` | `6baf1ec47f4bc27c9dc2ab3501637690d717673e63d9e0f5036e1b2dc2ed1620` |

The public review bundle contains a text-only rendered summary rather than a copy or thumbnail of DEM-derived pixels. The terrain receipt provides the exact second-order binding to these external artifacts.

## What approval means

Approval records that the reviewer examined and accepts the exact terrain-screen result, map surface, and limitations. After the completed response is locked and reconciled, only the human-review gate in the terrain-readiness audit may be reassessed.

Approval does not make the overall audit pass. It does not authorize vertical conversion, coordinate-system component installation, `GEOID` or `NONE`, independent reference-data acquisition, Sentinel transfer or processing, radar-ready promotion, DEM-derived image publication, or scientific interpretation.

## What remains deferred

- the exact EGM2008 vertical-datum route and its owner-controlled installation prerequisite;
- independent elevation accuracy against ground control or another suitable DEM;
- pair-specific Sentinel-1 terrain-correction behavior, layover and shadow masks, and stable-reference registration;
- Sentinel acquisition, container, materialization, header, pixel, mask, coverage, and registration gates;
- satellite-observed change, interpretation, attribution, and emergency guidance.

## How to decide

- **Approve** if the exact terrain-screen result and its limited claim boundary are acceptable.
- **Revise** if the review or presentation needs a specific change. Observed metrics, predeclared thresholds, source identities, and failed attempts will not be rewritten.
- **Defer** if the owner terrain-result review should remain unresolved.

Use the exact blank response generated from the bundle-bound review contract. Do not edit the bundle, proposal, evidence, or contract after the bundle hash is issued.
