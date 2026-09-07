# Decision log

## D-001 — Public repository scope

**Decision:** Create a public repository containing methods, controls, small scripts, and lightweight evidence records.
**Reason:** Supports inspectability without placing large or restricted data in Git.
**Status:** Authorized for bootstrap by the owner.

## D-002 — Projected coordinate system

**Decision:** Use WGS 1984 UTM Zone 45N (EPSG:32645) as the master analytical CRS.
**Reason:** The study area lies in UTM zone 45N and projected units support defensible distance and area measurement.
**Status:** Confirmed after owner approval of the M1 search and review AOIs; ArcGIS Pro imported the EPSG:32645 derivative successfully.

## D-003 — Core imagery route

**Decision:** Prefer Sentinel-2 Level-2A and Sentinel-1 GRD for the reproducible public core.
**Reason:** Complementary optical/radar evidence and broadly accessible Copernicus data.
**Status:** Candidate products recorded; pixels and rights not yet verified.

## D-004 — High-resolution imagery

**Decision:** Keep Planet/Vantor or similar noncommercial imagery on a separate gated path.
**Reason:** Account terms and CC BY-NC or asset-specific restrictions may constrain use and redistribution.
**Status:** Deferred pending exact asset and license review.

## D-005 — Data custody

**Decision:** Exclude raw imagery, large rasters, geodatabases, packages, credentials, and licensed assets from Git.
**Reason:** Size, security, reproducibility, and third-party rights require controlled custody.
**Status:** Adopted in `.gitignore` and repository validation.

## D-006 — Repository license

**Decision:** Do not add a license during bootstrap.
**Reason:** Public visibility is not a license, and the owner has not selected terms for original repository content.
**Status:** Owner decision pending.

## D-007 — Scientific wording

**Decision:** Default to “satellite-observed change” and keep observation, interpretation, and attribution separate.
**Reason:** Before/after proximity alone does not prove causation.
**Status:** Adopted as a project rule.

## D-008 — M1 search and review AOIs

**Decision:** Approve the exact three-area geometry bound to SHA-256 `68c406f7f41c301c339e200ccdd75194183c483c65156ab3949e64236072ccde` for M1 source discovery, review, and ArcGIS organization.
**Reason:** The regional overview, source area, and upper corridor provide explicit, reproducible bounds while remaining separate from future mapped change polygons.
**Status:** Approved by the owner through locked human-review response `3e7198c5919fde579bc7864ceba6ce44d5fc91b9920fb0608a6857af54174bb9`; this does not authorize full-product acquisition or scientific conclusions.

## D-009 — Candidate source-manifest route

**Decision:** Propose all six Sentinel-1 GRD records and the two Sentinel-2 RUM records for controlled acquisition planning; defer both Sentinel-2 RUL context records; reject none at metadata/quicklook stage.
**Reason:** RUM and the detailed radar slices intersect the approved event-area AOIs, while RUL contributes only cloud-limited regional context. Inconclusive candidates remain preserved until pixel QA.
**Status:** Approved by the owner for controlled acquisition planning through source-manifest review bundle SHA-256 `dd7d85562134e2c0cc2115eabdf329de56763209918dc65c872ceed911900544` and candidate manifest SHA-256 `6c67a1a6cb3411bd9ccab5f837e2c060757ddc5f1317f171bc5f62f9b1a22eef`. The approval does not authorize authentication, terms acceptance, or downloads.

## D-010 — Proposed M2 controlled-acquisition boundary

**Decision:** Propose a bounded M2 route for a fresh storage preflight, external non-Git custody, use of an owner-controlled existing Copernicus account or authenticated session, and download and verification of only the eight exact M1-approved products.
**Reason:** M1 has fixed source identities and dispositions, but product custody, pixels, masks, rights at access time, checksums, and baseline quality remain untested.
**Status:** Approved by the owner on 3 September 2026 through the exact review bundle SHA-256 `e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d` and acquisition-plan SHA-256 `6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d`. The completed response was locked and reconciled before activation. New or changed terms, account changes, credential disclosure, spending, products outside the exact eight, and scientific publication remain outside the approval.

## D-011 — ArcGIS evidence model

**Decision:** Store direct satellite observations, analyst interpretations, and event-attribution assessments in distinct related datasets, with separate exclusion, stable-control, source-link, and QA structures.
**Reason:** A projected map must preserve the difference between measured change, possible geomorphic meaning, and causal support while retaining failed, rejected, deferred, inconclusive, invalid, and superseded evidence states.
**Status:** Implemented and validated as a metadata-only EPSG:32645 ArcGIS Pro 3.7.1 workspace. Scientific datasets remain empty; no acquisition or scientific claim is implied.

## D-012 — Offline container verification before pixel admission

**Decision:** Require exact local SHA-256, provider-MD5 agreement, catalog-size review, safe ZIP structure, CRC, exact SAFE root identity, and analysis-critical Sentinel-1 or Sentinel-2 members before any acquired product advances to raster and AOI pixel QA.
**Reason:** A successful transfer or present filename does not establish a complete, untampered, analysis-capable product; a complete container still does not establish usable pixels or scientific fitness.
**Status:** Implemented as deterministic controls with synthetic tests. M2 is now active, but the historical pre-acquisition readiness audit remains `defer` because no product bytes have been examined.

## D-013 — Predeclared projected pixel-readiness thresholds

**Decision:** Judge each real-product route against fixed EPSG:32645 AOI-coverage, mask, grid-alignment, and registration rules before admitting satellite observations. Treat a QA pass as fitness evidence only; retain route-level `block`, `defer`, and `invalid` outcomes without automatically rejecting the source identity.
**Reason:** Pixel usability cannot be inferred from catalog coverage or container structure, and thresholds chosen after viewing change could bias the result. A portable core keeps decisions reproducible while an ArcGIS-native adapter proves projected area and raster-grid behavior on the target platform.
**Status:** Contract and core implemented before product access. ArcGIS Pro 3.7.1 Advanced and Spatial Analyst passed deterministic 20 m synthetic coverage for all three approved AOIs, passed an aligned pair, blocked an intentional 0.6-pixel shift, and deferred unmeasured registration. No real pixels or scientific evidence were admitted.

## D-014 — Activated M2 source gate and empty custody initialization

**Decision:** Execute only the approved non-mutating live preflight, then create the exact empty external custody and staging structure after every source, rights, identity, path, collision, and storage check passes.
**Reason:** Catalog approval alone does not establish current availability or a safe destination, and authentication must remain separate from public records and filesystem initialization.
**Status:** Completed on 3 September 2026. All eight exact products were online with unchanged names, UUIDs, sizes, and provider checksums; the source gate passed 64 required criteria; 514.942 GiB was free; and matching repository/external custody receipts have SHA-256 `12812d1c53e13ec287425f74a1988f5c0be7d0638f856c9606fddf1c1431fb09`. No authentication or product transfer occurred. Work stops at `M2-AUTHENTICATION-REFERENCE` pending a secret-safe existing owner-controlled credential or session reference.

## D-015 — Fail-closed one-product transfer state machine

**Decision:** Transfer only one exact approved product per invocation through exclusive staging, append-before-transfer evidence, streamed SHA-256 and provider-MD5 verification, redirect refusal, retained failures, and atomic hard-link no-replace promotion.
**Reason:** An authenticated HTTP response is not custody evidence, and a collision, changed page, changed catalog identity, partial file, or checksum mismatch must remain visible without overwriting existing bytes.
**Status:** Implemented and covered by eleven local fixture tests. The readiness receipt records no network request, authentication, active-intake mutation, or product bytes. Real execution remains at the secret-safe authentication-reference gate.

## D-016 — Active per-product offline container verification

**Decision:** Activate the predeclared container controls for the exact eight M2 products and require a promoted active-intake identity plus successful-transfer receipt before any archive scan.
**Reason:** Candidate checks built before activation must be bound to the current approval and custody, while archive access must remain offline, read-only, non-extracting, and separate from pixel or scientific admission.
**Status:** Active contract and per-product wrapper implemented. Five tests verify authority, exact product controls, custody bindings, offline behavior, and refusal of an unpromoted asset. No real archive bytes were read during activation or testing.

## D-017 — Proposed exact DEM dependency amendment

**Decision:** Prepare, but do not activate, an M2 amendment for the exact four Copernicus DEM GLO-30 COG tiles that cover the approved AOIs and for explicit acceptance of the exact hash-bound Copernicus WorldDEM-30 license.
**Reason:** The installed ArcGIS Pro Sentinel-1 terrain-correction tools accept or require a DEM, while the active M2 approval covers only eight Sentinel products and forbids new terms acceptance or extra products. The anonymous AWS route avoids a new account but does not remove the license-acceptance requirement.
**Status:** Approved on 3 September 2026 through review bundle SHA-256 `caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e`, amendment proposal SHA-256 `92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69`, and exact license SHA-256 `9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd`. See D-025 for activation evidence and the current boundary.

## D-018 — Predeclared DEM verification and Sentinel-1 processing boundaries

**Decision:** Derive non-authorizing intake and ArcGIS GeoTIFF verification controls for the exact four proposed DEM tiles, and fix the two independent Sentinel-1 processing routes before real pixels are available.
**Reason:** A reviewed source list does not define safe custody or raster acceptance, and ArcGIS processing defaults could otherwise hide consequential choices about orbit vectors, despeckling, terrain masks, units, or vertical datum.
**Status:** The active intake and verification controls inherit the exact approved amendment. All four DEM rasters later passed exact-byte, ArcGIS structural, and valid-AOI-coverage checks. Production processing remains deferred because the source heights are EGM2008 orthometric while ArcGIS documents EGM96 for its built-in geoid option, and updated orbit files are not authorized auxiliary products. No radar-processing or scientific result has been created.

## D-019 — Predeclared Sentinel-2 Level-2A processing

