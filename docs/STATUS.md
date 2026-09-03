# Current status

- **State:** M1 complete; M2 active with independent Sentinel authentication and DEM acquisition checkpoints
- **Last completed milestone:** M1 — Event geometry and source manifest
- **Active milestone:** M2 — Controlled acquisition and baseline
- **Scientific result:** None
- **Imagery custody:** Empty external custody structure initialized; zero products downloaded
- **Long-term goal:** Active
- **Checkpoints:** `M2-AUTHENTICATION-REFERENCE`; parallel `M2-DEM-ACQUISITION`

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

The owner approved review bundle SHA-256 `e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d` and acquisition-plan SHA-256 `6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d`. The exact completed response was locked and reconciled before `contracts/milestone-002.json` became active. The control profile now maps the approved custody preflight and eight-product acquisition units directly to that exact activation record, eliminating the generic under-gating lint without broadening authority.

At `2026-09-03T17:31:17Z`, the non-mutating live preflight:

- re-fetched the official CDSE OData, token, terms, and Sentinel Legal Notice pages;
- confirmed all eight exact product UUIDs, names, catalog sizes, provider MD5/BLAKE3 values, and online states;
- passed all 64 required source criteria using 120 evidence items, including 80 live items;
- found 514.942 GiB free against the 60 GiB minimum;
- verified that the approved external root was absent, outside Git, collision-free, and free of reparse-point ancestors;
- read no credential values, performed no authentication, and transferred no product bytes.

The approved structure at `C:\Projects\Active\nepal-2026-before-after-map-data` was then created with custody and staging children. The repository and external initialization receipts match at SHA-256 `12812d1c53e13ec287425f74a1988f5c0be7d0638f856c9606fddf1c1431fb09`.

The one-product transfer runner is prepared and locally verified. Eleven tests pass for secret-reference refusal before mutation, exclusive staging, streamed SHA-256 and provider-MD5 checks, size/checksum failure preservation, redirect refusal, path containment, receipt no-replacement, terminal failed-attempt history, and atomic hard-link promotion. Readiness receipt `records/acquisition/transfer-runner-readiness.json` explicitly records zero network requests, zero authentication, zero product bytes, and no active-intake mutation.

The activation-time active intake is now retained at `records/acquisition/active-intake-initial-snapshot.json` with SHA-256 `a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c`. The repository no longer mistakes that historical identity for the permanently current mutable intake. A separate read-only validator and nine tests verify exact immutable product identity, append-only authorized/staging/failed/promoted transitions, terminal receipt bindings, secret exclusion, and optional external-path and promoted-byte reconciliation. The live external check passes with eight authorized products, zero attempts, and no custody files.

Checkpoint derivation is also explicit and read-only. Validated state counts map to `M2-AUTHENTICATION-REFERENCE`, `M2-ACQUISITION-IN-PROGRESS`, `M2-ACQUISITION-REVIEW`, or `M2-CONTAINER-VERIFICATION`; inconsistent counts stop. The tool can write review candidates only beneath ignored `scratch/`, refuses replacement, and does not change tracked controls. Nine focused tests and the current live external derivation pass at the authentication-reference checkpoint.

The exact eight-product offline verification contract is now active under the same M2 approval. Its wrapper requires a promoted active-intake identity and successful-transfer receipt before it reads an archive. It performs no network request or extraction and cannot establish pixel usability. Five active-contract and wrapper tests pass; activation read zero product bytes.

## Current gate

Preflight found no `CDSE_ACCESS_TOKEN`, username, or password reference in the process environment. No login was attempted. Before the first exact-product transfer, the workflow requires a secret-safe reference to an existing owner-controlled CDSE access token or authenticated session.

Do not place a token, password, cookie, refresh value, or authorization header in chat, Git, a filename, a receipt, or captured command output. Stop if login, MFA, recovery, or terms acceptance needs owner action.

## Parallel DEM amendment

ArcGIS Pro 3.7.1 Image Analyst exposes the intended Sentinel-1 radiometric and geometric terrain-correction tools, and their installed usage signatures accept or require a DEM. The active M2 approval contains only the eight exact Sentinel products, so elevation data cannot be added silently.

A metadata-only review found four exact Copernicus DEM GLO-30 COG tiles whose 1° footprints cover the approved AOI union. All four official STAC items and anonymous AWS object HEAD requests returned successfully; the remote total is 170,302,058 bytes (162.413 MiB). No payload byte was requested, no account or authentication was used, and no DEM pixel was examined.

The owner approved review bundle SHA-256 `caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e`, amendment proposal SHA-256 `92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69`, and accepted license document SHA-256 `9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd`. The exact completed response was locked and reconciled before the amendment was activated. Approval is limited to the four named tiles, their fresh anonymous no-cost preflight and acquisition, non-Git custody, verification, and the already bounded radar-processing use.

At `2026-09-03T20:48:10Z`, the fresh preflight re-fetched the license and matched its exact approved SHA-256, revalidated all four official STAC identities, and matched all four anonymous object byte lengths, ETags, Last-Modified values, content types, and `Accept-Ranges` headers without redirects, accounts, credentials, requester charges, or payload bytes. Its source gate passes 40 required criteria with 76 evidence items. The path check found 519.029 GiB free, no reparse points, and no destination or staging collisions.

