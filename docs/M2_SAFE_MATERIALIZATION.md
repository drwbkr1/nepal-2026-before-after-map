# M2 controlled SAFE materialization

## Purpose

The eight approved Sentinel products arrive as ZIP archives. ArcGIS raster and metadata inspection requires ordinary files under an extracted `.SAFE` directory, but extraction must not weaken the verified archive identity or hide partial work. `contracts/m2-materialization.json` therefore defines the offline transition from one passing container receipt to one append-only external SAFE attempt.

This control inherits the approved M2 `data_processing` authority. It does not add products, grant network access, authorize a DEM, or create scientific admission.

## Required upstream evidence

One source may materialize only when all of the following are true:

1. the source is one of the eight exact products in the approved acquisition plan;
2. the active intake asset is `promoted` with exactly one successful transfer attempt;
3. the matching per-product container receipt is `pass_container_only` and is bound to that attempt;
4. the promoted archive's current byte count and SHA-256 still match both the intake record and container receipt;
5. the active M2 contract still includes `data_processing` under the exact approval.

The runner verifies its own code and contract inputs before reading custody. It makes no network request and performs no authentication.

## Output custody

Complete and incomplete attempts remain outside Git under:

```text
C:\Projects\Active\nepal-2026-before-after-map-data\materialized\
  <source-id>\
    <materialization-attempt-id>\
      started.json
      <exact-product-id>.SAFE\...
      materialization-manifest.json
      completed.json
```

An attempt directory is created exclusively and is never reused. If extraction fails after creation, its partial bytes remain with `failed.json`; they cannot be relabeled or overwritten by a later attempt. A complete external manifest records every extracted relative path, byte count, ZIP CRC, and SHA-256. The lightweight public receipt binds that manifest without placing raw SAFE files in Git.

## Member safety

Before any materialization output directory is created, the full ZIP namespace is checked again. The runner rejects:

- absolute, parent, dot, empty, or backslash paths;
- files outside the exact `.SAFE` root;
- encrypted or symbolic-link members;
- case-insensitive duplicates and file/directory collisions;
- Windows reserved names, alternate-data-stream colons, forbidden characters, and trailing dots or spaces;
- member-count, single-file-size, or total-expansion limits outside the active verification controls.

The same checks repeat immediately before extraction. Files are written with exclusive creation, hashed while decompressed, and size-checked. The source archive is hashed again before a complete manifest is written, so a concurrent archive change leaves a retained failed attempt instead of a passing marker.

## Invocation after the gates pass

After one exact transfer and its container verification pass, use a new lowercase attempt identifier and a current RFC 3339 UTC timestamp:

```powershell
python scripts/materialize_m2_product.py `
  --source-id M1-SRC-001 `
  --attempt-id mat-20260903t190000z `
  --started-at-utc 2026-09-03T19:00:00Z
```

Do not run this command for an unpromoted product or substitute a different source. At the present checkpoint, the runner stops on `asset_not_promoted` before custody access or materialization output.

## Validation and claim boundary

Fourteen portable tests cover deterministic derivation, the exact eight-product boundary, executable hashes, successful synthetic extraction, per-file hashes, traversal, ambiguous paths, backslashes, Windows device and ADS names, case collisions, file/directory collisions, symbolic links, no-replacement behavior, and the production wrapper's pre-custody refusal.

These tests use temporary synthetic ZIP files only. They establish no real archive materialization, raster readability, pixel usability, baseline, observable change, interpretation, attribution, or emergency guidance.