**Decision:** Fix the exact RUM pair, metadata-derived BOA scaling, DN-zero treatment, conservative SCL mask, 20 m EPSG:32645 grid, contextual indices, and cross-platform comparison controls before reading product pixels.
**Reason:** Processing baseline 05.12 requires band-specific offsets and metadata verification, while a high-cloud post-event scene and an S2C-to-S2B comparison could otherwise invite hidden mask, scaling, or harmonization changes.
**Status:** Fifteen portable tests and one ArcGIS Pro 3.7.1 synthetic run pass. Five scaled bands and NDVI, MNDWI, and NBR matched declared values with DN-zero and SCL exclusions preserved. Missing and duplicate offset controls are covered. Real metadata, pixels, AOI coverage, registration, optical change, and scientific admission remain unestablished.

## D-020 — Append-only SAFE materialization after container verification

**Decision:** Permit offline materialization of only the eight exact M2 products after one promoted intake identity and its matching `pass_container_only` receipt, using an exclusive external attempt and a SHA-256 manifest for every extracted file.
**Reason:** ArcGIS needs ordinary SAFE files, but generic ZIP extraction can introduce traversal, Windows path aliasing, overwrite, symlink, archive-drift, and incomplete-attempt ambiguity after a container check.
**Status:** The gate-deferred contract, portable core, and production wrapper are implemented with fourteen passing synthetic tests. The production wrapper currently stops on `asset_not_promoted`; no real archive, external materialization path, raster, or scientific evidence was accessed or created.

## D-021 — Separate native JP2 header readiness from pixel fitness

**Decision:** Require the exact materialized Sentinel-2 pair to pass member identity, Level-2A metadata, native JPEG2000 readability, EPSG:32645, resolution, extent, and cross-date header checks before any pixel, mask, or change processing.
**Reason:** A complete SAFE extraction does not prove that ArcGIS can open its rasters, that the selected granule and bands are unique, or that before/after grids are comparable. Keeping header readiness separate prevents a structural pass from becoming a pixel or scientific claim.
**Status:** Twelve portable tests and an ArcGIS Pro 3.7.1 synthetic run pass; a deliberate full-grid shift blocks. Two direct ArcGIS JP2-write failures and five superseded prepublication passing receipts remain recorded. The production runner still stops before ArcPy because no real materialization receipts exist.

## D-022 — Correct the PB 05.12 classification-quality mask model

**Decision:** Model `MSK_CLASSI_B00.jp2` as its specified three-band 60 m Boolean mask, with opaque cloud, cirrus, and snow/ice bands kept distinct from the single-band 20 m SCL layer.
**Reason:** Official Sentinel-2 documentation contradicted the first published fixture's one-band 20 m assumption. Keeping that assumption would cause the header gate to reject a structurally valid PB 05.12 product before pixel QA.
**Status:** The `df3e93a` checkpoint and its ArcGIS attempt are retained as superseded evidence. The corrected contract and twelve portable tests pass, and ArcGIS Pro 3.7.1 opens the three-band 60 m mask by reading its `Band_1` through `Band_3` child descriptions. The deliberate full-grid shift blocks with sixteen extent mismatches. No real SAFE was read.

## D-023 — Preserve the initial intake while validating append-only acquisition progress

**Decision:** Retain the activation-time active intake as an immutable snapshot and validate the mutable active intake against it through the authorized, staging, failed, and promoted states. Require exact approved product identity, one append-only attempt at most under the current no-retry control, terminal receipt consistency, secret exclusion, and optional local reconciliation of external paths and promoted bytes.
**Reason:** The transfer runner must mutate `contracts/m2-intake.json` after a real attempt. Comparing every later state to the initial file hash would make the repository validator fail on the first legitimate transfer and would blur an activation-time binding with current operational truth.
**Status:** Implemented with nine focused tests and a passing read-only external check. All eight products remain authorized and unattempted; no credential value or product byte was read.

## D-024 — Derive acquisition checkpoints without silently changing project truth

**Decision:** Derive the current M2 acquisition checkpoint only from a passing append-only intake validation. Map eight authorized products to the authentication handoff, partial or active nonfailed progress to acquisition in progress, any retained transfer failure to review, and eight promoted products to container verification. Emit proposed profile and goal updates only as exclusive scratch candidates.
**Reason:** A real attempt changes operational state before a Git checkpoint can be committed. Deterministic derivation prevents stale status while keeping multi-file control updates reviewable and reversible.
**Status:** Implemented with nine focused tests. The live state derives `M2-AUTHENTICATION-REFERENCE`; tracked profile and goal controls already match, and no candidate or tracked file was written by the verification run.

## D-025 — Activate the exact four-tile DEM amendment

**Decision:** Bind the owner's exact completed approval to the four named Copernicus DEM GLO-30 tiles and the accepted WorldDEM-30 license document, then activate only their fresh preflight, anonymous no-cost acquisition, non-Git custody, verification, and bounded Sentinel-1 terrain-processing use.
**Reason:** The human review closed the legal and acquisition-scope gate without changing the independent Sentinel credential checkpoint or authorizing accounts, credentials, cost, extra products, redistribution, scientific publication, vertical-datum assumptions, or orbit auxiliaries.
**Status:** Activated on 3 September 2026 after locking response SHA-256 `4d877e1b667116a58950b0f567cbb300a3b59a84de65446647c9e760bdfc8193` and reconciling one approval with no fabricated decisions. The active intake contains four authorized, unattempted assets, and the active verifier is gate-deferred. Activation made no network request, external DEM custody mutation, payload request, raster read, or scientific claim. The next parallel checkpoint is `M2-DEM-FRESH-PREFLIGHT`.

## D-026 — Pass fresh DEM preflight and initialize empty custody

**Decision:** Advance the approved DEM workstream only after the exact license bytes, four official STAC items, four anonymous object identities, storage, paths, redirects, and collisions pass a fresh no-payload check; then create only the missing empty DEM custody and staging directories.
**Reason:** The earlier metadata review established candidate availability, not current identity or safe local custody. Separating `HEAD` and catalog checks from payload transfer preserves a clean stop before any external data bytes arrive.
**Status:** Passed at `2026-09-03T20:48:10Z`. The exact license hash and all four object lengths, ETags, Last-Modified values, content types, and byte-range headers matched; 519.029 GiB was free; and no redirects, account action, charge, path hazard, collision, or payload occurred. Empty custody was initialized at `2026-09-03T20:50:33Z` with matching receipt SHA-256 `31d1b814d8da753dd2335f3110a49107df3f7a6c75875154a0fff0338b7e80a0`. The next checkpoint is `M2-DEM-ACQUISITION`; GeoTIFF, pixel, vertical-datum, radar, and scientific fitness remain unestablished.

## D-027 — Use a one-tile anonymous DEM transfer state machine

**Decision:** Acquire one exact tile per invocation only after a matching anonymous `HEAD` check, then write an external started event before streaming to exclusive staging, compute local SHA-256 and exact size, preserve all failed or partial bytes, and promote by atomic hard-link without replacement.
**Reason:** A public object and passing preflight still do not establish transferred-byte identity. One-at-a-time append-only custody prevents concurrent ambiguity, hidden redirects, overwrite, or silent retry.
**Status:** The runner and seven local tests pass with readiness receipt SHA-256 `515b692ac4717540d5347a518a6f8ea47625939c11ca92fc264133d960b92337`. All four approved tiles were subsequently transferred in order and promoted with exact size and local SHA-256 receipts; no transfer failed, no credential or account was used, and each terminal attempt was reconciled before the next began. ArcGIS verification is complete; the current checkpoint is `M2-DEM-VERTICAL-DATUM-REVIEW`.

## D-028 — Retain and correct the first ArcGIS GeoTIFF wrapper failure

**Decision:** Preserve the first `M2-DEM-001` verification receipt as a failed runtime attempt, classify it separately from data fitness, and replace the unsupported `GetRasterProperties("NODATAVALUE")` call with the installed `arcpy.Raster.noDataValue` property before any rerun.
**Reason:** ArcGIS Pro 3.7.1 rejected `NODATAVALUE` as outside the tool's property domain after local byte identity passed. Treating that wrapper error as a raster defect or silently overwriting the failed attempt would corrupt the evidence trail.
**Status:** Two failed receipts remain immutable. Correction 001 replaced the unsupported NoData property; the second attempt then stopped because the COG has no precomputed ArcGIS statistics. Correction 002 uses ArcPy's NumPy bridge to compute full-raster finite non-NoData counts and extrema without writing statistics or sidecars. The third append-only `M2-DEM-001` attempt passed, as did the first attempts for the other three tiles. The failures remain historical evidence and are superseded only as data results.

## D-029 — Complete four-tile ArcGIS structural and AOI-valid coverage verification

**Decision:** Reconcile exactly one passing ArcGIS receipt for each approved DEM tile, preserve the two earlier failed wrapper attempts, and advance only to explicit vertical-datum review.
**Reason:** Exact local bytes, ArcGIS-readable structure, and finite coverage across the approved AOIs are prerequisites for terrain processing, but they do not establish void/seam/artifact quality, terrain plausibility, vertical-datum fitness, radar-processing success, or a scientific result.
**Status:** Completed at `2026-09-03T21:32:49Z`. ArcGIS Pro 3.7.1 verified four 3600-by-3600, single-band F32 EPSG:4326 rasters, 170,302,058 exact bytes, 51,840,000 finite non-NoData cells, zero NoData or nonfinite cells, and coverage of all three approved AOI bounds. Summary SHA-256 `97f6a66daccd236decc6cdaac7035ca4cafb541ce7d82cecf08973ec6962f7ef` is bound to the active controls. The next checkpoint is `M2-DEM-VERTICAL-DATUM-REVIEW`; no `GEOID` or `NONE` route has been selected.

## D-030 — Prepare an exact EGM2008 preconversion method review

**Decision:** Present an exact, bundle-bound proposal for EGM2008 one-minute preconversion before using `NONE` in the ArcGIS SAR tools; retain the built-in EGM96 `GEOID` route as sensitivity-only and keep raw orthometric input with `NONE` prohibited.
**Reason:** Copernicus identifies the source heights as EGM2008 orthometric, ArcGIS identifies its SAR `GEOID` option as EGM96, and the installed runtime lacks the optional EGM2008 grid. Selecting a production route changes scientific method and requires an explicit human decision plus an owner-controlled component installation.
**Status:** Review-ready with proposal SHA-256 `bdaa7f9e10840d41c9bc47d65b33bbee3f71e82fe7862069ff1129785047f065` and bundle SHA-256 `9b40e81df766ea866c5bff51cdbc4d83e7e7da6a554fb1709fc553d8221bebbc`. The blank response contains zero decisions. No sign-in, terms acceptance, software download or installation, UAC action, DEM conversion, radar processing, or scientific claim occurred.

