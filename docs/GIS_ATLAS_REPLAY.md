# Replay the existing atlas

The five-map unverified atlas can be rebuilt with the published code and an owner-local **`Nepal_Unverified_Atlas_Replay_Inputs.zip`**. This capsule contains the unchanged brightness-project APRX, four existing TIFFs, source metadata geodatabase and local toolbox. It does not contain new imagery or a new scientific method.

Use the [current evidence bundle](GIS_EVIDENCE_CATALOG.md) for viewing and exporting. The replay capsule is a separate build input, not a replacement map delivery. Both large ZIPs remain outside Git.

## Prerequisites

- Git and the existing licensed ArcGIS Pro Python environment. The tested runtime is ArcGIS Pro 3.7.1; this recipe installs nothing.
- The owner-local replay capsule: **63,991,718 bytes**, SHA-256 **`e922acd6baee241c86f5b9040a5822a92590e25f62c8814e4bd4325de8223d12`**.
- A new writable directory. Do not use Program Files or overwrite an earlier attempt.

The capsule has 67 files: 65 original input files plus its README and input manifest. Its ZIP CRC, extracted inventory and every file hash were checked. The source APRX is SHA-256 `f9629911a0041980f25164d1514de20a4f18459da68a5694da11ca5110a68b39`. The builder independently checks that APRX, all four TIFFs and the exact approved projected AOI JSON before building.

## Run from a clean published checkout

Edit the first three paths for your machine. These commands obtain only public project code; they do not download satellite data or collect credentials. Stop on errors and preserve output folders and receipts.

```powershell
$ReplayCapsule = 'C:\Projects\Active\nepal-2026-before-after-map-data\gis-demonstration-001\replay-001\Nepal_Unverified_Atlas_Replay_Inputs.zip'
$ReplayWorkspace = 'C:\Projects\Active\nepal-atlas-replay'
$ArcGISPython = 'C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe'

if (Test-Path -LiteralPath $ReplayWorkspace) { throw 'Use a new replay workspace.' }
if (-not (Test-Path -LiteralPath $ArcGISPython -PathType Leaf)) { throw 'ArcGIS Python was not found.' }
$CapsuleHash = (Get-FileHash -LiteralPath $ReplayCapsule -Algorithm SHA256).Hash.ToLowerInvariant()
if ($CapsuleHash -ne 'e922acd6baee241c86f5b9040a5822a92590e25f62c8814e4bd4325de8223d12') {
    throw 'Replay capsule identity differs. Do not substitute inputs.'
}

New-Item -ItemType Directory -Path $ReplayWorkspace | Out-Null
$CodeRoot = Join-Path $ReplayWorkspace 'published-code'
$InputRoot = Join-Path $ReplayWorkspace 'inputs'
$AtlasRoot = Join-Path $ReplayWorkspace 'atlas'
$RoundtripRoot = Join-Path $ReplayWorkspace 'roundtrip'
$BundleRoot = Join-Path $ReplayWorkspace 'bundle'

git -c core.longpaths=true clone --no-checkout https://github.com/drwbkr1/nepal-2026-before-after-map.git $CodeRoot
if ($LASTEXITCODE -ne 0) { throw 'Public code checkout stopped.' }
git -C $CodeRoot config core.longpaths true
if ($LASTEXITCODE -ne 0) { throw 'Git long-path configuration stopped.' }
git -C $CodeRoot checkout --detach 6865f939c45c91a232404ad4c3b0a221ee0388b4
if ($LASTEXITCODE -ne 0) { throw 'Exact code revision checkout stopped.' }

Expand-Archive -LiteralPath $ReplayCapsule -DestinationPath $InputRoot
& $ArcGISPython (Join-Path $CodeRoot 'scripts\check_project.py')
if ($LASTEXITCODE -ne 0) { throw 'Repository controls failed.' }

& $ArcGISPython (Join-Path $CodeRoot 'scripts\gis_experiment_atlas_001.py') `
    --source-root $InputRoot `
    --aoi (Join-Path $CodeRoot 'config\aoi\approved-study-areas-epsg32645.json') `
    --output $AtlasRoot
if ($LASTEXITCODE -ne 0) { throw 'Atlas build stopped; retain its receipt.' }

& $ArcGISPython (Join-Path $CodeRoot 'scripts\arcgis_demo_roundtrip.py') run `
    --project (Join-Path $AtlasRoot 'Nepal_Unverified_Atlas.aprx') `
    --source-root $AtlasRoot --output $RoundtripRoot --sharing INTERNAL
$StrictRoundtripExit = $LASTEXITCODE

# The strict receipt can fail on ArcGIS system-field ordering. It is retained.
# The atlas-specific verifier checks exact named fields, geometry, rasters,
# layouts and renders. It rejects other differences; this is not a retry.
& $ArcGISPython (Join-Path $CodeRoot 'scripts\package_gis_experiment_atlas_001.py') `
    --verify-package --source-root $AtlasRoot --roundtrip $RoundtripRoot
if ($LASTEXITCODE -ne 0) { throw 'Atlas package comparison failed; retain all receipts.' }

& $ArcGISPython (Join-Path $CodeRoot 'scripts\package_gis_experiment_atlas_001.py') `
    --source-root $AtlasRoot --roundtrip $RoundtripRoot --output $BundleRoot
if ($LASTEXITCODE -ne 0) { throw 'Replay bundle sealing failed.' }

Write-Host "Rebuilt atlas: $AtlasRoot"
Write-Host "Sealed replay bundle: $BundleRoot"
Write-Host "Retained strict roundtrip exit code: $StrictRoundtripExit"
```

Long-path support is set only in the cloned repository. An initial replay checkout missed a long historical review filename; the missing exact committed file was restored after the failure was recorded. The original repository, historical review and Windows system configuration were not changed.

## What the replay establishes

The test rebuilds all five layouts, study polygons, source/method tables and layer files. It checks the four unchanged TIFFs, projected placement, exact displayed pixels, and a new package extraction/reopen. Package hashes can differ because native project/package files include path or generated metadata; map content and input raster identities are checked separately.

This is a **same-machine, clean-code, relocated-input** replay. It is not a clean-machine, independent-user, cross-version, scientific registration or landscape-change acceptance test. The source dates, existing masks, colors, thresholds and original scientific outcomes do not change. The measurement remains an unverified 28 August minus 16 August VV brightness difference, without geomorphic interpretation or event attribution.

The complete repository suite was also run in the clean Windows clone: 1,237 tests, one error and eight intentional skips. The retained error is a historical radar-contract metadata test: it finds the original private data folder but the strict loader requires the clone's corresponding sibling folder. That production boundary and its test remain unchanged. The focused atlas/catalog tests pass (portable: 11 run, two GDAL skips); the replay result records this narrower coverage rather than claiming the whole repository is portable.

The current evidence catalog remains bound to the original delivered PPKX and committed public records. Do not relabel a newly generated replay package as that original package or overwrite its historical catalog. Keep the replay receipt separate; the current viewing bundle remains unchanged.

Credits: **ASF DAAC HyP3 2026. Contains modified Copernicus Sentinel data 2026, processed by ESA.** HyP3 doi:10.5281/zenodo.3962581; GAMMA doi:10.5281/zenodo.3962936. Independent demonstration, no endorsement.
