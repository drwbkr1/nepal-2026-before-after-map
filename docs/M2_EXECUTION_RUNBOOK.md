# M2 controlled-intake execution runbook

## Current boundary

M2 is proposed and not active. This runbook and the static intake packet do not authorize account use, authentication, external-directory creation, product transfer, extraction, or raster processing.

The pending owner decision remains bound to:

- activation review bundle SHA-256 `e8d105970d64c43d955ff459ba9e5d5a3a1e4fb4f95874aa67f384e6b293a35d`;
- acquisition plan SHA-256 `6261dc61061cb962f22163755047f080e309ed2d746cdcdd61e6cf61d7ec2a8d`.

The static controls added after that bundle do not change either reviewed artifact or broaden its scope.

## Prepared controls

`contracts/m2-intake-candidate.json` is a plan-derived controlled-intake contract for eight exact products. It uses:

- sibling, non-Git custody and staging roots under `C:\Projects\Active\nepal-2026-before-after-map-data`;
- one unique staging path and final destination per product;
- `collision_policy: fail`;
- `promotion_mode: atomic-no-replace`;
- `secret_policy: references-only`;
- planned states with no transfer attempts;
- disabled resumption until byte-range support and an unchanged strong remote identity are proven.

`records/acquisition/m2-intake-static-dry-run.json` proves only that the reviewed product set can be converted into those static controls. It performs no filesystem probe and makes no network request.

Regenerate or verify these bytes with:

```powershell
python scripts/prepare_m2_intake.py --created-at 2026-09-02T04:46:03Z --verify-only
python -m unittest discover -s tests -v
python scripts/check_project.py
```

## Required sequence after an exact M2 activation

1. Lock and reconcile the exact completed owner response. Do not infer activation from conversation, a blank form, or filenames.
2. Recheck the current [CDSE OData product-download documentation](https://documentation.dataspace.copernicus.eu/APIs/OData.html#product-download), [token guidance](https://documentation.dataspace.copernicus.eu/APIs/Token.html), and [terms](https://dataspace.copernicus.eu/terms-and-conditions). Stop if terms are new, changed, or require acceptance.
3. Re-query all eight provider UUIDs. Require exact product names, online status, catalog identity, and compatible access routes.
4. Perform the formal M2 storage and path preflight against `C:\Projects\Active`. Reject traversal, symlinks, case-insensitive collisions, existing destinations, inadequate free space, or unexpected roots.
5. Create custody and staging directories only after the activation and fresh preflight pass.
6. Use an owner-controlled existing authenticated session or account reference. Keep usernames, passwords, access tokens, refresh values, cookies, and authorization headers out of files, commands captured as evidence, logs, and Git.
7. Intake one product at a time. Append an attempt record before transfer and write only to its unique `.part` staging path.
8. Resume only if the server proves range support and the remote length plus strong identity are unchanged. Otherwise preserve the partial attempt and start a distinct attempt.
9. Flush and close staged bytes. Compute local SHA-256, compare available provider MD5 and BLAKE3 values with suitable verified tools, and run a deterministic ZIP/container test. A successful HTTP response is insufficient.
10. Promote with a same-filesystem no-replace operation. Stop if the destination exists or the platform cannot guarantee non-replacement. Re-hash the promoted file and require equality with staged bytes.
11. Preserve failed, partial, corrupt, superseded, and inconclusive attempts. Never rewrite them into passing history.
12. Only verified products can advance to band/polarization inventory, pixel-level AOI coverage, rights confirmation, baseline creation, EPSG:32645 registration, and optical/radar QA.

## Scientific boundary

Verified custody will not establish event change. Pixel usability, cloud and snow masks, radar layover and shadow, terrain correction, co-registration error, stable-reference behavior, and independent optical/radar evidence must still pass before change mapping. Observation, interpretation, and attribution remain separate review layers.