## D-031 — Separate portable DEM receipt validation from external custody verification

**Decision:** Let repository tests validate exact tracked receipts and recorded promoted identities without resolving the operator's external data root, while retaining strict external path and byte verification as the production reconciliation default and as an explicit local check.
**Reason:** GitHub Actions run `33809208304` failed because the Linux runner does not contain the operator's Windows custody directory. Requiring that directory in a portable repository test conflated two evidence surfaces without strengthening custody verification.
**Status:** Corrected with six focused tests, 185 full repository tests, a 192-file project check, and a separate local re-hash of four promoted files totaling 170,302,058 bytes. The failed run remains retained evidence. A separate generic intake-validator failure is also retained because the four immutable completed attempt IDs contain uppercase `T` and `Z`; those historical identities were not rewritten. The correction creates no raster, vertical-datum, radar, or scientific claim.

## D-032 — Correct future Sentinel attempt identifiers before acquisition

**Decision:** Lowercase the transfer attempt identifier derived from asset ID, timestamp, and nonce, while preserving the separate RFC 3339 event timestamps and every existing source, authority, collision, checksum, and custody gate.
**Reason:** The DEM validation finding showed that uppercase `T` and `Z` timestamp fragments violate the generic intake-contract identifier grammar. The Sentinel route is still unattempted, so its generator can be corrected before it creates any historical identifier.
**Status:** Eleven focused tests pass and the unchanged active Sentinel intake passes the generic validator. The historical readiness receipt remains immutable and is supplemented by a current correction receipt. No secret prompt, credential, network request, external file, active intake, or product byte was read or changed.

## D-033 — Predeclare DEM terrain-quality evidence before real metrics

**Decision:** Fix the four source identities, four native seam pairs, terrain and slope thresholds, EPSG:32645 processing, exclusive external output, required visual criteria, and decision semantics before reading real DEM values.
**Reason:** Full finite coverage does not establish absence of void-fill artifacts, boundary steps, or implausible terrain. Predeclaration prevents result-driven threshold changes and keeps terrain quality independent from the unresolved vertical-datum decision.
**Status:** Static controls and five synthetic tests pass. The first synthetic north-south seam fixture failure is retained in the readiness record and was corrected only by fixing reversed fixture row indices. No real DEM pixel, output, vertical conversion, Sentinel processing, or scientific result was created by readiness.

## D-034 — Pin the portable terrain-QA dependency without changing the method

**Decision:** Install exact `numpy==2.5.1` in GitHub Actions before the portable tests, while leaving the bound terrain contract, core, tests, input identities, seams, and thresholds unchanged.
**Reason:** The first public checkpoint passed the repository checker but the Linux test runner lacked NumPy. The next workflow edit failed with zero jobs and no available job log; retaining both results distinguishes CI integration failure from terrain or ArcGIS evidence.
**Status:** Failed runs `33819299553` and `33819378562` remain public. Corrected run `33819458096` installed NumPy 2.5.1, passed the 199-file checker, and passed all 190 tests before any real DEM terrain metrics were observed. The additive evidence commit then failed as run `33819677224` because its hash bound Windows CRLF bytes instead of the LF-normalized Git blob; that failure is retained and the receipt is now explicitly serialized with LF.

## D-035 — Preserve the first ArcGIS terrain-QA path failure and predeclare attempt-002

**Decision:** Classify attempt-001 as a wrapper path-binding failure, never reuse its declared output path, and create an attempt-002 control that changes only the external custody root and exclusive output path.
**Reason:** The active DEM files live beneath `nepal-2026-before-after-map-data\custody`, while the first control joined tile-relative paths directly beneath the project data root. Correcting that join must not alter source identity, thresholds, seam definitions, processing, vertical semantics, or the scientific claim boundary.
**Status:** Attempt-001 failed before opening a DEM or creating output and is retained by receipt SHA-256 `f5b3d6ddd244aaee66128ba874c821a03ca5ded2ba8b4c4768d46f27380c0740`. Attempt-002 contract SHA-256 `434f8ff1d73a1d726e6aca47db78c2ef969fe9f395f03a3673d9564d569f9553` points to the verified custody root and a new no-overwrite path. No real terrain metric, vertical conversion, Sentinel processing, or scientific result has been produced.

## D-036 — Exclude transient ArcGIS locks from a new stable-output manifest

**Decision:** Preserve attempt-002 as failed and use a new attempt-003 wrapper that lists but does not hash basename-suffixed `.lock` files while continuing to hash every stable artifact.
**Reason:** Attempt-002 completed the terrain and map operations but the live geodatabase held a process lock when the inventory opened it. A lock is a transient coordination file rather than a reproducible deliverable; inventory logic can exclude it without changing terrain values, thresholds, source custody, raster operations, or scientific interpretation.
**Status:** Attempt-002 remains a failed 189-file external artifact set because no quantitative receipt was persisted. Failure receipt SHA-256 `858413f1e88c6d25640738e49723c8562fc3fabea952adccd08b8d0a9ff89e63` records the unchanged four source hashes and exact runtime error. Attempt-003 contract SHA-256 `e903117aba56e07c83e4b314ec613019f9e0d2b35f60222c03ca74a7c0a66f88` uses a new output path and otherwise preserves the method.

## D-037 — Admit the attempt-003 terrain screen without promoting downstream readiness

**Decision:** Record attempt-003 as a pass for the fixed gross-artifact, seam, slope, projection, stable-output, and exported-map criteria, while retaining vertical datum, independent elevation accuracy, pair-specific radar behavior, owner or expert review, and all satellite-change claims as separate deferred gates.
**Reason:** The observed terrain metrics and visual surfaces satisfy the predeclared terrain-only rules, but neither those rules nor a coherent map can establish vertical accuracy or radar-processing fitness. A dataset-readiness audit must preserve those unresolved dependencies instead of letting the successful terrain screen authorize later work.
**Status:** Completed at `2026-09-04T00:35:22Z`. All four tiles and seams passed, the AOI slope screen passed, and all 189 stable external files reconciled by path, size, and SHA-256 with no remaining lock. The PNG and rendered one-page PDF passed model visual inspection. Receipt SHA-256 `9663c261de37c77fd96896d1fbb37c4c3a970c47966661908673db880e640dd7` binds the external manifest SHA-256 `6baf1ec47f4bc27c9dc2ab3501637690d717673e63d9e0f5036e1b2dc2ed1620`. The formal readiness decision is `defer`; it created no authority and released no downstream action. The parallel checkpoint remains `M2-DEM-VERTICAL-DATUM-REVIEW`.

## D-038 — Prepare a terrain-result owner review without embedding DEM pixels

**Decision:** Create a separate owner review for the exact attempt-003 terrain result, using a text-only public review surface and second-order hash bindings to the external APRX, PDF, PNG, and stable-output manifest.
**Reason:** The readiness audit requires a completed owner or independent expert result review, but the active data boundary prohibits committing DEM-derived raster imagery. Binding the external artifacts through the immutable terrain receipt preserves inspectability without copying pixels into Git or allowing a visual approval to waive vertical, accuracy, radar, or scientific gates.
**Status:** Review-ready under bundle SHA-256 `834ad354fc134b2017afdd3b238c1a6271276e8b1a95776e434180c7283a26d5`. Seven tracked artifacts validate, the 1800-by-1680 text-only surface passes visual inspection, and the blank response contains one item with zero human decisions. Approval can permit reassessment only of the owner terrain-result review gate after exact response lock and reconciliation. It creates no vertical-datum, installation, acquisition, radar-processing, publication, or scientific authority.

## D-039 — Prepare an exact restituted-orbit amendment without acquiring payloads

**Decision:** Bind one exact S1D `AUX_RESORB` file to each of the four unique approved Sentinel-1 acquisition windows using full validity coverage, greatest minimum temporal margin, latest publication, and provider UUID in that order; present the four-file route as a separate owner amendment and require a fresh review for any later precise substitution.
**Reason:** The approved GRD archives contain predicted state vectors, while the radar baseline contract requires restituted or precise vectors and ArcGIS supports explicit EOF application. The four orbit files are additional product identities outside the active eight-product approval. A declared deterministic rule prevents unrecorded orbit choice and keeps the currently unavailable precise route distinct.
**Status:** Review-ready under bundle SHA-256 `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1` and proposal SHA-256 `b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292`. Official live metadata found four selected restituted files totaling 2,539,715 bytes and zero covering precise files at assessment time. The source gate remains blocked on scope authority; candidate intake and verification controls are non-active; the review surface passed visual inspection; and the blank response contains one item with zero human decisions. No credential, payload, orbit XML, corrected metadata, radar pixel, or scientific result was accessed or created.

## D-040 — Activate the exact four-file restituted-orbit amendment

**Decision:** Accept the owner's hash-bound approval for review bundle `ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1` and proposal `b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292`, and activate only the four named S1D `AUX_RESORB` files for acquisition, verification, non-Git custody, and exact-source application after their Sentinel custody prerequisites pass.
**Reason:** The locked response closes the exact scope-authority gate while retaining the reviewed dependency ordering, secret-reference boundary, and distinction between restituted and later precise products.
**Status:** Activated at `2026-09-04T02:01:22Z`. Approval receipt SHA-256 `6501c953baa6d823304eaa54b53a94fa41119b7805622840306d2633a9fb87c1` binds the exact response, reconciliation, proposal, candidate manifest, and active controls. All four orbit assets remain authorized with zero attempts. No precise substitution, account action, terms acceptance, payload publication, radar pixel processing, or scientific result is authorized.

## D-041 — Preserve the first orbit-custody initialization failure and complete a bounded correction

