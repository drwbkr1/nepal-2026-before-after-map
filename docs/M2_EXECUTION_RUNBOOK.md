# M2 controlled-intake execution runbook

## Current boundary

M2 is active under `contracts/milestone-002.json`. The exact approval covers only the bounded actions in the reviewed plan. The live preflight passed at `2026-09-03T17:31:17Z`, and the approved empty external custody structure was initialized with receipt SHA-256 `12812d1c53e13ec287425f74a1988f5c0be7d0638f856c9606fddf1c1431fb09`.

The activation remains bound to:

- activation review bundle SHA-256 `e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d`;
- acquisition plan SHA-256 `6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d`.

The reviewed artifacts remain unchanged. Active intake, preflight, and custody records inherit that exact scope and do not broaden it.

The current checkpoint is `M2-AUTHENTICATION-REFERENCE`. No credential reference was present at preflight, no authentication occurred, and no product bytes were downloaded. Continue only through a secret-safe reference to an existing owner-controlled CDSE access token or authenticated session. Never place secret values in a command argument, chat message, repository file, receipt, URL, or captured output.

A separate DEM amendment was approved on 3 September 2026 through review bundle SHA-256 `caecbdfe69ec1a6c8c39401b63756005820a727cb8f9e7e0084753e2d6afb39e`, proposal SHA-256 `92f48680c0b779398d8bbebd872a60bc3850f008f5c9b68d5bf45a2448abdd69`, and license SHA-256 `9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd`. Its independent checkpoint is `M2-DEM-FRESH-PREFLIGHT`. It does not change the Sentinel authentication handoff.

## Prepared controls

`contracts/m2-intake-candidate.json` preserves the plan-derived pre-activation control. `contracts/m2-intake.json` is the active intake contract for the same eight exact products. It uses:

- sibling, non-Git custody and staging roots under `C:\Projects\Active\nepal-2026-before-after-map-data`;
- one unique staging path and final destination per product;
- `collision_policy: fail`;
- `promotion_mode: atomic-no-replace`;
- `secret_policy: references-only`;
- planned states with no transfer attempts;
- disabled resumption until byte-range support and an unchanged strong remote identity are proven.

`records/acquisition/m2-intake-static-dry-run.json` proves only that the reviewed product set can be converted into those static controls. It performs no filesystem probe and makes no network request.

`scripts/acquire_m2_product.py` handles one exact approved source ID per invocation. It requires `CDSE_ACCESS_TOKEN` to exist only in the process environment and stops before mutation when that reference is absent. It revalidates unchanged official access/terms page bytes and the exact live catalog identity, then writes an exclusive external started-event before payload transfer. It refuses redirects, existing staging or destination files, path escapes, reparse points, inadequate storage, unexpected HTML, and response-length drift. It streams directly to a unique `.part` path while computing SHA-256 and provider-MD5, preserves failures, and uses a same-volume hard link for atomic no-replace promotion.

The runner must never be invoked with a token on its command line. Once a secure environment reference exists, the first exact attempt is:

```powershell
python scripts/acquire_m2_product.py --source-id M1-SRC-001
```

This command has not been run against CDSE. `records/acquisition/transfer-runner-readiness.json` binds the current runner and eleven passing local fixture tests; it records no authentication or product transfer.

`records/acquisition/active-intake-initial-snapshot.json` preserves the exact activation-time state at SHA-256 `a2816e9244a0141bf797c3a3fba00e2d492e272fb4886e7ff9aff58ab3cb716c`. `scripts/validate_m2_acquisition_progress.py` treats that hash as historical identity and validates the current mutable intake separately. It accepts only the runner's authorized, staging, failed, and promoted states, requires immutable product identity and append-only attempt evidence, checks terminal receipts, and rejects secret-bearing fields. Add `--verify-external` to reconcile the local staging/custody paths and re-hash promoted bytes. The validator performs no network request and never reads `CDSE_ACCESS_TOKEN`.

After any terminal transfer attempt, run `python scripts/derive_m2_acquisition_checkpoint.py --verify-external`. It derives one explicit checkpoint from the validated state. If the tracked profile or long-term goal is stale, rerun with a new `--candidate-output-root scratch/<unique-attempt>` and review those candidates before applying the exact changes. Candidate output is scratch-only, exclusive, and does not alter authority or tracked files.

`contracts/m2-offline-verification.json` is the active read-only verification contract. After a transfer reaches `promoted`, run its exact wrapper with a new timestamp:

```powershell
python scripts/verify_m2_product_container.py --source-id M1-SRC-001 --scanned-at-utc <RFC-3339-UTC>
```

The wrapper refuses unpromoted assets, missing or ambiguous successful-attempt evidence, unexpected custody paths, and existing receipt names. A passing `pass_container_only` result remains ineligible for scientific use until the later raster, AOI, mask, baseline, and registration gates pass.

`contracts/m2-offline-verification-candidate.json` defines the read-only post-download checks for the same eight exact archives. It requires local SHA-256, provider-MD5 agreement, exact size, safe ZIP membership, CRC, exact SAFE root identity, and analysis-critical band, polarization, calibration, noise, and quality members. It does not access custody until a later explicit scan invocation.

`contracts/m2-materialization.json` defines the next offline step. `scripts/materialize_m2_product.py` refuses any asset without one exact promoted intake attempt and its matching `pass_container_only` receipt. It re-hashes the archive, rejects unsafe Windows and cross-platform member paths, and extracts into a new append-only external attempt while hashing every file. Partial or failed attempts remain visible. See [M2_SAFE_MATERIALIZATION.md](M2_SAFE_MATERIALIZATION.md). No real archive has reached this gate.

