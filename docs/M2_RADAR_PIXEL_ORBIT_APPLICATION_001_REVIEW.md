# M2 radar pixel readiness and orbit application review 001

## Decision

Choose **approve**, **revise**, or **defer** for proposal `3a0f03c5269f4e3e6822c1e31bbe5f19cd288e9e17db67b42990d96b27a4f490`. Approval must be an attested owner decision bound to the exact public review-bundle hash.

## Established inputs

Six exact Sentinel-1 GRD products pass custody, materialization, and header-only readiness. Four exact S1D `AUX_RESORB` files pass offline identity and structure verification. Four exact EGM2008-corrected WGS 84 ellipsoidal DEM derivatives pass conversion verification. ArcGIS Pro 3.7.1 exposes the required SAR tool signatures.

These facts establish input identity and capability only. No Sentinel-1 measurement pixels have been decoded, no external orbit has been applied, and no terrain-corrected radar candidate exists.

## Readiness audit

The current decision is `DEFER`: source rights, provenance, route independence, and evaluation design pass, while real pixel schema behavior, masked AOI coverage, exclusions, registration, exact-pipeline reproducibility, and this owner decision are unresolved. The proposal is designed to generate that missing evidence without changing the frozen QA rules.

## What approval would release

Approval releases a dependency-ordered route: exact implementation and synthetic/ArcGIS tests; successful public CI; one final no-content preflight; one versioned orbit-application and QA-processing attempt per exact Sentinel-1 source in fixed order; then one independent QA evaluation per ascending and descending route. Execution failures stop the source sequence. A valid route `BLOCK` or `DEFER` remains evidence and does not suppress evaluation of the independent route.

Every real output remains outside Git in a fresh, non-overwriting attempt. Original Sentinel, orbit, and DEM custody must remain unchanged.

## What remains prohibited

No source, date, orbit, DEM, vertical relation, AOI, CRS, grid, threshold, mask, stable-control, or route substitution. No automatic retry, overwrite, token, network, installation, precise-orbit claim, baseline admission, change product, cross-route synthesis, interpretation, attribution, derived-pixel publication, or scientific claim.

## Decision meaning

A later `PASS_QA_ONLY` may establish measured coverage, masking, grid, seam, and registration fitness. It cannot establish a baseline, observable event change, geomorphic interpretation, or attribution.