**Decision:** Retain attempt-001 as failed after its omission of the `attempt-events` parent, then permit one attempt-002 continuation only against the exact seven-directory, zero-file partial inventory and unchanged approved roots.
**Reason:** The first run created approved empty directories before stopping. Treating them as absent or silently retrying would obscure the failed attempt; binding the exact partial inventory allowed a narrow correction without authorizing network, credential, or payload activity.
**Status:** Attempt-001 failure receipt SHA-256 `a8d70ea0b63307962545078f4a578f696cc2255d9fd322d9a187128a8d79ebf7` remains required. Attempt-002 readiness SHA-256 `b7025e1efae74b2f18adf2ee6fbbfabd58316fd767ac56df491dcd752a20f4a0` bound the partial inventory and corrected initializer. The completed initialization receipt SHA-256 `1ea8bef201ad72cc695d9332400561edacacdc93e704916ed7b1a4b28efa1723` verifies seven preserved and ten newly created empty directories, with no authentication, network request, or payload file.

## D-042 — Guard orbit transfer on verified Sentinel custody

**Decision:** Require each orbit transfer to verify all bound Sentinel sources as promoted and offline container-verified before catalogue access or token lookup, then require exact provider MD5 and BLAKE3, local SHA-256, safe EOF XML, ordered finite state vectors, exact validity, scene binding, and atomic no-replace promotion.
**Reason:** Orbit files are meaningful only for their approved scenes, and early credential or network access would bypass the dependency order. Binding the executable controls and tests before real transfer makes later attempts auditable without treating synthetic validation as provider-byte evidence.
**Status:** Readiness receipt SHA-256 `7db7f160229299ab6e5a9302dd76546191855c8259c6f3757294c44dea30f9c0` records 29 focused tests and 219 full-suite tests passing. A fake-reference probe stopped with exit 12 and `bound_sentinel_source_not_promoted`, active controls were unchanged, and custody contains zero orbit payload files. The checkpoint is `M2-ORBIT-SENTINEL-CUSTODY`; later precise substitution remains separately gated.

## D-043 — Correct the active orbit intake's unknown-checksum explanation

**Decision:** Preserve the generic validator failure, then add only `expected.unavailable_reason` to each of the four active orbit assets to explain that local SHA-256 cannot exist before transfer while exact provider length, MD5, and BLAKE3 are already recorded.
**Reason:** The controlled-intake schema requires an explanation whenever expected identity is incomplete. The omission did not change source identity, but leaving the active contract invalid would weaken the pre-transfer gate.
**Status:** Failure receipt SHA-256 `05c4a67fe863c171e40d7ed9b1e08fe802d20a008f61b8a4ba3148b37278fecf` retains all four validator errors against active-intake SHA-256 `d82f062a59c256a53c658dfe3c138fa2ea7de01c076339d111413e0bd99a4c9c`. Correction receipt SHA-256 `53980d2cae8f757ecd82114be2526313b2664881d8d83c9234c42c016bf0d951` binds corrected active-intake SHA-256 `b52512ecf86a7d85f99f5cff932219bc29620f08871e3b3242b76b645b0e2604`. The generic validator passes, 219 repository tests and 29 focused orbit tests pass, and the guard still exits 12 before catalogue or token access with zero payload files.

## D-044 — Correct the activated orbit intake's stale candidate label

**Decision:** Preserve the inconsistent activated state, then change only the active intake's root `status` from `candidate_not_active` to `active`.
**Reason:** The activation correctly authorized the four assets and updated the authority extension, but retained the candidate control's top-level label. A future consumer could use that stale label to misroute the contract even though the current runner does not.
**Status:** Finding receipt SHA-256 `c803547535ad3c4a8bf4306eee293a8c08b2d9148853fdcfd5de6cc921f416ce` binds pre-correction intake SHA-256 `b52512ecf86a7d85f99f5cff932219bc29620f08871e3b3242b76b645b0e2604`. Correction receipt SHA-256 `6b60feff477344f36eb63125d3bc50dfb13e9ec4ef25fd260d78fa82171861c7` binds active-intake SHA-256 `9e1c2675b4716ec78fbca8c3c2e9cf0bd3df20cf6362b5bba0db4de582a27539`. The generic validator, 219 repository tests, and 29 focused orbit tests pass; the guard remains exit 12 before catalogue or token access and custody contains zero orbit payload files.

## D-045 — Reconcile rendered CDSE terms-page drift by binding the legal section

**Decision:** Preserve the initial source gate and preflight, record the stopped owner invocation as a pre-mutation guard stop, and supplement them with a fresh source gate and preflight that bind the CDSE terms page by its normalized legal section plus official structured modification date. Keep exact-byte bindings for the OData documentation, token documentation, and linked Sentinel Data Legal Notice.
**Reason:** The rendered terms HTML changed after the initial preflight even though the official terms node still reports a 5 May 2026 document modification date, every scope-relevant clause used by the source gate remains present, and the exact linked Sentinel Legal Notice is unchanged. A whole-page hash also covers unrelated page shell and related-news content, so it is too broad for the legal stop while a section identity remains fail closed for actual terms changes.
**Status:** Reconciled and refreshed at `2026-09-04T03:41:36Z`. Terms reconciliation SHA-256 `113828e782e47e3335a4b5701f1cedcb51f7416a53c0e71bad0124403f7cac2c`, refreshed source-gate SHA-256 `799e23ee6bba16184c692d6ce2ed91af6e8e6c697b2171838e9ea1c08410ddfe`, and refreshed preflight SHA-256 `0eba97d9a9c3988b0fdf74223f198cf32b63f02a46c55ebd248535313cc83ba7` bind eight online exact products, 64 passing criteria, normalized legal-section SHA-256 `22cf55ad3949e8eaee715780654be9eb0e8648a2808d6ba007b47c9849ab2b01`, and zero Sentinel attempts or payload files. No credential value, authentication, terms action, or external custody mutation occurred. The checkpoint remains `M2-AUTHENTICATION-REFERENCE`.

## D-046 — Preserve the first truncated Sentinel transfer and require recovery review

**Decision:** Admit `M1-SRC-001` through `M1-SRC-003` only as promoted, container-verified inputs; retain the incomplete `M1-SRC-004` bytes and terminal events as failed evidence; and stop all further Sentinel acquisition until an exact recovery decision is completed. Do not resume the partial because the attempt did not preserve both verified range support and an unchanged strong remote object identity.
**Reason:** Three transfers matched their exact catalog lengths and provider MD5 values, passed no-replace promotion, and passed offline ZIP/SAFE checks. CDSE then ended the `M1-SRC-004` response after 561,593,598 of 1,732,332,897 expected bytes. Deleting, resuming, silently retrying, or continuing the batch would weaken the append-only failure and recovery controls.
**Status:** Reconciled at `2026-09-04T04:50:25Z` in `records/acquisition/sentinel-acquisition-reconciliation-001.json`. The active intake validates with four authorized, one failed, and three promoted products. The retained partial has SHA-256 `299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66`; automatic retry is false; no secret value is recorded; and pixel usability, registration, and scientific change remain unestablished. The current checkpoint is `M2-ACQUISITION-REVIEW`.

## D-047 — Prepare one fresh Sentinel recovery for exact owner review

**Decision:** Prepare, but do not activate, a review package for one fresh byte-zero transfer of the same exact `M1-SRC-004` through a distinct exclusive staging identity. Preserve the original failed partial and events unchanged. If the recovery passes, allow continuation only of the four still-unattempted products under the original approval; stop on any later failure.
**Reason:** The retained attempt is terminal and explicitly disallows automatic retry. Its evidence does not establish both verified range support and an unchanged strong remote-object identity, so partial resume is not a safe recovery. A new bounded owner decision is required before any additional product bytes are requested.
**Status:** Ready for review with zero human decisions. Review bundle SHA-256 `dffa194cc91636a35b5f55af6ece32bb6eb90d77b65ea3d9865413f912d146e7` binds proposal SHA-256 `7b8b5e83265b37962f879ca7dad85ab5f5c04ceb28ee0f15fa774a79df7fd013` and blank surface SHA-256 `9d643d42aaa9d279cfa5690363ade3e3f065411231239ae51bf77a4b4bc30307`. No retry, deletion, resume, product substitution, or further Sentinel acquisition has been performed or authorized by preparation.

## D-048 — Preserve test-induced production artifacts and repair test isolation

**Decision:** Retain the unintended `M1-SRC-001` SAFE materialization as materialization-only evidence with explicit test provenance. Retain the zero-byte failed `M2-ORB-001` attempt and both external events as terminal failure evidence. Correct the stale production-wrapper tests so they select only currently ineligible sources or exercise the full milestone guard, skip when no safe refusal probe exists, and verify the relevant repository and external inventories remain unchanged.
**Reason:** Live project state advanced beyond assumptions embedded in two tests. One wrapper therefore materialized a legitimately eligible archive; another crossed a per-orbit scene guard even though the active milestone's full `M2-VERIFY` dependency was incomplete. Erasing either outcome would weaken the audit trail, while leaving the tests unchanged could cause repeated production mutation.
**Status:** The retained materialization contains 26 files and 1,732,324,248 extracted bytes; all per-file hashes independently match its manifest. It establishes no raster readability, pixel usability, baseline, change, or scientific admission. The retained orbit attempt used a tracked nonsecret test literal, received zero payload bytes, left no payload file, used no owner credential, and is not eligible for automatic retry. The corrected orbit runner exits 12 with `sentinel_verification_unit_not_complete` before catalogue access, token lookup, events, or payload requests. Twenty-nine focused orbit tests pass with the retained inventories unchanged.

## D-049 — Prepare dependency-gated orbit recovery for exact owner review

**Decision:** Prepare, but do not activate, a review package for one fresh byte-zero transfer of the same exact `M2-ORB-001` through a distinct attempt identity. Preserve the original failed receipt and events unchanged. Require the entire `M2-VERIFY` unit to be complete before the recovery can reach catalogue access or an owner credential reference. After a passing recovery, permit continuation only of `M2-ORB-002` through `M2-ORB-004` under the original orbit approval and their existing controls.
**Reason:** The failed attempt is terminal and occurred outside the full active milestone dependency even though its two bound scenes were individually eligible. A new owner decision is required to reconcile the failure, and approval must not bypass the still-incomplete eight-product Sentinel verification unit.
**Status:** Ready for review with zero human decisions. Review bundle SHA-256 `df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b` binds proposal SHA-256 `ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a` and blank surface SHA-256 `63dc1df8aff522a9ffdf8a77f24b600d4efcfaf0342aed8ec914d5372821edd8`. No recovery, deletion, repeated retry, precise-orbit substitution, orbit application, radar processing, or scientific publication has been performed or authorized by preparation.

