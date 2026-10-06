# Five-map ArcGIS atlas

**Unverified GIS experiment:** five editable map views of the existing 16 and 28 August 2026 Sentinel-1D ASF HyP3 RTC imagery. All maps use WGS 84 / UTM zone 45N, **EPSG:32645**.

For closer comparison, use the [Leaflet viewer](GIS_SWIPE_VIEWER.md), with swipe, blink and brightness-difference modes. The atlas provides printable views and native ArcGIS layers alongside that viewer.

![Source-area search extent, with the two dates at equal scale](assets/gis-atlas-001-source_area_comparison.png)

## The five views

| Layout | What it shows |
|---|---|
| `regional_overview` | Approved regional search/review extent and available imagery; no added basemap |
| `source_area_comparison` | Two dated views centered on the approved source-area search extent |
| `upper_corridor_comparison` | Two dated views centered on the approved upper-corridor search extent |
| `evidence_map` | Existing unverified after-minus-before VV brightness difference |
| `limitations_map` | Existing included/excluded cells and the blank area outside the input grid |

Each layout includes dates, CRS, a legend explanation, linked kilometer scale bars and true-north arrows, source credits and the experiment label. The outlines are approved **search/review extents, not event perimeters**. No settlements, roads, impact footprints or landscape-change features are invented.

## Open and export

The latest owner-local handoff is **`Nepal_Unverified_Atlas_Complete.zip`**. Extract the entire bundle to a writable folder and open **`Nepal_Unverified_Atlas.aprx`** directly, or open the unchanged **`Nepal_Unverified_Atlas.ppkx`** and let Pro unpack it. Do not extract under Program Files.

The standalone APRX includes local writable home, geodatabase and toolbox defaults. A fresh ZIP extraction was opened in a separate ArcGIS Python process, with every operational source confined to that extraction; all five maps exported with identical rendered pixels. The PPKX, four TIFFs, existing PNG/PDF exports and [offline catalog](GIS_EVIDENCE_CATALOG.md) are unchanged. Keep all files together. Earlier ZIPs remain preserved. See the [standalone delivery result](../records/readiness/gis-demonstration-001-standalone-atlas-result.json).

In the Catalog pane, expand **Layouts**, open a layout, and use **Share → Export Layout**. The project contains five principal maps and two supporting dated maps. Existing PDF/PNG exports are in the bundle's `exports` folder.

The bundle also includes four unchanged GeoTIFFs, five `.lyrx` files, `Experiment.gdb`, `ExperimentMetadata.gpkg`, method notes and an artifact manifest. To add a standalone layer, open one of the `.lyrx` files. Keep `layers`, `imagery` and `Experiment.gdb` together: the layer files use relative connections. The GeoPackage holds three approved projected study polygons, two displayed-source rows and one method row. It contains no claimed event-change geometry.

The large GIS bundle stays outside Git. The [sanitized result](../records/readiness/gis-demonstration-001-atlas-result.json) identifies the package, exports and bundle by hashes.

## Read the colors

![Unverified brightness difference, blue for lower and orange for higher values](assets/gis-atlas-001-evidence_map.png)

Both dated images use the same fixed **−30 to 0 dB** grayscale. The difference is the previously calculated **28 August minus 16 August** value. Blue is lower, orange is higher; its display spans **−6 to +6 dB**. Stored values remain unclipped. The atlas does not calculate, clip, warp, filter or resample a new analysis raster.

On the limitations map, teal means both existing inputs have valid values; gray means either input is invalid. White outside the original grid has no observation. Those gaps are not evidence of no physical change.

<details>
<summary>Method limits and checks</summary>

Registration remains unverified. Brightness can differ because of alignment, radar geometry, moisture, scattering or speckle. There is no registration correction, normalization, thresholded detection, geomorphic interpretation or event attribution. The original full-area source dispositions remain `defer`; 10 m posting is not 10 m positional accuracy. The original M4–M6 scientific acceptance requirements remain unmet.