The empty DEM custody and staging directories were initialized outside Git at `2026-09-03T20:50:33Z`, with matching local/external receipt SHA-256 `31d1b814d8da753dd2335f3110a49107df3f7a6c75875154a0fff0338b7e80a0`. `contracts/m2-dem-intake.json` still has four authorized, unattempted assets, and `contracts/m2-dem-offline-verification.json` remains gate-deferred until promoted rasters exist. The next parallel checkpoint is `M2-DEM-ACQUISITION`; only one exact tile may be staged, hashed, and promoted per attempt. The separate Sentinel CDSE checkpoint remains unchanged.

The candidate controls remain immutable historical evidence. The production radar chain remains deferred on two explicit dependencies: EGM2008 orthometric DEM heights do not exactly match ArcGIS's documented EGM96 geoid correction, and updated Sentinel orbit files are separate auxiliary products outside current authority. Approval does not resolve either scientific dependency.

## Prepared optical baseline controls

The exact Sentinel-2C-before and Sentinel-2B-after RUM route now has a deterministic processing contract. It requires internal baseline 05.12 metadata, band-specific BOA offsets, the product quantification value, DN-zero handling, conservative SCL and quality exclusions, a fixed 20 m EPSG:32645 grid, and independent stable-control measurement before any cross-platform normalization. Fifteen portable tests and an ArcGIS Pro 3.7.1 Spatial Analyst run pass. The ArcGIS run used only a 16-by-16 synthetic fixture and passed five reflectance-band plus three index checks. It did not access external custody or read real metadata or pixels.

The real optical route remains **DEFER**. Neither archive is in verified custody; AOI coverage, masks, registration, and cross-platform bias are unmeasured; and the post-event catalog cloud estimate is 78.471315 percent. An inconclusive optical route must be retained rather than tuned or silently replaced.

## Prepared SAFE materialization controls

The exact eight-product route now has an offline, gate-deferred materialization contract and runner. A product must be promoted in the active intake and have one matching `pass_container_only` container receipt before the runner reads custody. The archive is re-hashed, its full member namespace is revalidated for Windows and cross-platform safety, and every extracted file is recorded in an external SHA-256 manifest under one exclusive append-only attempt.

Fourteen synthetic tests pass, including traversal, ambiguous components, backslash, Windows reserved-name and alternate-data-stream, case-collision, file/directory-collision, symbolic-link, attempt-collision, receipt-collision, and production pre-custody refusal checks. No external materialization directory exists, no real archive was read, and no raster or pixel claim was created.

## Prepared optical input-readiness gate

The exact materialized RUM pair now has a separate gate before pixel processing. It requires two passing materialization receipts, revalidates each external manifest and complete marker, re-hashes the ten selected SAFE members, parses the Level-2A baseline and scaling fields, and uses ArcGIS to inspect native JP2 headers. A pass is limited to header readability and can advance only to pixel, mask, coverage, and registration QA.

The first published input-readiness checkpoint was superseded after official Sentinel-2 documentation showed that PB 05.12 `MSK_CLASSI_B00.jp2` is a three-band 60 m Boolean mask, not the one-band 20 m mask used in that fixture. The correction preserves the published attempt and does not claim anything about real product bytes.

Twelve portable tests and the corrected ArcGIS Pro 3.7.1 Advanced run pass. ArcGIS opens sixteen synthetic JP2 rasters with matching EPSG:32645 10 m and 20 m scientific grids plus a three-band 60 m classification-quality grid; a deliberate 10 m shift of the complete after grid blocks with sixteen extent mismatches. Two failed direct `CopyRaster` JP2-generation attempts, five superseded prepublication passes, and the superseded published pass remain recorded. No real materialization receipt, SAFE metadata, raster header, or pixel was accessed.

Checkpoint derivation is also portable. Repository-only tests do not require the operator's external Windows custody roots; external custody reconciliation remains an explicit local, read-only validation. Failed GitHub Actions run `33800916326` is retained in the append-only portability-correction evidence that records this boundary fix.

## Authorized but not completed

- authenticate through an existing owner-controlled CDSE credential or session reference;
- download only the eight exact approved products, one at a time;
- preserve append-only attempts and use collision-safe staging and promotion;
- verify exact bytes, provider checksums, ZIP safety, SAFE identity, and required content;
- inspect real pixels, masks, AOI coverage, baselines, and EPSG:32645 registration.
- acquire and verify only the four exact approved GLO-30 tiles, one at a time, under the passing DEM preflight and empty-custody receipt.

## Outside the active authority or still unproven

- accepting new or changed provider terms;
- creating or recovering an account or changing account security;
- disclosing credentials or using a paid route;
- downloading products outside the exact eight;
- changing the accepted Copernicus WorldDEM-30 license, using a different route, or acquiring any DEM tile outside the exact approved four;
- using or redistributing restricted high-resolution imagery;
- repository-license selection;
- usable-pixel, change, interpretation, attribution, or emergency-guidance conclusions;
- storing archives, SAFE products, rasters, geodatabases, or ArcGIS packages in Git.

Catalog metadata and the live source gate establish eligibility for controlled acquisition only. They do not establish transferred-byte integrity, pixel usability, scientific fitness, or event causation.