## D-050 — Parse retained Windows event paths portably

**Decision:** Preserve failed GitHub Actions run `33900195532`, then change the read-only acquisition-progress validator to extract the basename of recorded absolute Windows event paths with explicit Windows path semantics on every host. Add a regression test containing backslashes.
**Reason:** The project correctly records external custody on Windows, but the Linux CI host interpreted each backslash path as a single filename and rejected all four otherwise valid started-event references. This was a validator portability defect, not source, custody, receipt, or credential drift.
**Status:** The ten focused acquisition-progress tests and the 294-file repository checker pass locally after the correction. No network request, credential read, external mutation, or product request occurred. The failed run remains failed evidence; a new CI run must be verified separately.

## D-051 — Materialize the remaining eligible promoted Sentinel archives offline

**Decision:** Use the active materialization contract to extract `M1-SRC-002` and `M1-SRC-003` one at a time into distinct append-only external attempts after confirming each source is promoted and container-verified. Preserve the existing `M1-SRC-001` materialization and its unintended-test provenance; do not repeat it. Do not materialize failed or unattempted products.
**Reason:** Materialization is already authorized as offline data processing for an exact approved product after its transfer and container prerequisites pass. Completing it for the other eligible archives advances source custody without touching either acquisition-recovery gate, using a credential, or making a network request.
**Status:** Both planned attempts passed. Together with the retained `M1-SRC-001` attempt, 78 extracted files and 5,183,550,209 bytes independently match their external manifests. No source archive was modified. No raster readability, pixel usability, baseline, change, or scientific admission is established, and the Sentinel and orbit recovery decisions remain pending.

## D-052 — Predeclare a read-only radar input gate before inspecting real SAFE headers

**Decision:** Bind only the three materialized pre-event Sentinel-1 sources to a new offline gate that reverifies nine selected members, parses exact acquisition and embedded-orbit annotation structure, opens only the VV/VH measurement TIFF headers in ArcGIS, and compares complete attempt inventories before and after access.
**Reason:** The three sources can be checked independently for structural ArcGIS readiness while the missing post-event sources and separate recovery, orbit, vertical-datum, terrain-result, and pixel gates continue to block all baseline work. Freezing the rules before real metadata or header access prevents post-observation threshold changes.
**Status:** Fourteen portable tests and the final ArcGIS Pro 3.7.1 synthetic attempt pass; a deliberate VV/VH width mismatch blocks. Six prepublication attempts remain visible, including one failure with five retained synthetic files and one pass superseded when publication review found an unsafe ArcPy fallback on the pre-ArcGIS block path. The exact gate was then published as commit `87aa2610f1a89fe2d612f9cdd6cb88e63e833c8d` and passed public CI run `33905019294` before its one real invocation. See D-053 for the retained result.

## D-053 — Preserve the real radar input-readiness block without tuning or retry

**Decision:** Record the exact published-contract result as **BLOCK** and retain it without changing the observed label, threshold, or decision semantics. Do not rerun the current contract.

**Reason:** All three source inventories, all six annotation structures and embedded-vector checks, and all six ArcGIS TIFF-header reads passed, but every real annotation reported `pixelValue` as `Detected`; the frozen contract required `AMPLITUDE`. Changing the rule after observing the data would erase the failed route rather than evaluate it.

**Status:** Receipt SHA-256 `feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c` is retained. Independent post-run verification found all three 29-file attempt inventories exact, all 78 SAFE files and 5,183,550,209 bytes unchanged, and no added sidecar. No pixel, baseline, change, or scientific claim is released. Any proposed correction must first cite an authoritative Sentinel-1 product specification and undergo separate review.

## D-054 — Prepare a source-bound one-field amendment without activating it

**Decision:** Use the official Sentinel-1 Product Specification and processing page to prepare a review-only proposal that replaces the failed contract's `AMPLITUDE` schema label with `Detected`, while preserving the physical interpretation as detected amplitude and leaving every other gate rule unchanged.

**Reason:** The specification's `pixelValueType` domain is `Complex` or `Detected`, and the image-information field uses those same labels. The processing description separately explains that GRD values represent detected amplitude. The original contract conflated those two layers, but changing a rule after seeing real inputs requires explicit owner review and a clear post-observation limitation.

**Status:** The source gate is ready for metadata and review preparation only. Proposal SHA-256 `ebdcb763afd99ea23090c9bd83fd9e9cb6cb8dfbb2b5fed60edb80f1fa61c731` and review bundle SHA-256 `831df5d5aae06862514667ad861c815154085fa3c546039e60f517d38ee442ff` are exact. The blank response contains one item, zero decisions, and no attestation. No corrected contract, test run, publication, real-002 inspection, pixel use, or baseline action is authorized.

## D-055 — Freeze candidate-change and cross-route semantics before post-event pixels

**Decision:** Predeclare separate optical and radar candidate thresholds using locked stable-reference zones, median/MAD normalization, existing coverage and registration gates, a 5,000-square-metre minimum mapping unit, and complete dispositions for all three routes. Treat overlap as spatial coincidence, preserve disagreement and untestable routes distinctly, and keep every automated class at the observation-candidate level.

**Reason:** The project had fixed inputs, preprocessing, and pixel QA but no immutable boundary for turning continuous deltas into mapped candidates. Choosing controls after seeing a dramatic event could bias the map, while merging missing coverage with disagreement or candidate agreement with attribution would overstate the evidence.

**Status:** The contract and protocol are prepared with no real-processing authority. Twelve portable synthetic tests pass. No satellite pixels were read, no candidate feature was created, and interpretation, attribution, scientific admission, and publication remain separate later gates.

## D-056 — Approve one secret-safe detached Sentinel recovery-002 route

**Decision:** Accept the exact recovery-002 bundle and proposal and release only their bounded detached-worker implementation, synthetic interruption and secret-exposure tests, public-CI gate, one fresh byte-zero `M1-SRC-004` attempt, and passing-recovery continuation of the four named unattempted products.

**Reason:** The recovery-001 process disappeared before terminal evidence, leaving a second incomplete partial and an unknown cause. A detached supervisor with nonsecret heartbeat and terminal records makes console closure survivable and absent-worker state independently reconcilable while keeping the token out of command lines, environment variables, files, logs, and repository evidence.

**Status:** The exact response is locked and reconciled. Local implementation validation is passing. A real token handoff and transfer remain blocked until the exact commit passes public CI, the publication gate is recorded, activation succeeds, and the final no-payload preflight passes. Any recovery-002 failure is terminal and cannot be retried automatically.

## D-057 — Reconcile the successful recovery separately from the stopped continuation

**Decision:** Record `M1-SRC-004` as promoted and container-verified only through its successful recovery-002 identity, preserve both earlier failed partials, and retain the detached supervisor's later `continuation_live_preflight` terminal event as a separate failure. Do not restart the supervisor or request another product under the completed run. Prepare a new continuation-only owner review that explicitly forbids another `M1-SRC-004` request.

**Reason:** The byte-zero recovery completed with exact length, local SHA-256, provider MD5, ZIP CRC, and required SAFE-member checks. The same supervisor then emitted a generic terminal failure before any `M1-SRC-005` attempt, event, staging path, destination, or payload request existed. Because its exception boundary did not retain a safe underlying category, the exact cause is unknown and cannot be reconstructed from later checks.

**Status:** Outcome reconciliation SHA-256 `f806d86e6c956e648f4458f4710699d4480e2b0abfb2cf95e8777f3de281b3f4` updates the active intake to four promoted and four authorized products while preserving both failed partials and the failed supervisor terminal state. Continuation proposal SHA-256 `d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1` and review bundle SHA-256 `018adc5c9edad48beb665f717c0c39fc5b63b93c0127c1f571df59d30c25f192` are ready with a blank, unattested response and zero decisions. No continuation implementation, token entry, payload request, retry, or pixel action is currently authorized.

## D-058 - Preserve failed review publication and rebind canonical LF packet

**Decision:** Retain failed public workflow run `33935109759` and commit `46aafc5249f7199308b46cb1d4c8375beecd84b5` as evidence. Supersede the unapproved CRLF-bound review identity from D-057 with canonical-LF review bundle SHA-256 `382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b`; proposal SHA-256 `d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1` is unchanged.

**Reason:** Git normalized three new review JSON files to LF on publication, so the first contract bound local CRLF bytes that did not exist in the public commit. Hash-bound review evidence must identify the public bytes exactly.

**Status:** The corrected packet remains blank and unattested. This correction creates no implementation, credential, acquisition, retry, pixel, or scientific authority. Public CI must pass on the corrected commit before owner handoff.

## D-059 — Approve the exact bounded Sentinel continuation

**Decision:** Accept continuation-001 review bundle SHA-256 `382d2238b7d27269604cc07134edfa29c9a3464d2c7c3b65163ceccab35e3f9b` and proposal SHA-256 `d58706dc0961816191a76f420d993bdc28be8f140358dc1638f6cc937366e7b1`. Release only the reviewed continuation-only implementation and proof, public-CI gate, final no-payload preflight, fresh anonymous-pipe credential handoff, and at most one attempt per source for `M1-SRC-005`, `M1-SRC-006`, `M1-SRC-008`, and `M1-SRC-010` in that order with stop on first failure.

**Reason:** Recovery-002 established a valid `M1-SRC-004` archive, but its supervisor then failed before any continuation attempt and retained no safe exact exception category. A separate exact decision was required to continue without treating that stopped process as reusable authority.

**Status:** The completed response is locked at SHA-256 `add004d26f7a35ed1b657089dae1c1f68f01eba495c0c4edb35cee943a13cb39`. Approval record SHA-256 `93f451f458c5b4984f980049f5adadf73e52663c8a71ee9699939b7f85e727a1` and reconciliation SHA-256 `420f525d160a1b95f6784da06a0ca95ddf8e6e8e37d7947925f6c865157d28a6` preserve one approval, zero revise/defer decisions, and the attestation. No `M1-SRC-004` request, partial reuse, retry after failure, token storage, pixel action, or scientific action is authorized.

