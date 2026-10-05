# Nepal imagery: a GIS workflow demonstration

This is an independent, unofficial GIS demonstration. It shows existing satellite imagery and an ArcGIS workflow; it does **not** identify validated landscape change or attribute a feature to the 26 August 2026 event. It is not an operational hazard map.

![Partial imagery demonstration with unverified registration and native cartographic cues](assets/gis-demonstration-cartography-001.png)

## What the panel contains

| Item | Before | After |
|---|---|---|
| Acquisition | 16 August 2026 | 28 August 2026 |
| Sensor | Sentinel-1D | Sentinel-1D |
| Source ID | M1-SRC-002 | M1-SRC-005 |
| Processing | ASF HyP3 RTC VV gamma0, displayed in dB | Same |
| Project CRS | WGS 84 / UTM zone 45N, EPSG:32645 | Same |
| Posting | 10 m | 10 m |

The displayed rasters were already generated under the earlier local visual route. Demonstration staging copies their bytes unchanged. It does not recalibrate, filter, warp, register, threshold or compute a difference between them. Posting is not a claim of 10-m positional accuracy.

The new demonstration uses the same fixed grayscale display range, **-30 to 0 dB**, for both dates, with no gamma stretch. This replaces the original panel's automatic percentile display with a shared presentation scale. It changes presentation only; source raster values and scientific criteria remain unchanged. A shared display scale does not establish radiometric normalization or registration.

The common valid VV/VH area is **54.6721% of the source-area AOI** and **75.7928% of the upper-corridor AOI**. The panel displays VV only. Blank areas represent exclusions for layover, shadow or NoData; they do not demonstrate an unchanged surface. The fractions use the original full-AOI denominators, and both full-area QA dispositions remain `defer` under the original 80% rule. Residual registration is unverified. Brightness differences can reflect radar geometry, moisture, scattering, speckle or alignment rather than event effects.

## Demonstration deliverables and verification

The owner-local working directory holds an editable APRX, two copied display GeoTIFFs, a source-manifest table, writable project defaults, PNG/PDF exports and package-test evidence. A PPKX is deliverable only after extraction and fresh-process reopen tests pass. Large GIS artifacts remain outside Git.

The repository contains the staging and package-test code, rights review, qualified preview when verified, and a sanitized result. Tests establish the recorded local mechanics, not scientific validity. Same-machine testing is not a clean-machine or cross-version acceptance test. This demonstration does not mark the original M5/M6 scientific acceptance criteria complete.

### Verified result on 5 October 2026

The initial working handoff was a **ZIP retaining the original display GeoTIFFs**. Its CRC and 65 manifest-file hashes pass, and copies at two new folder locations reopen with matching map structure, full-cell digests and rendered exports. Home folder, default geodatabase, toolbox and operational sources resolve inside the extracted folder. The owner-local ZIP is 43,547,880 bytes, SHA-256 `55b483b03358635757e857f7ee8e7d94bc496cb7103dc0346fd0792fdd6a7098`.

Four PPKX failures remain retained. The first exposed an omitted empty default geodatabase; the second exposed a standalone-table adapter error. After those corrections, both later candidates preserved the geometry, cell values and source table but failed exact rendered-export parity. Adding a common display scale did not resolve that mismatch. Those four PPKXs remain failed candidates. No scientific source was reacquired or reprocessed to make this demonstration.

See the [sanitized result](../records/readiness/gis-demonstration-001-result.json). Public CI verifies repository controls and software tests, not private GIS data. The local demonstration proof is the separate ArcGIS runtime record.

### Later PPKX result on 5 October 2026

A fresh fifth test used `PackageProject` with `sharing_internal='INTERNAL'`. For these strictly local inputs, it included the two original compressed GeoTIFFs byte-for-byte instead of converting them to geodatabase rasters. Both a first extraction and a second extraction at a different location passed fresh-process reopen, full-cell/georeference/source-table equality and exact rendered-layout equality. Project defaults and operational sources resolve inside each extracted folder. The preview is unchanged.

The owner-local PPKX is **41,797,549 bytes**, SHA-256 `044af3651f7505cfb02fdb7800afda0be7be19da873debea4bd055e393be4435`. It is now a verified **same-machine demonstration package**; the original ZIP also remains valid. Neither test establishes clean-profile, clean-machine or cross-version portability, real registration or scientific acceptance. The historical result records are not rewritten.

Internal packaging can leave network resources referenced, as described in the [official Package Project documentation](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/package-project.html). This verifier rejects network, service and out-of-root operational sources before packaging and after extraction. The passing result must not be generalized to projects with such sources. See the [additive PPKX result](../records/readiness/gis-demonstration-001-ppkx-preserved-format-result.json).

### Cartographic result on 5 October 2026

