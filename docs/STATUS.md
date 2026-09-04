# Current status

- **State:** M1 complete; M2 active with independent Sentinel authentication and DEM vertical-datum review checkpoints
- **Last completed milestone:** M1 — Event geometry and source manifest
- **Active milestone:** M2 — Controlled acquisition and baseline
- **Scientific result:** None
- **Imagery custody:** Four exact Copernicus DEM GLO-30 tiles promoted and structurally verified outside Git; the eight Sentinel products remain unattempted
- **Long-term goal:** Active
- **Checkpoints:** `M2-AUTHENTICATION-REFERENCE`; parallel `M2-DEM-VERTICAL-DATUM-REVIEW`

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

The empty DEM custody and staging directories were initialized outside Git at `2026-09-03T20:50:33Z`, with matching local/external receipt SHA-256 `31d1b814d8da753dd2335f3110a49107df3f7a6c75875154a0fff0338b7e80a0`. The four approved tiles were then acquired sequentially with a fresh anonymous `HEAD` check before each transfer, exclusive staging, exact-length verification, local SHA-256, and atomic no-replace promotion. The promoted hashes are `66ae02e02fff0bcc1455717c1a5d6199c5ad3d00f96a1a94c10b74f3301d122a`, `5a0ec09cda62bcacfccacae0724e6493bee8f3f6fe11fb0ef47ccf3fa3716194`, `4df89793d0dc6373deb9c27536a1d7039ec4a9962a699a2312f57c935fbbe6dc`, and `1590255a0ae7e8c1f49b277e287032a18a2e32c8e13c4c3298ed458f851cd3c7`. No credential or account was used. All four append-only transfer attempts and reconciliation checkpoints are retained, no transfer failed, and the separate Sentinel CDSE checkpoint remains unchanged.

The anonymous one-tile transfer runner passes seven local fixture tests for exact remote identity, redirects and requester charges, exclusive staging, streamed SHA-256 and size, partial retention, and the absence of credential handling. Readiness receipt SHA-256 `515b692ac4717540d5347a518a6f8ea47625939c11ca92fc264133d960b92337` records no network request, intake mutation, external custody mutation, or payload byte during that validation.

Two ArcGIS GeoTIFF attempts for `M2-DEM-001` are retained as **FAIL** wrapper results. Both passed exact promoted size and SHA-256 and left the before/after custody inventories unchanged. The first used an unsupported `GetRasterProperties` value, `NODATAVALUE`; after that correction, the second exposed that the COG contains no precomputed ArcGIS statistics. Neither establishes a DEM data defect. The corrected read-only route uses `arcpy.Raster.noDataValue` and `arcpy.RasterToNumPyArray`, without writing source statistics or sidecars.

ArcGIS Pro 3.7.1 then passed one append-only receipt for each exact tile: the corrected third attempt for `M2-DEM-001` and first attempts for `M2-DEM-002` through `M2-DEM-004`. Each is a 3600-by-3600, single-band F32 raster in EPSG:4326 with an exact promoted SHA-256 and unchanged custody inventory. Full-raster scanning found 51,840,000 finite non-NoData cells and zero NoData or nonfinite cells. Because every approved AOI bound lies within the continuous four-tile footprint, structural fitness and valid AOI coverage pass. Summary SHA-256 `97f6a66daccd236decc6cdaac7035ca4cafb541ce7d82cecf08973ec6962f7ef` advances the parallel checkpoint to `M2-DEM-VERTICAL-DATUM-REVIEW`.

The candidate controls remain immutable historical evidence. Full-tile finite coverage does not establish freedom from void-fill artifacts, seams, anomalous terrain, or suitability for terrain correction. The production radar chain remains deferred on two explicit dependencies: EGM2008 orthometric DEM heights do not exactly match ArcGIS's documented EGM96 geoid correction, and updated Sentinel orbit files are separate auxiliary products outside current authority. Approval does not resolve either scientific dependency.

An exact vertical-datum review packet is ready. Official ArcGIS documentation supports an EGM2008 one-minute transformation through the optional ArcGIS Coordinate Systems Data `world1x1_vert` component. Local ArcGIS Pro 3.7.1 inspection found the built-in EGM96 grid but no `Dataset_egm2008-1.grd` or usable EGM2008 transformation over the approved AOIs. Proposal SHA-256 `bdaa7f9e10840d41c9bc47d65b33bbee3f71e82fe7862069ff1129785047f065` recommends converting verified copies to WGS 84 ellipsoidal height and then using `NONE`; bundle SHA-256 `9b40e81df766ea866c5bff51cdbc4d83e7e7da6a554fb1709fc553d8221bebbc` contains zero human decisions. My Esri sign-in, license acceptance, component download or installation, and UAC remain owner-controlled and are not authorized by the packet.

An independent terrain-quality gate is predeclared before real terrain metrics. Contract SHA-256 `fdee6dbaaafee7c010c7ef77fe6d7121164686f4b26edcb8ca8f0d150d1d1fa2` binds the four exact promoted hashes, four native seam pairs, fixed artifact and slope thresholds, a 30 metre EPSG:32645 map, one exclusive external output attempt, and mandatory visual review. The route preserves EGM2008 orthometric values with no vertical transform and permits no Sentinel processing or DEM-derived raster publication. Five synthetic decision tests pass; no real DEM pixel, derived output, terrain conclusion, vertical-datum decision, or scientific claim was created by readiness.

The first public terrain-control run failed because NumPy was absent from the Linux runner; the next workflow edit failed before creating any job. A later correction-evidence commit failed because its receipt hash was computed from Windows CRLF bytes before Git normalized the committed blob to LF. All three runs are retained. The corrected workflow pins `numpy==2.5.1`, and GitHub Actions run `33819458096` passed the 199-file repository check and all 190 tests. The LF-normalized additive correction receipt does not change the terrain thresholds or any DEM input.

GitHub Actions run `33809208304` for the published DEM verification commit remains a **FAIL**. Its Linux test runner could not resolve the operator's external Windows custody root. The correction keeps strict external path and byte validation as the production default, lets the portable suite verify tracked receipts and recorded promoted identities without external access, and separately reverified all four custody files locally (170,302,058 bytes). The failed run is retained rather than reclassified; no DEM pixel, vertical datum, radar output, or scientific result was established by the correction.

The generic intake-contract validator also returns **FAIL** for the four immutable DEM attempt IDs because their RFC 3339 timestamp fragments preserve uppercase `T` and `Z`, while its identifier grammar is lowercase-only. The project-specific receipt, byte, and custody validators pass. Rewriting completed receipt identities would damage the audit trail, so the mismatch is retained; it prompted the prospective Sentinel correction below.

The still-unattempted Sentinel transfer runner has now been corrected prospectively: attempt identifiers lowercase only the identifier copy of the timestamp while preserving the RFC 3339 event timestamps themselves. Eleven focused tests pass, the active Sentinel intake remains unchanged and passes the generic intake validator, and no network, authentication, credential, custody, or product-byte action occurred. The completed DEM identifiers remain unchanged.

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
- review and explicitly resolve the DEM vertical-datum route before Sentinel-1 terrain correction, without silently selecting `GEOID` or `NONE`;
- if the exact EGM2008 route is approved, wait for the owner to install the matching ArcGIS Coordinate Systems Data component before any conversion attempt;
- review void-fill, seam, artifact, and terrain plausibility before treating the structurally valid DEM as processing-fit.

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