## D-060 — Require public proof for the continuation-only worker

**Decision:** Implement a separate broker, detached supervisor, exact-order source wrapper, activation recorder, no-payload preflight, and success reconciler bound to D-059. Require a clean exact public commit and passing CI before activation, token entry, or payload access.

**Reason:** The earlier supervisor's generic failure erased the useful safe error category. The replacement must preserve nonsecret phase and terminal evidence, survive broker-console interruption on Windows, prevent secret propagation through arguments, environment, files, and errors, and prove the fixed one-attempt sequence before real use.

**Status:** Twenty-three focused tests and 317 full repository tests pass locally. Current readiness receipt SHA-256 `f52d989352541a1fb28dacf858fd14408de28bde84fcb9355154ea623df48fad` supersedes retained attempt-001 SHA-256 `86af300807b6db28e97deb6b8188d609f02bf0bed3044741e1eb124eddc28c48` after adding the exact prelaunch Git-state boundary. Public CI, activation, final no-payload preflight, credential entry, and all four payload attempts remain pending.

## D-061 — Preserve failed implementation publication and isolate the synthetic test

**Decision:** Retain exact commit `114cb663dbaf13bd286d26f92167ea4a9b7ec420`, failed public CI run `33942595168`, and readiness SHA-256 `f52d989352541a1fb28dacf858fd14408de28bde84fcb9355154ea623df48fad`. Change only the synthetic live-preflight failure test so it creates temporary custody and staging roots on every platform, then issue a new readiness identity and require a new public run.

**Reason:** The public repository validator passed, but Linux could not resolve the Windows external custody root before the test reached its mocked legal-page failure. The test therefore depended on owner-machine external state even though it was intended to prove a fully synthetic pre-attempt boundary.

**Status:** Failure record SHA-256 `17035284194fad3645f95d2162a6ff639f6743e2d849c67fce4e3505340cc2f0` preserves the failed run and confirms no activation, token request, payload request, or external product mutation. The isolated correction passes 23 focused and 317 full tests locally. Readiness SHA-256 `35bb375543dc2add5e66e80019ee7bc4eb70cee2f2cc3a4c8cf542c97369919a` is current; public CI remains pending.

## D-062 — Reconcile the completed Sentinel transfer cohort at M2-VERIFY

**Decision:** After portable correction commit `68ac0484d598790cc8c47a8747a674b7d5d9de73` passed public CI run `33942997642`, activate the approved continuation, pass one fresh token through the anonymous-pipe broker, and execute exactly one attempt each for `M1-SRC-005`, `M1-SRC-006`, `M1-SRC-008`, and `M1-SRC-010` in the approved order. Admit the result only after independent archive, transfer-receipt, and container-receipt reconciliation.

**Reason:** The completed owner decision authorized this exact continuation after public proof and a final no-payload preflight. Each transfer reached a distinct terminal success and passed the predeclared container-only gate. Advancing the checkpoint requires preserving those facts without treating archive custody as pixel readiness or erasing earlier failed attempts.

**Status:** Detached supervisor `m2-sentinel-continuation-001-20260905t041158z-ca2f8e75` ended with `continuation_001_all_four_succeeded`. Post-success reconciliation SHA-256 `ab11ba63fcd8765f7fbddd5b7601bb835446674f0f205a2d4ecba138ac27047e` binds all eight promoted archives, all eight passing container receipts, the exact four continuation attempts, and both retained incomplete `M1-SRC-004` partials. Two post-success validation attempts remain preserved because stale control and cross-workstream test assumptions still described earlier states; neither affected acquisition. The current checkpoint is `M2-VERIFY`: only three sources are materialized, five remain unmaterialized, and no pixel decoding, baseline, orbit recovery, change analysis, or scientific publication is released.

## D-063 — Prepare the exact materialization and pixel-readiness route for owner review

**Decision:** Prepare, but do not activate, one hash-bound owner packet for a dependency-ordered M2 route: five exact one-attempt SAFE materializations, one six-source radar and one two-source optical header inspection after published implementation proof, and one conditional optical pixel-readiness measurement for the exact RUM pair and three approved AOIs. Exclude radar pixel decoding, orbit and DEM work, baselines, change analysis, source or date substitution, retries, and scientific publication.

**Reason:** All eight archives are now in verified container custody, but five lack ordinary SAFE materializations and the project has no complete real before/after header or pixel-readiness result. Binding the exact source order, attempt identities, prerequisites, QA scope, and stop rules before further access prevents container success from being mistaken for usable pixels and prevents the high-cloud optical route from being rescued by date shopping after observation.

**Status:** Ready for review with zero human decisions. Review bundle SHA-256 `8da456e9e0a0e378210b3d9b017e88990f1711da334f27b4cd3886211a97369a` binds proposal SHA-256 `3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c`, no-mutation preflight SHA-256 `9a4ec0e286ab787194f76fa569293c67cc5db8529f96af9aba7e0959792af019`, and blank response SHA-256 `296916d31bdfbd248e27ca9fd03b7f6f0530269976fbf4accc3690bfb6965f0d`. No materialization, real header access, pixel read, network request, authentication, baseline, change result, or scientific action was performed or authorized by preparation.

## D-064 — Execute the approved dependency-ordered materialization and input-readiness route

**Decision:** Bind the owner's attested approval of review bundle SHA-256 `8da456e9e0a0e378210b3d9b017e88990f1711da334f27b4cd3886211a97369a` and proposal SHA-256 `3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c`, then execute only the released stages after each stage's implementation, synthetic, public-CI, and final-preflight gates pass.

**Reason:** Container custody did not establish ordinary SAFE extraction, native raster readability, pixel coverage, masks, or registration. The approved order preserved those distinctions and limited every real action to one attempt.

**Status:** Stage 1 public CI run `33984065216` passed before five exact one-attempt materializations succeeded in the approved order; reconciliation SHA-256 `71013b14363f941d41411dff24e5410a6f8682976f8ac9844ff2b2e9ec772d82` rehashed every materialized file. Stage 2 public CI run `33985362022` passed before the one six-source radar and one two-source optical header inspections both passed without measurement-pixel decoding; reconciliation SHA-256 `5bde8c6997e3c61b524f088a87d5cb1e484223a853ae81730cd2493f95c741d1` binds them. Stage 3 public CI run `33986585291` and preflight 002 passed before the single optical pixel attempt described in D-065. No radar pixel, baseline, change, attribution, or publication action was released.

## D-065 — Preserve terminal optical real-001 and require a new recovery decision

**Decision:** Classify `optical-pixel-readiness-real-001` as terminal `INVALID`, preserve its exclusive external root and repository receipt, prohibit retry under the completed authorization, and prepare a zero-decision review package for one separately identified correction and recovery attempt.

**Reason:** The runner read the first real SCL raster, then raised `KeyError: 'xmin'` because the production analysis grid stores bounds inside `analysis_grid.extent` while the synthetic target used flat fields. The failure occurred before AOI mask, registration, or other metrics. Correcting code after observing a real input and running a second attempt requires a new owner decision even though the scientific thresholds and source pair would remain unchanged.

**Status:** Real receipt SHA-256 `0f756c23ecaeaf017c196b0d79632960be5d249854d296f11fece639260d2164` and reconciliation SHA-256 `0e99672232d16208c77053e5343997c5dfc7ee4d4367ccaf68ee9eee13865e1a` record one invocation, no derived raster, no metrics, and no automatic retry. Recovery proposal SHA-256 `96f0125628e894061fc5da55faff94e92e51b0385293576177c1e15bd009b3da` and review bundle SHA-256 `d137b8ac1d46531ae42e7944955829eb2df37985428431b39863f4a157e83ac2` contain zero human decisions. No code correction or recovery attempt is authorized.

## D-066 — Activate the bounded optical pixel recovery after exact owner approval

**Decision:** Bind the owner's attested approval of review bundle SHA-256 `d137b8ac1d46531ae42e7944955829eb2df37985428431b39863f4a157e83ac2` and proposal SHA-256 `96f0125628e894061fc5da55faff94e92e51b0385293576177c1e15bd009b3da`. Release only nested production-grid normalization, exact-shape portable and ArcGIS synthetic tests, fresh public CI, one final no-pixel preflight, and at most one new append-only `optical-pixel-readiness-recovery-001` invocation with no automatic retry.

**Reason:** Real-001 established that the existing executor expected flat grid bounds while the frozen production contract stores them under `analysis_grid.extent`. The approved correction supplies a deep-copied execution view without changing the exact pair, AOIs, masks, registration method, thresholds, or prior result.

**Status:** Approval SHA-256 `983303532e95814828fd55d1f8c26c55d06d6785d579d236f8e5321072e8fcff` is active. Three pre-lock failures remain preserved: the original review contract omitted a required hash-prefix field, a PowerShell wrapper used an invalid parameter, and the first corrected contract omitted required post-review actions. The fourth lock passed against operational contract SHA-256 `552de54d12eca297ce94166453d697bea928a1b780803d8a111555bc29621761`. Ten portable tests and ArcGIS Pro 3.7.1 exact nested-shape synthetic receipt SHA-256 `34de82e63f7bb6b07f5925372cba69a7ca2aab5e129d6f8950852ffda23314a8` pass. Fresh public CI remains required; no recovery preflight or real invocation has started.

## D-067 — Retain the terminal optical recovery block without rescue

**Decision:** Classify `optical-pixel-readiness-recovery-001` as terminal `BLOCK`, preserve its append-only external outputs and public receipt, mark the one-invocation recovery authority consumed, and require a separately scoped owner decision for any alternate path. Do not retry, tune thresholds, substitute dates or sources, or begin baseline or change analysis.

**Reason:** The corrected implementation completed the fixed measurements. `AOI-SOURCE` was fully covered but only 0.063252 usable; `AOI-UPPER-CORRIDOR` was fully covered but only 0.256403 usable; and registration had 20 accepted control pairs with 0.508747-pixel RMSE, producing `DEFER`. The aggregate predeclared decision is therefore `BLOCK`.