`config/qa/optical-input-readiness-contract.json` then keeps native raster-header readiness separate from pixel fitness. `scripts/inspect_optical_inputs_arcgis.py` requires both exact optical materialization receipts, re-hashes ten selected members per SAFE, parses baseline 05.12 scaling metadata, and checks sixteen JP2 headers and pair grids in ArcGIS Pro. A pass advances only to the existing pixel-readiness contract. See [OPTICAL_INPUT_READINESS_PROTOCOL.md](OPTICAL_INPUT_READINESS_PROTOCOL.md).

`records/readiness/m2-readiness-decision.json` preserves the historical pre-acquisition `defer`: no full products, pixel coverage, masks, or registration evidence existed. The later live source gate resolves only access-time source and rights checks; it does not alter the remaining data-readiness gates. See [M2_OFFLINE_VERIFICATION.md](M2_OFFLINE_VERIFICATION.md).

## Parallel DEM sequence

`contracts/m2-dem-intake.json` authorizes only `M2-DEM-001` through `M2-DEM-004`; all remain unattempted. `contracts/m2-dem-offline-verification.json` is active and offline but refuses raster access until a matching intake asset is promoted. Before any tile bytes are requested:

1. Re-fetch the exact license URL and require SHA-256 `9cd37d37ea654bbcaf0a2e059e6a3a5b5f76072824d8dd860ccf274ada8951bd`.
2. Revalidate each exact anonymous HTTPS object without redirects, authentication, requester-pays behavior, cost, or identity drift. Require the reviewed content length, ETag, last-modified value, and byte-range behavior.
3. Revalidate free space, path containment, absent destination and staging collisions, and no reparse-point ancestors under the approved external root.
4. Write append-only live-source and preflight receipts. Only a complete pass may advance `M2-DEM-ACQUIRE`.
5. Acquire one tile at a time through exclusive staging, compute local SHA-256, preserve all failures, and promote without replacement.
6. Run the active ArcGIS GeoTIFF verifier offline for each promoted tile. Structural readability is not valid-pixel or radar fitness.

Stop if the license bytes, object identity, route, access mode, cost, paths, or custody conditions differ. Do not infer a vertical-datum conversion or download orbit auxiliaries.

Regenerate or verify these bytes with:

```powershell
python scripts/prepare_m2_intake.py --created-at 2026-09-02T04:46:03Z --verify-only
python scripts/prepare_m2_verification.py --created-at 2026-09-03T16:43:33Z --verify-only
python scripts/validate_m2_acquisition_progress.py --verify-external
python scripts/derive_m2_acquisition_checkpoint.py --verify-external
python C:\Users\drewb\.codex\skills\intake-controlled-data\scripts\validate_intake_contract.py contracts/m2-dem-intake.json --project-root C:\Projects\Active --json
python -m unittest discover -s tests -v
python scripts/check_project.py
```

## Required sequence under the exact M2 activation

1. Lock and reconcile the exact completed owner response. **Completed.**
2. Recheck the current [CDSE OData product-download documentation](https://documentation.dataspace.copernicus.eu/APIs/OData.html#product-download), [token guidance](https://documentation.dataspace.copernicus.eu/APIs/Token.html), and [terms](https://dataspace.copernicus.eu/terms-and-conditions). **Completed for the recorded preflight timestamp.** Stop if later terms are new, changed, or require acceptance.
3. Re-query all eight provider UUIDs. Require exact product names, online status, catalog identity, and compatible access routes. **Completed for the recorded preflight timestamp.**
4. Perform the formal M2 storage and path preflight against `C:\Projects\Active`. Reject traversal, symlinks, case-insensitive collisions, existing destinations, inadequate free space, or unexpected roots. **Completed.**
5. Create custody and staging directories only after the activation and fresh preflight pass. **Completed with an append-only receipt.**
6. Use an owner-controlled existing authenticated session or account reference. Keep usernames, passwords, access tokens, refresh values, cookies, and authorization headers out of files, commands captured as evidence, logs, and Git.
7. Intake one product at a time. Append an attempt record before transfer and write only to its unique `.part` staging path.
8. Resume only if the server proves range support and the remote length plus strong identity are unchanged. Otherwise preserve the partial attempt and start a distinct attempt.
9. Flush and close staged bytes. Compute local SHA-256, compare available provider MD5 and BLAKE3 values with suitable verified tools, and run the fail-closed offline ZIP/container verifier. A successful HTTP response is insufficient.
10. Promote with a same-filesystem no-replace operation. Stop if the destination exists or the platform cannot guarantee non-replacement. Re-hash the promoted file and require equality with staged bytes.
11. Preserve failed, partial, corrupt, superseded, and inconclusive attempts. Never rewrite them into passing history.
12. Only `pass_container_only` products can advance to raster readability, pixel-level AOI coverage, rights confirmation, baseline creation, EPSG:32645 registration, and optical/radar QA. The container result itself is not a usable-pixel decision.
13. Materialize one passing archive into a new append-only external SAFE attempt. Require the complete marker and externally bound per-file manifest before ArcGIS raster access; retain any partial or failed attempt.

## Scientific boundary

Verified custody will not establish event change. Pixel usability, cloud and snow masks, radar layover and shadow, terrain correction, co-registration error, stable-reference behavior, and independent optical/radar evidence must still pass before change mapping. Observation, interpretation, and attribution remain separate review layers.
