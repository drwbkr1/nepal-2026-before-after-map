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
