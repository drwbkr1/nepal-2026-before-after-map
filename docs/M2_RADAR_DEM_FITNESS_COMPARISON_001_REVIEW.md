# M2 radar DEM fitness and controlled GTC comparison-001 review

This is a **local zero-decision proposal** at base commit `dafa082b608b16f630e5378ca8072e76e17078fe`. Proposal SHA-256: `a918f784e4722dfa25ddf8c78b0dc98abab86bd4c2023e439293d4004baebf06`. Preparation releases no Git publication, project-data read, ArcPy call, DEM acquisition, or new attempt.

The no-DEM probe completed, but it changed more than DEM presence relative to recovery-005. It used an ArcPy Raster input, omitted the prior 10 m snap environment, and ran separately. The earlier `ERROR 000425` therefore has no isolated cause. Catalog footprints show possible gaps, not actual valid pixels. [Esri GTC guidance](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-geometric-terrain-correction.html) calls for DEM use on land scenes; [Esri RTF guidance](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-radiometric-terrain-flattening.html) documents NoData outside DEM coverage. [Esri's array-read documentation](https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/rastertonumpyarray-function.html) specifies multiband array shape and block window behavior.

## One proposed owner decision

Approve, revise, or defer one bounded envelope covering packet publication, implementation and synthetic/installed-runtime validation, public CI gates, final no-content preflight, one read-only actual valid-pixel audit, **conditionally one** DEM-supplied GTC call on the exact preserved M1-SRC-001 gamma CRF, durable receipts, reconciliation, and sanitized terminal publication without intermediate reconfirmation. The proposal binds paths, AOI, native-grid validity counts, stop rules, one prospective root, and a quarantined output.

The audit projects AOI geometry to the native input CRS and reads at most 512-by-512 cells per window without resampling input rasters. Ambiguous NoData or grid alignment stops the process before GTC. Positive valid cells in each input on the overview AOI are only a floor for this diagnostic comparison. M1-SRC-001 does not cover the full event source and upper-corridor AOIs, so this does not assess a full scene or baseline. Even if GTC saves a raster, that output cannot be admitted to a map or a scientific claim under this proposal. The fourteen additional DEM catalog cells remain unapproved for acquisition; their need and pixel fitness remain unknown.

No action in this proposal is authorized merely by its preparation. The review asks for one decision on the entire bounded envelope, with no intermediate microapproval.