**Status:** Commit `395b63e1bd5c53a39ca3e2601768ba5a00f4bcf4` passed public CI run `33989213698` before final preflight SHA-256 `d2d7eaf39ae67b0926de0c5e16d803eafcbdb0d076aab06c87d165d8f03ebb5e`. Real receipt SHA-256 `9ffae2e589700adec07373325e3d35d6ee8ccf5bc3a5d66da5fe7e6639c406b5` records one recovery invocation, a derived QA classification raster, metrics, no spectral indices, and no candidate change polygons. Reconciliation SHA-256 `445adfc716c97ef9122f699c28cb8193924c3863159cc91de511e56b72f7fb9f` rehashed the attempt, real-001, and both source materializations and released no retry or scientific admission.

## D-068 — Prepare a control-only radar-first path review

**Decision:** Preserve the terminal optical `INVALID` and `BLOCK` results, identify the aggregate-verification dependency conflict, and prepare a blank owner review for a radar-first control-path amendment. Do not modify the active scientific thresholds, query alternate optical dates, or treat the old orbit-recovery packet as actionable.

**Reason:** The approved materialization proposal predeclared optical and radar route independence. The current unapproved orbit-recovery proposal nevertheless requires full `M2-VERIFY`, which cannot complete while the optical branch is terminal `BLOCK`. That prerequisite now deadlocks the independent radar route before it can reach its separate DEM and orbit gates.

**Status:** Analysis SHA-256 `19672e1d646b5ee6131f57c99710c2483b9deb17743f833dd662edaa8afd128e`, proposal SHA-256 `ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77`, and review bundle SHA-256 `5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad` are ready with one blank item, zero decisions, and no attestation. Exact packet commit `b357e335cb1312c124384958ee5fd6512e184eeb` passed public CI run `33990934063`. Approval would release only the route-specific control correction and preparation of a corrected zero-decision orbit review. It would not authorize DEM conversion, software installation, orbit access, radar pixels, optical substitution, baseline, change analysis, attribution, or scientific publication.

## D-069 — Activate the radar-first control split and prepare corrected orbit recovery-002 review

**Decision:** Bind the owner's attested approval of radar-first bundle SHA-256 `5a5bd80f724841f9558ad5ff966ed0d49222419f7310b345492172e4639421ad` and proposal SHA-256 `ae2ddfa153a86b7acf7f8ec500690713d5ced9a8ddd58f5655d831e1eb282c77`. Preserve optical real-001 as terminal `INVALID`, recovery-001 as terminal `BLOCK`, and the old unapproved orbit proposal and bundle as stale evidence. Split only the control graph, bind the six exact radar sources to custody, materialization, and header readiness, and prepare a new zero-decision one-file orbit recovery review.

**Reason:** Aggregate `M2-VERIFY` cannot complete after the fixed optical route ended `BLOCK`, but the approved project design treats radar and optical as independent evidence routes. The six Sentinel-1 sources already have passing custody, materialization identity, and header-only evidence. Replacing the stale aggregate prerequisite removes that control deadlock without treating header readiness as pixel fitness or releasing any real orbit action.

**Status:** The completed response was locked at SHA-256 `6f571127b6c736aba227e699569f88fe7fc37401605d75222df1e956e3f44b55` and reconciled as one approval with no fabricated decisions. Approval record SHA-256 `e017099532a681f6c7d39afa8b7ab94c25e3c51495381363eaefd67a4533bdb9` activates only the control correction. Radar readiness SHA-256 `a582d33b697e8fd9868c265401d99e0f4748dd262f5f5b68189d8e7ffea0c389` records six sources and no pixel decoding. Stale-packet record SHA-256 `bf56645b5f18cb4bdf6fcaf0b7a279d6219e45080ecdabfc207f31ad95c4215d` preserves old proposal SHA-256 `ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a` and old bundle SHA-256 `df5aa9d0d03f8ee30a5cd74b91f74a88c83a525e762c22b0bd2b6773ccb5bc6b` as unapproved evidence. Corrected proposal SHA-256 `d30208c07deb66ef2c7487f8c901abd4fb5ff04aa56766bca8066d4c8d4f0db8` and bundle SHA-256 `6d43342b6bda2740667fa6e924a52f15313d8827cfb62563ea107bc483e87fa5` contain zero decisions. No catalog access, token read, payload request, DEM action, radar-pixel read, baseline, change analysis, attribution, or scientific publication occurred.

## D-070 — Approve bounded M2-ORB-001 recovery-002 implementation

**Decision:** Bind the owner's exact attested approval of bundle SHA-256 `6d43342b6bda2740667fa6e924a52f15313d8827cfb62563ea107bc483e87fa5` and proposal SHA-256 `d30208c07deb66ef2c7487f8c901abd4fb5ff04aa56766bca8066d4c8d4f0db8`. Release only recovery-only implementation, synthetic secret-exposure tests, public CI, one final no-payload preflight, and one fresh byte-zero attempt for exact `M2-ORB-001`.

**Reason:** The retained first request received zero payload bytes and used no owner credential. A separately identified recovery can test the exact product while preserving that failure and the route-specific radar prerequisite.

**Status:** Approval SHA-256 `ee5922426882b5620f2e90e6703d0eb7d5f5ab77ede3ed61acfb8616b2c22d07` and reconciliation SHA-256 `b289cd6486ea819c22823fba986702c6e3b353171bff87bc437a67c6bfa0e3ab` bind one approval and zero revise/defer decisions. Twelve focused tests and the full 395-test repository suite pass locally. The first implementation publication run `33996953195` failed only because a Windows PowerShell parser test was invoked on Linux; no gate, activation, credential, payload, or external-data action followed. The corrected test remains active on Windows and skips only the unavailable executable on other platforms.

The first owner token handoff after successful CI stopped locally because the broker removed only LF and retained the carriage return from PowerShell's CRLF line ending. Failure receipt SHA-256 `c8ebff040e6f7f9b03091342c73d5ce09691e03d614134d4788fd872b32c055e` records no supervisor, attempt ID, catalog request, payload byte, destination, or external-data mutation. The correction accepts only LF or CRLF framing while preserving the token's internal-whitespace rejection and anonymous single-use pipe. Twelve focused tests, nine orbit I/O tests, and the full 395-test suite pass locally. Fresh successful public CI, reactivation, and final no-payload preflight remain required before the owner may choose another handoff. Requests for `M2-ORB-002` through `004`, automatic retry, precise-orbit substitution, DEM action, orbit application, radar pixels, baseline, change analysis, attribution, and scientific publication remain unauthorized.

## D-071 — Preserve terminal recovery-002 and prepare a distinct recovery-003 review

**Decision:** Record the one recovery-002 owner handoff as terminal and consumed after its detached supervisor failed in a bounded local pretransfer window. Preserve the supervisor journal, empty exclusive payload-parent directory, unchanged active intake, and prior orbit failure. Prepare a separate blank recovery-003 review with a new namespace and staging root; do not infer missing diagnostics or retry recovery-002.

**Reason:** The supervisor journal proves that exact public catalogue revalidation returned, but the next local setup stage failed before an attempt event root, attempt ID, authenticated download, destination, or payload byte. The approved recovery-002 policy made any failure terminal for that identity. A new attempt therefore requires a new exact owner decision. The proposed evidence-first sequence would establish attempt-scoped evidence before later pretransfer stages, while retaining the same one-file, byte-zero, one-handoff, no-retry boundary.

**Status:** Outcome SHA-256 `3d0b6be8e09e0d9049c32c65461e321b2fdbd5db398dd9a6d1b08b62c6c51380` and terminal reconciliation SHA-256 `3ac47e6e57c7f2c27074910f6f5a41b432561fc59caad1a0dd75459aeff3abfc` record zero transfer attempts and zero payload bytes. Recovery-003 proposal SHA-256 `5aa4a0042024634a7ade191e0c5f36614216d8581a9c0535c0042be20583bfa3` and bundle SHA-256 `bc3cdc22d16251c77b26d9903036b4317221e2b01207aa9db26436bfd091fe9d` contain zero human decisions. Exact packet commit `70226497f72c8cbbc576608b8fc7f4cbcae18cc6` passed public CI run `34050115168`, so the exact owner decision is pending. No implementation, credential, catalogue, payload, DEM, radar-pixel, baseline, change, attribution, or scientific-publication authority exists.

## D-072 — Preserve terminal recovery-003 and separate OSV precision observation from interpretation

**Decision:** Record the one approved recovery-003 handoff and request as terminal without retry. Preserve the exact staged bytes, supervisor and attempt journals, public failure receipt, initial outcome-reconciliation refusal, and active-intake correction. Do not promote the file or reinterpret the frozen validator result.

**Reason:** The exact 639,533-byte `M2-ORB-001` file matches the provider MD5 and BLAKE3, but its final OSV timestamp is `2026-08-16T14:09:55.968171` while its whole-second validity stop is `2026-08-16T14:09:56`. The frozen predicate required literal endpoint coverage and returned `osv_times_do_not_span_validity`. The first outcome reconciliation then exposed a stale active-intake projection left at `staging` and `started`; a bounded evidence-only correction finalized it to the matching terminal failure before the existing reconciler passed.

**Status:** Outcome SHA-256 `f67b7307dfe82cb6f02a13003389f482c7c2a96342fab138f737a31c2ec2d503`, terminal control reconciliation SHA-256 `d70fe44d5a5a1cb8fa2ac6d5bb4aa5362a5a1c7bb1e8729bf959879c4b56548c`, and active-intake SHA-256 `74fa02b68e46bb0e2b7a6ad55fb306c2eb73589f5ea4e73f406ff087e29d3909` preserve the exact state. Recovery-003 made one handoff and one request, promoted nothing, and is consumed with no retry.

## D-073 — Prepare a zero-decision OSV precision amendment review

**Decision:** Prepare, but do not answer or activate, a bounded review for a maximum one-second OSV endpoint-consistency rule and conditional local promotion of only the already preserved `M2-ORB-001` staged bytes. Require public CI before owner review.

**Reason:** The Copernicus POD file-format specification uses whole-second header validity values and microsecond OSV values, while stating consistency without defining a numerical tolerance. A one-second maximum is therefore a local inference from representational precision and must be reviewed as a post-observation method change. The exact scene remains more than 6,350 seconds inside the declared interval, but that does not waive the review.

