# M2 ApplyOrbitCorrection input-resolution diagnostic-001 review

## Review status

This is a local zero-decision review packet. Proposal SHA-256: `bb318432bf3a63f2bb75d2b1ea69716b6fbade9917d7c35ff8388d3edaa41d84`. It is not published, approved, or authorized for implementation.

## Exact observed boundary

Recovery-002 attempt `radar-pixel-orbit-application-recovery-002-real-001` is terminal and consumed. Identity scanning, ArcPy import, the `ArcInfo` product check, both extension checkouts, DEM mosaic creation, and analysis-support creation completed. The first fixed-order source, `M1-SRC-001`, then failed inside `ApplyOrbitCorrection` while bound to `M2-ORB-001`. ArcGIS returned `ERROR 999999`, including “The system cannot locate the object specified.” No later source or route started, no retry occurred, cleanup completed, and external custody remained unchanged.

The frozen runner called `arcpy.ia.ApplyOrbitCorrection` with the copied SAFE's `manifest.safe` path and the exact orbit EOF path. Python-level controls established filesystem presence and identity, but the terminal evidence did not record whether ArcGIS catalog resolution recognized the SAFE directory, `manifest.safe`, the orbit EOF, or which object the error referred to. Historical root cause and recovery readiness remain unestablished.

## Proposed bounded diagnostic

After separate publication, owner approval, implementation, public CI, and final preflight gates, run at most one read-only diagnostic process. It would first establish whether the exact append-only recovery-002 attempt-root candidates for `M1-SRC-001` currently exist, then inspect only any exact candidate found there and exact `M2-ORB-001`. The packet does not claim those external candidates still exist because current project-data access is unauthorized. It would record:

1. Current existence and exact filesystem identities for the attempt-root SAFE candidate, its `manifest.safe` candidate, and the orbit EOF.
2. ArcGIS installation, product, extensions, and `ApplyOrbitCorrection` usage identity.
3. `arcpy.Exists` for the SAFE directory, `manifest.safe`, and orbit EOF.
4. Sanitized `arcpy.Describe` fields only for objects ArcGIS recognizes.

The diagnostic would make zero `ApplyOrbitCorrection` calls, zero geoprocessing calls, zero copies, zero custody mutations, and zero derived rasters. A missing attempt root or candidate would terminate the diagnostic without reconstruction or substitution. A result could describe current filesystem presence and ArcGIS object recognition only. Any path correction or new processing attempt would require another exact review and owner decision.

## Still prohibited

Git publication, public CI, owner approval, implementation, ArcPy invocation, project-data or external-custody access, a diagnostic process, any `ApplyOrbitCorrection` call, any new radar attempt, source or path substitution, baseline admission, change analysis, interpretation, attribution, derived-pixel publication, and scientific publication remain unauthorized.
