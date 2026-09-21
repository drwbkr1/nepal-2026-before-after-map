# M2 radar raster-function call-shape recovery-004 review

## Decision

Approve one bounded authority envelope for proposal SHA-256 bee3b46d05bf671b8b6657ee12629dfeaa5f04a9adce40bd0593823a664429ed.

One approval would cover local packet publication, implementation, reversible corrections inside the exact scope, portable tests, installed ArcGIS signature-only validation, public CI gates, one final no-content preflight, at most one fresh real attempt, terminal reconciliation, and sanitized terminal publication. No intermediate owner reconfirmation would be required while the evidence, inputs, parameters, and scope remain unchanged.

## Why this packet exists

Short-path recovery-003 is terminal and consumed. Its path projection passed with 269 paths and a maximum of 237 characters. ArcGIS initialized, both extensions checked out, the DEM mosaic and support data were created, and the M1-SRC-001 orbit-correction call returned. The next call failed with: RemoveThermalNoise takes from 1 to 2 positional arguments but 3 were given.

A read-only inspection of ArcGIS Pro 3.7.1 shows ApplyOrbitCorrection is an in-place tool, while the other five arcpy.ia interfaces return Raster objects and omit output paths from their Python signatures. The frozen recovery-specific module supplied output paths to all five Raster-returning interfaces. Correcting only the first call would likely expose the same interface mismatch later, so this packet reviews the complete installed-interface correction once.

## Exact correction

The implementation may change only the recovery-specific processing module and its new recovery-004 orchestration:

- keep ApplyOrbitCorrection unchanged;
- call each Raster-returning function with the installed argument order and no output-path positional argument;
- require the returned object to expose save;
- save it exactly once to the predeclared absent output;
- require the output to exist after saving;
- persist before and after stage markers for every exact tool call;
- stop on the first failed call, source, or route, with no retry.

The source products, dates, orbit files, DEMs, AOIs, EPSG:32645 grid, masks, thresholds, registration method, source order, route order, and scientific predicates remain frozen.

## Attempt boundary

The only proposed production attempt is radar-pixel-orbit-application-raster-function-recovery-004-real-001 at C:\Projects\Active\nepal-2026-before-after-map-data\r4\a1. It uses exact M1-SRC-001 through M1-SRC-006, then the exact ascending and descending routes. Maximum attempts is one. Automatic retry, overwrite, network, and credential actions are prohibited.

The consumed recovery-001, recovery-002, and recovery-003 attempts and receipts remain immutable.

## Evidence and limits

The installed signature audit SHA-256 is fb7ebc9d4f62e855cdce8ef4cec2fe9bb8fcbb6220f4d4a0bda62877fa9b1eae. It invoked no ArcPy processing function, checked out no extension, read no project or external-custody data, made no network request, and created no production attempt.

Recovery-003 shows the shortened path allowed the M1-SRC-001 orbit-correction call to return, but it does not establish why recovery-002 failed. A recovery-004 pass would establish only that the six-source and two-route QA pipeline completed under the frozen contracts. It would not establish event-related change, geomorphic interpretation, attribution, or publication-ready science.

## Approval effect

Approval authorizes the exact combined envelope described above and nothing outside it. Changed inputs or parameters, credentials, network actions, installation, retry, a second attempt, baseline admission, change analysis, attribution, derived-pixel publication, and scientific publication remain separately gated.