A separate fresh copy adds two native, map-linked true-north arrows, two kilometer scale bars, and a native shared VV legend. The bars show 0, 2.5, 5 and 10 km; they express projected distance, not positional accuracy. The legend labels match the existing fixed -30 to 0 dB display range. Both frame extents, scales and rendered imagery regions are unchanged. The page is now 13 by 8.5 inches; dates, coverage limitations and credits remain visible.

The first cartographic preview failed visual review because its native unit/legend settings did not serialize as intended. It remains a failed, retained preview. Corrected previews pass visual review. A timestamp-generation failure before a separate relocation extraction is also retained; no extraction ran in that failed reservation. These presentation corrections do not change pixels, masks, scientific predicates or prior evidence outcomes.

The latest owner-local PPKX is **41,799,678 bytes**, SHA-256 `f23dcb0e3cf6710eb32b38e0e87076e60e4f975f4699b8a594ea24d53188d63c`. It preserves both exact original display TIFFs. At two extraction locations, fresh-process tests pass full-cell/georeference/source-table equality, native cartographic metadata equality and exact rendered-layout equality. This is still a same-machine result, not independent-environment or scientific acceptance. The earlier preview and result records remain unchanged. See the [additive cartographic result](../records/readiness/gis-demonstration-001-cartography-result.json).

## Reproduce with your local verified inputs

ArcGIS Pro 3.7.1 was used. No cloud basemap, account, new download or installation is needed for these steps. The staging script checks the exact accepted hashes before it writes a new directory. Inputs must be the previously verified local panel rasters and repaired project, not substitute scenes.

```powershell
& $ArcGISPython scripts/stage_gis_demonstration_001.py `
  --project $VerifiedRepairedProject --rasters $VerifiedPanelFolder `
  --output $NewStagingFolder

& $ArcGISPython scripts/arcgis_demo_roundtrip.py run `
  --project "$NewStagingFolder/Nepal_GIS_Demonstration.aprx" `
  --source-root $NewStagingFolder --output $NewRoundtripFolder --sharing INTERNAL
```

To add the native cartographic cues, refine a fresh staged copy before packaging:

```powershell
$StagedProject = Join-Path $NewStagingFolder 'Nepal_GIS_Demonstration.aprx'
$StagedHash = (Get-FileHash -LiteralPath $StagedProject -Algorithm SHA256).Hash.ToLowerInvariant()

& $ArcGISPython scripts/refine_gis_demonstration_layout_001.py `
  --project $StagedProject --source-root $NewStagingFolder `
  --output $NewCartographyFolder --project-sha256 $StagedHash

& $ArcGISPython scripts/arcgis_demo_roundtrip.py run `
  --project "$NewCartographyFolder/Nepal_GIS_Demonstration.aprx" `
  --source-root $NewCartographyFolder --output $NewCartographyRoundtripFolder `
  --sharing INTERNAL
```

The refinement checks the two exact TIFF identities and rejects changed viewports or overflowing text/legend elements. It copies the project into a disjoint directory, changes only layout and legend presentation metadata, and leaves the source tree unchanged. The verifier separately compares layout metadata and rendered pixels so one cannot conceal a mismatch in the other.

Use new output folders. Preserve failed receipts; do not overwrite an existing attempt. Inspect the exported layout visually before sharing it. The staging script gives the project local writable defaults and includes two provenance rows in `SourceManifest`. The round-trip verifier rejects broken, remote or out-of-tree operational sources, checks the packaged structure and rendered pixels, and records file-identity changes.

`--sharing EXTERNAL` remains the script default, preserving the earlier call behavior. Use the explicit `INTERNAL` option only for the strictly local demonstration described here; both modes enforce the same source-boundary checks.

The verifier also compares full-cell digests, NoData-normalized array shapes, projected extents and presentation settings for each existing display raster before and after packaging. This is within-source packaging validation, not a before/after change calculation.

## Rights, credits and privacy

Public access alone is not a redistribution permission. The exact two provider VV metadata files allow credited use. The intended demonstration use was separately reviewed; the previously generated DEM is excluded. ASF requests product-specific acknowledgements and DOIs for publications and presentations ([ASF guidance](https://hyp3-docs.asf.alaska.edu/usage_guidelines/)). The underlying Sentinel notice permits lawful adaptation and public communication with the source/modification notice ([Copernicus notice](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice)).

Image credit: **ASF DAAC HyP3 2026. Contains modified Copernicus Sentinel data 2026, processed by ESA.**

Processing environment: [10.5281/zenodo.3962581](https://doi.org/10.5281/zenodo.3962581). GAMMA plugin: [10.5281/zenodo.3962936](https://doi.org/10.5281/zenodo.3962936).

Public material excludes credentials, account details, private correspondence, the owner's private planning context and restricted ancillary rasters. Code licensing does not relicense third-party imagery. The original failed, inconclusive and deferred routes remain in the evidence history; this demonstration changes the presentation purpose, not those outcomes.
