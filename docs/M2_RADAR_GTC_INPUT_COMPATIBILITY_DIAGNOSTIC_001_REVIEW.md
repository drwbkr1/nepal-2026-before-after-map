# M2 radar GTC input-compatibility diagnostic-001 review

## Review status

This is a local zero-decision packet. Proposal SHA-256: `9506b91f3809b08340b44e8965311088ad7537ff5626ef78a9f5bdad9d841910`. It is not published, approved, or authorized for implementation or data access.

## Exact observed boundary

Recovery-005 attempt `radar-pixel-orbit-application-esri-sequence-recovery-005-real-001` is terminal and consumed. `M1-SRC-001` completed orbit correction, thermal-noise removal, calibration, radiometric terrain flattening, and the approved exact `REFINED_LEE` despeckle. ArcGIS then raised `ERROR 000425` inside gamma `ApplyGeometricTerrainCorrection` before returning a Raster. No GTC output, later source, route, or retry exists.

This establishes a precise call boundary, not its cause. The preserved terminal evidence does not record whether the saved despeckled CRF and terrain-support inputs retain the structural metadata ArcGIS expects at that boundary.

## Proposed single bounded diagnostic envelope

One later approval would cover implementation, synthetic tests, public CI, one final no-content preflight, at most one fresh read-only diagnostic process, reconciliation, and sanitized terminal publication without intermediate owner reconfirmation.

The diagnostic would inspect only the six exact preserved recovery-005 candidates listed in the proposal. It would record filesystem metadata, `arcpy.Exists`, and sanitized `arcpy.Describe` metadata. It would perform zero geoprocessing calls, zero raster-function calls, zero pixel reads, zero network requests, and zero mutations. Missing or unrecognized input terminates the diagnostic without reconstruction or substitution.

The result may characterize current structural and ArcGIS catalog compatibility only. It cannot establish historical root cause, a corrected method, recovery readiness, a usable baseline, change evidence, interpretation, attribution, or a scientific result.

## Current boundary

Preparation changed no canonical checkpoint and accessed no project data. Publication, implementation, ArcPy, external custody, the diagnostic process, another radar-processing attempt, baseline work, change analysis, attribution, and scientific publication remain unauthorized.