The handoff is tested in ArcGIS Pro 3.7.1 on the same machine, including fresh-process extraction, reopen and re-export. This does not establish clean-machine, clean-profile or cross-version portability. Five native PNG exports and five separately rendered PDFs are visually inspected. Earlier synthetic and cartographic faults remain retained rather than overwritten. Repository tests and CI are routine engineering checks, not scientific verification or presentation-release gates.

The generic package checker retained a failed strict-schema receipt because packaging moved the system `Shape_Length` and `Shape_Area` fields after the named attributes. A separate atlas check compares the exact field names and types independent of order, and additionally verifies polygon coordinates and named attributes. It passes along with exact raster bytes and rendered maps. The original strict receipt is unchanged; the scientific rules are not altered.

</details>

## Reproduce from the same existing outputs

Use the exact existing brightness-difference project and four TIFFs described in [the difference guide](GIS_BRIGHTNESS_DIFFERENCE.md). The build verifies their identities and the unchanged approved M1 projected AOI JSON before copying to a fresh directory.

```powershell
& $ArcGISPython scripts/gis_experiment_atlas_001.py `
  --source-root $ExistingBrightnessProjectFolder `
  --aoi config/aoi/approved-study-areas-epsg32645.json `
  --output $NewAtlasFolder

& $ArcGISPython scripts/arcgis_demo_roundtrip.py run `
  --project "$NewAtlasFolder/Nepal_Unverified_Atlas.aprx" `
  --source-root $NewAtlasFolder --output $NewPackageTestFolder --sharing INTERNAL

& $ArcGISPython scripts/package_gis_experiment_atlas_001.py --verify-package `
  --source-root $NewAtlasFolder --roundtrip $NewPackageTestFolder

& $PortablePython scripts/package_gis_experiment_atlas_001.py `
  --source-root $NewAtlasFolder --roundtrip $NewPackageTestFolder `
  --output $NewBundleFolder
```

Use new output directories and retain earlier results. The complete ZIP includes a README and per-file SHA-256 manifest; its extraction is checked against the bundle's file identities. This packaging is for the existing unverified experiment, not a scientific M6 acceptance run.

For a complete PowerShell recipe using a clean published-code checkout and the sealed owner-local input capsule, see [Replay the existing atlas](GIS_ATLAS_REPLAY.md). That same-machine replay reproduced all five map images exactly with relocated inputs and preserved raster bytes. The original viewing bundle remains unchanged.

To reproduce the standalone extension from its two exact preserved local inputs:

```powershell
& $ArcGISPython scripts/gis_standalone_atlas_delivery_001.py deliver `
  --bundle $ExistingEvidenceBundleZIP --project $ExactOriginalAtlasAPRX `
  --output $NewStandaloneBundleFolder

& $ArcGISPython scripts/gis_standalone_atlas_delivery_001.py inspect `
  --project "$NewStandaloneBundleFolder/extracted/Nepal_Unverified_Atlas.aprx" `
  --source-root "$NewStandaloneBundleFolder/extracted" `
  --output $NewDirectOpenCheckFolder
```

The builder requires evidence ZIP SHA-256 `247fe982f834d30dd612a5a25bad0d424c96ff265879da455a14cd228f8af0ab` and original atlas APRX SHA-256 `d92af6a2423c9b792a165451c26e7bfc01a5ba15b15a70cd54aa0fac12e95caa`, with its exact adjacent `Experiment.pyt` and XML. It writes a new disjoint directory, adds the standalone project and local toolbox, preserves all 109 other existing artifact files, and retains a terminal receipt. The second command checks direct open after sealed-ZIP relocation. This does not change the scientific schema, source selection, masks, arithmetic or prior results.

## Credits

**ASF DAAC HyP3 2026. Contains modified Copernicus Sentinel data 2026, processed by ESA.** HyP3: [doi:10.5281/zenodo.3962581](https://doi.org/10.5281/zenodo.3962581). GAMMA: [doi:10.5281/zenodo.3962936](https://doi.org/10.5281/zenodo.3962936). Independent demonstration; no endorsement. The unchanged-source rights review is recorded in [the demonstration guide](GIS_DEMONSTRATION.md).