**Status:** Proposal SHA-256 `0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4`, bundle SHA-256 `71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7`, and contract SHA-256 `aeda5b43507f295fbc471e07c612555ebfc93a491e2ccd5b33a6c84a3d735ec0` contain one blank item, zero decisions, and no attestation. Approval would still require implementation, synthetic proof, public CI, a final no-network preflight, and one local validation. No credential, network request, retry, other orbit file, promotion, processing, or scientific authority currently exists.

## D-074 — Approve the bounded one-second OSV endpoint interpretation

**Decision:** Bind the owner's exact attested approval of review bundle SHA-256 `71b3eea557cbd027fecec299b8661ce555a8fa993bccd8ffaea8f525d79d01a7` and proposal SHA-256 `0eb9e60f3cd26365cc447eb007e28186470a778928730b055b633c5e88d344e4`. Release only the exact one-second endpoint-consistency implementation, synthetic tests, public CI, final no-network preflight, and one local validation with conditional no-replace promotion of the preserved exact `M2-ORB-001` bytes.

**Reason:** The observed 0.031829-second endpoint difference is smaller than the approved one-second representation-based tolerance, but changing the frozen literal validator after observing the file required a separately reviewed and versioned method decision. The amendment leaves the strict default unchanged for all unamended contracts and forbids a larger tolerance.

**Status:** Review reconciliation SHA-256 `1bdbf7a56533b67d9228f1c3545fcd5a65643eacce584a5796e7d80b8d0d1c3c` and approval SHA-256 `4a77a044475b6c940a4b58d4c4dbcf76730c06e63d18927eb717312a97667cf4` bind one approval and true attestation. Versioned contract SHA-256 `ee578c8cc7c4e27c28f6e8ea4d65b664ce1a22a33db57e06c10c9cccafbb928e` and readiness SHA-256 `c8e01e91cfb30485308e68f00d8eab53de0ca17de95d37002afbafe6591b324d` bind nine passing focused tests and 433 passing full-suite tests with three intentional skips. A later control-only correction with SHA-256 `dfa2cda515a12701c6a3b6678685681cb8935561db02d98cb79cf95970ca7cac` updates one stale orbit-acquisition status label without changing authority. No real staged bytes were read, no network action occurred, and no validation or promotion began. Public default-branch CI remains the next gate. Requests for `M2-ORB-002` through `004`, recovery retry, precise-orbit substitution, DEM action, orbit application, radar pixels, baseline, change analysis, attribution, and scientific publication remain unauthorized.

## D-075 — Accept one input-only M2-ORB-001 promotion and stop before remaining sources

**Decision:** After exact public CI and final no-network preflight, consume the approved amendment through one local validation and conditional no-replace promotion of exact `M2-ORB-001`. Preserve the recovery-003 staging bytes and both earlier failed attempts. Route the project to preparation of a separate zero-decision review for `M2-ORB-002` through `004` without requesting them.

**Reason:** The file's 0.031829-second final endpoint shortfall passes the approved maximum one-second rule while every unchanged identity, checksum, XML, OSV ordering, finite-value, unit, scene-binding, and margin check passes. This establishes controlled orbit-input fitness for one source only. The current amendment explicitly excludes the other three requests and all downstream processing.

**Status:** Commit `55397416ac902fac7ec46382cdc3904b53566478` passed public CI run `34056822125`; publication-gate SHA-256 is `c5b8bedd2f656acc8f464a880fae11dd0d936bf2c12ac3891275bb27c36ba3ea`. Final preflight SHA-256 `6060a52bc293ce4005bf0bc1a73df806a77fd51338784eb4e66b3b5151a9abbc` preceded the one local result at SHA-256 `9b3e45fe1d8fe0c9c6668287d7bfc2ec0f8e238d6e0730f04a8d99583eef9898`. Terminal reconciliation SHA-256 `6309ee02114a8a59d5c3b46ed29b4f5901dfdb009d47dccb314561664a6254dd` records one promoted orbit, three unrequested orbit identities, zero network actions under the local amendment, and no scientific result. The next checkpoint is `M2-ORBIT-REMAINING-SOURCES-REVIEW-PREPARATION`.

## D-076 — Prepare the remaining-orbit continuation review without releasing access

**Decision:** Prepare and locally validate a blank review for exact `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004` in fixed order. Propose one byte-zero attempt per source, stop on first failure, the proven secret-safe broker architecture, and a prospective maximum one-second OSV endpoint rule before those payload bytes are observed. Require successful public default-branch CI before owner review.

**Reason:** The original orbit amendment fixes all three source identities, but the consumed M2-ORB-001 recovery and precision amendments authorize no request for them. A separate bounded review preserves that boundary, predeclares the method before observation, and prevents an automatic continuation or silent extension of the post-observation M2-ORB-001 rule.

**Status:** Proposal SHA-256 `01a2c3521625f8f219909b8d69476dbc3355292ff12e59fd0917ed52bc371e8b`, bundle SHA-256 `f4712a3ffd65eb9cbd1955ccd854423607a384800931004ae10da174a4880dd6`, and contract SHA-256 `40c4a010e75306a3df997b55d0c68216f745a39622da48fc45566fc877936296` contain one blank item, zero decisions, and no attestation. Exact commit `998fb415a04e531c71d4ea49b554168bb99b2095` passed public CI run `34062485694`; publication reconciliation SHA-256 is `1b69eb39e6f06224541155209235dac21f36baeffb70194789a2ed71993a60c0`. One stale-assertion validation failure remains preserved, after which all 446 tests pass with three intentional skips and the 748-file checker passes. No implementation, credential, live query, payload request, custody mutation, orbit application, DEM or radar-pixel action, baseline, change analysis, attribution, or scientific publication is authorized. One exact owner decision is pending.

## D-077 — Approve and implement the fixed-order remaining-orbit continuation

**Decision:** Bind the owner's attested approval of bundle SHA-256 `f4712a3ffd65eb9cbd1955ccd854423607a384800931004ae10da174a4880dd6` and proposal SHA-256 `01a2c3521625f8f219909b8d69476dbc3355292ff12e59fd0917ed52bc371e8b`. Release only the fixed-order implementation, synthetic interruption, exact-order, stop-on-failure, and secret-exposure tests, and public default-branch CI at the current checkpoint. Retain final no-payload preflight, the one owner handoff, and the three one-attempt source actions behind that public gate.

**Reason:** Exact `M2-ORB-001` is already promoted and cannot be touched. The three remaining source identities are unattempted and require a sequence that cannot reorder, retry, resume, replace, or continue after a failure. The one-second endpoint rule is prospective for only these three sources.

**Status:** Locked response SHA-256 `692f9ef93a7fd43adc76001cc0c6b5fd5dd5738ad840f91bcdb42d446ace0f04`, reconciliation SHA-256 `11e29c1e6a259201b745b802f59219234e4bfec2433f1caf909f2202e3b9f0fa`, and approval SHA-256 `66c40db57082ed29c1dfd3e00a163ab072fe9f14b8e0ed4455df188673de84ba` bind one approve, zero revise/defer, and true attestation. An invalid first lock filename is preserved as a no-read/no-lock failure. Projection-correction SHA-256 `cf76b0a532f1ab27d5298446218a06d96620d049d2f3bdf98c9abbf284a51e17` adds two omitted active-amendment pointers without changing authority. The initial implementation passed 24 focused tests and all 470 repository tests; readiness SHA-256 `184d7b6308bd90a79ce472f0c1032354459f83324e8900b24292b46474128a33` records zero network, authentication, payload, custody, and real-attempt actions. Exact commit `e64acfb566bdd807816744f91fff058384ddf327` passed public CI run `34065152165`, but activation stopped before outputs on a publication-recorder/validator assertion-key mismatch. Gate-attempt SHA-256 `fb5b051daedda020e6a925ae67380ef06fa8b77f07b19b221568f22455501377` and failure SHA-256 `ccc8a18f3ff70b16b6c4a31e5fab262e3a8eccf436082be9ab2230c16a311aa8` preserve it. The corrected validator and compatibility test pass 25 focused and 471 full-suite tests; readiness-002 SHA-256 `707875a46ffccc5793829a3bf66e585d67b712ecf049c080f1520f0e69c799b5` is current. Corrected commit `aec406019e0caf8056352bc675ffd02a487a8b9f` failed public CI run `34065435604` because Git normalized the historical activation-failure receipt from its exact local bytes. Failure SHA-256 `25546f8192eb8a19ad1c778703e6a00ac7e31ffa1f8f94464e787bacf9fa6ffc` records zero gate, activation, final preflight, credential, authentication, catalogue, payload, handoff, or external mutation. The original receipt is now explicit non-text custody, and a fresh public CI pass is still next.

## Orbit continuation-001 completion and offline verification gate — 2026-09-07

The approved continuation consumed exactly one owner handoff and one byte-zero attempt per `M2-ORB-002`, `M2-ORB-003`, and `M2-ORB-004`, in that order. All three requests passed exact catalogue, checksum, XML, OSV, scene-binding, staging, and no-replace promotion checks. No retry occurred and `M2-ORB-001` was neither requested nor mutated. Success reconciliation SHA-256 `039f635252c394dfda6f3a2e33918947e4579b7f10d48f1d89574fd2aba7fbc9` records the terminal result.

A first project-control reconciliation stopped before mutation because its guard expected a shortened activation status; failure SHA-256 `4dfebba0750768764a144b83142af84e45706e6a48cb48103063d24f235e0333` is retained. The corrected reconciliation, SHA-256 `65999a0db7fdc9d54ab10637c94edb15b8d603baf1337f18997322ca94fc87c4`, advances only to `M2-ORBIT-VERIFY-IMPLEMENTATION`. The exact four-source verifier projects the owner-approved maximum one-second OSV endpoint rules and the two authorized receipt formats. Real EOF reads remain blocked until this implementation passes public default-branch CI, is activated, and passes a final no-content preflight. Orbit application, DEM or radar-pixel action, baseline, change analysis, attribution, and scientific publication remain outside this decision.
