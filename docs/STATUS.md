# Current status

- **State:** M1 complete; M2 active at the authentication-reference boundary
- **Last completed milestone:** M1 — Event geometry and source manifest
- **Active milestone:** M2 — Controlled acquisition and baseline
- **Scientific result:** None
- **Imagery custody:** Empty external custody structure initialized; zero products downloaded
- **Long-term goal:** Active
- **Checkpoint:** `M2-AUTHENTICATION-REFERENCE`

## Purpose

This project is building a reproducible, ArcGIS-ready before/after evidence package for the 26 August 2026 Nepal debris avalanche and flash flood. Its public repository preserves source identity, authority, methods, decisions, and lightweight receipts. Heavy imagery and derived geospatial data remain outside Git.

## Completed foundations

- three owner-approved study areas are projected to EPSG:32645 and validated in ArcGIS Pro 3.7.1;
- the owner-approved source manifest preserves ten exact Sentinel candidates, with eight accepted for controlled acquisition and two optical context products deferred;
- the ArcGIS evidence workspace separates observation, interpretation, attribution, exclusions, controls, and QA, with scientific layers empty by design;
- fixed pixel-readiness rules cover AOI coverage, optical masks, radar masks, grid alignment, and registration before real product access;
- portable and ArcGIS-native synthetic tests exercise pass, block, and defer outcomes without creating a real-pixel claim;
- three independent candidate pair routes are predeclared: ascending radar, descending radar, and RUM optical.

## M2 activation and live preflight

The owner approved review bundle SHA-256 `e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d` and acquisition-plan SHA-256 `6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d`. The exact completed response was locked and reconciled before `contracts/milestone-002.json` became active.

At `2026-09-03T17:31:17Z`, the non-mutating live preflight:

- re-fetched the official CDSE OData, token, terms, and Sentinel Legal Notice pages;
- confirmed all eight exact product UUIDs, names, catalog sizes, provider MD5/BLAKE3 values, and online states;
- passed all 64 required source criteria using 120 evidence items, including 80 live items;
- found 514.942 GiB free against the 60 GiB minimum;
- verified that the approved external root was absent, outside Git, collision-free, and free of reparse-point ancestors;
- read no credential values, performed no authentication, and transferred no product bytes.

The approved structure at `C:\Projects\Active\nepal-2026-before-after-map-data` was then created with custody and staging children. The repository and external initialization receipts match at SHA-256 `12812d1c53e13ec287425f74a1988f5c0be7d0638f856c9606fddf1c1431fb09`.

## Current gate

Preflight found no `CDSE_ACCESS_TOKEN`, username, or password reference in the process environment. No login was attempted. Before the first exact-product transfer, the workflow requires a secret-safe reference to an existing owner-controlled CDSE access token or authenticated session.

Do not place a token, password, cookie, refresh value, or authorization header in chat, Git, a filename, a receipt, or captured command output. Stop if login, MFA, recovery, or terms acceptance needs owner action.

## Authorized but not completed

- authenticate through an existing owner-controlled CDSE credential or session reference;
- download only the eight exact approved products, one at a time;
- preserve append-only attempts and use collision-safe staging and promotion;
- verify exact bytes, provider checksums, ZIP safety, SAFE identity, and required content;
- inspect real pixels, masks, AOI coverage, baselines, and EPSG:32645 registration.

## Outside the active authority or still unproven

- accepting new or changed provider terms;
- creating or recovering an account or changing account security;
- disclosing credentials or using a paid route;
- downloading products outside the exact eight;
- using or redistributing restricted high-resolution imagery;
- repository-license selection;
- usable-pixel, change, interpretation, attribution, or emergency-guidance conclusions;
- storing archives, SAFE products, rasters, geodatabases, or ArcGIS packages in Git.

Catalog metadata and the live source gate establish eligibility for controlled acquisition only. They do not establish transferred-byte integrity, pixel usability, scientific fitness, or event causation.
