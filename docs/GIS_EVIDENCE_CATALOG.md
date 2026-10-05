# Offline evidence catalog

The [five-map atlas](GIS_EXPERIMENT_ATLAS.md) now has an owner-local evidence bundle: **`Nepal_Unverified_Atlas_Evidence.zip`**. It contains the same maps, raster values, layer files and ArcGIS project package, plus a catalog you can inspect without opening GitHub.

The catalog traces each dated raster, the existing difference and exclusion rasters, and the five principal layouts to their source identities and original records. It preserves selected unsuccessful routes alongside the usable experiment outputs. It does not add a new landscape-change feature or event interpretation.

## Inspect in ArcGIS

Extract the whole ZIP to a writable folder and open `Nepal_Unverified_Atlas.ppkx` as before. For the catalog, connect to the bundle's **`ExperimentMetadata.gpkg`** or add its attribute tables. CSV versions are in `evidence`; the same data is in `evidence/catalog.json`.

| New attribute table | Contents |
|---|---|
| `SourceIdentity` | Two exact original Sentinel-1 product IDs, acquisition start/end times, orbit metadata, RTC archive hashes, displayed-raster hashes and retained full-area dispositions |
| `EvidenceHistory` | Sixteen selected original record statuses, scope, repository paths and SHA-256 hashes |
| `ArtifactLineage` | Eighteen source → raster → layout → package links, with artifact and record identities |
| `CoverageHistory` | Six recorded individual-source and common-valid fractions using the original full-AOI denominators |
| `ClaimRegister` | The unverified sensor calculation, the unassessed interpretation boundary and the unassessed attribution boundary |

The original GeoPackage study polygons, displayed-source rows and method row are unchanged. All five new tables are **nonspatial metadata**, separate from the original scientific evidence schema.

## Read historical statuses in context

`Exact_Status` copies the original status literally. `Scope` describes what the record evaluated. A pass for archive integrity, software, display or packaging does not become a pass for scientific evidence.

The initial M1 source manifest is an identity snapshot from candidate review; its then-pending acquisition and approval fields are historical. `SourceIdentity` uses later RTC and pixel-QA records for its retained full-area `defer` state. The catalog includes the deferred original README predicate, later composite-provenance result, deferred radar coverage, inconclusive optical routes, blocked native-radar processing, and retained demonstration/package failures. Later usable presentation outputs do not erase those outcomes.

The catalog is **curated, not a complete inventory of every project attempt**. The original records remain in the repository and the selected byte-identical snapshots are under `evidence/records/<repository path>`. Snapshot hashes identify the committed bytes at `public_record_snapshot_commit`, avoiding working-tree line-ending differences. No private correspondence or new account data is included.

## Measurement and claim boundary

The measurement is the existing unverified **28 August minus 16 August VV brightness difference**. Coverage fractions are copied from their original recorded evaluations; no new mask, denominator, fraction or threshold is calculated. Source dates, masks, pixel values, display settings and scientific rules are unchanged.

No geomorphic interpretation or causal event attribution is added. Original scientific admission, real registration and independent-environment acceptance remain unresolved. This catalog improves traceability of the experiment and does not complete the original scientific goal.

## Rebuild the evidence extension

Use the complete original atlas bundle directory, whose existing artifact manifest must still match every file. The installed ArcGIS Python environment supplies GDAL; this command does not import ArcPy or decode imagery.

```powershell
& $ArcGISPython scripts/gis_evidence_catalog_001.py `
  --repo $RepositoryRoot --source-bundle $OriginalAtlasBundleDirectory `
  --output $NewEvidenceBundleDirectory
```

The builder refuses existing output directories and private/untracked record inclusion. It snapshots exact public records, checks lineage and dispositions, appends new attribute tables to a fresh GeoPackage copy, verifies that the original table rows/geometry and 85 existing artifact files are unchanged, and seals a new ZIP with file hashes and CRC checks. Original bundles and unsuccessful results remain preserved.

See the [public catalog](../records/readiness/gis-demonstration-001-evidence-catalog.json) and [sanitized bundle result](../records/readiness/gis-demonstration-001-evidence-catalog-result.json). The large GIS ZIP stays owner-local, outside Git.
