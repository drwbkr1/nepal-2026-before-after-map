# ArcGIS Sentinel-1 baseline processing protocol

## Purpose

This protocol fixes the intended Sentinel-1 preprocessing route before product pixels are available. It applies independently to the ascending path 85 and descending path 121 pairs in `config/qa/candidate-pair-plan.json`. A parameter declaration is not a processing result: no Sentinel or DEM pixel has been processed under this protocol.

The machine-readable contract is `config/qa/radar-baseline-processing-contract.json`.

## Input gate

Processing may begin only after all six exact Sentinel-1 products have promoted custody and offline-verification passes, all four exact DEM tiles have promoted custody and structural-verification passes, the DEM amendment is active, and scene-level pixel readiness is sufficient. Any extra Sentinel, DEM, orbit, or geoid-grid source is outside this contract.

The two orbit directions remain independent evidence routes. Same-date slices in the ascending route are assembled only after each slice passes identity and structural checks; seam and coverage failures remain visible.

## Fixed primary processing chain

The primary quantitative route uses ArcGIS Pro 3.7.1 Image Analyst and preserves linear backscatter:

1. validate source identity and inspect embedded orbit metadata;
2. remove thermal noise;
3. calibrate each VV and VH band to beta nought;
4. apply radiometric terrain flattening to gamma nought and retain the scattering-area, geometric-distortion, and native distortion-mask outputs;
5. apply geometric terrain correction to EPSG:32645 at a candidate 10 m cell size, using bilinear resampling for continuous backscatter and nearest-neighbor resampling for categorical masks;
6. derive dB display and difference layers from positive linear gamma nought values, recording nonpositive values as NoData.

The primary quantitative route applies no despeckle filter. A fixed 7 by 7 Refined Lee route may be evaluated later as a labeled sensitivity or display product, but it cannot replace the primary route without a recorded decision.

## Orbit-vector gate

ArcGIS documents predicted orbit vectors in Sentinel-1 Level-1 products and recommends updating them to restituted or precise vectors when available. Those auxiliary orbit files are separate products and are not authorized by the current eight-product M2 boundary. The processing contract therefore:

- inspects embedded orbit metadata first;
- accepts precise or restituted orbit status for processing readiness;
- defers a predicted-only route;
- blocks missing or unreadable orbit metadata;
- leaves ArcGIS username, password, and cloud-storage-connection parameters empty;
- prohibits auxiliary orbit download under current authority.

If an external orbit file proves necessary, it must receive its own exact source and custody gate.

## Vertical-datum gate

The proposed Copernicus GLO-30 tiles contain orthometric elevations tied to EGM2008. ArcGIS documents its `GEOID` option as an EGM96 conversion and says `NONE` is appropriate only for ellipsoidal heights. Those models cannot be treated as interchangeable without evidence.

Production terrain flattening is therefore deferred until one route passes a documented evaluation:

- convert EGM2008 orthometric heights to ellipsoidal heights with a validated transformation source, then use `NONE`; or
- run a clearly labeled EGM96 sensitivity route with `GEOID`, retain the model mismatch as a limitation, and demonstrate acceptable stable-terrain and registration behavior.

Using the orthometric tiles with `NONE`, or claiming that ArcGIS’s EGM96 option exactly handles EGM2008, is prohibited. If preconversion requires another external geoid grid, that grid needs a source gate before access.

## Terrain-distortion masks

ArcGIS’s native distortion mask is retained. Its class 0 is excluded as undetermined; classes 1 and 2 are retained with their foreshortening or lengthening flags; class 3 is excluded as shadow; class 4 is excluded as layover; and class 5 is excluded while preserving the combined layover-and-shadow reason.

The project QA mask then adds border noise, residual speckle or unstable background, water variability, and registration exclusions. This translation preserves the native class so the simpler project mask does not erase the original terrain-geometry evidence.

## QA and claim boundary

The existing pixel-readiness contract still governs AOI coverage, grid compatibility, and registration. At least 30 stable-control pairs are required; a pass requires registration RMSE and absolute bias no greater than 0.5 pixel, while RMSE above 0.5 and no greater than 1.0 pixel remains deferred.

A processing or QA pass does not establish landscape change, geomorphic interpretation, event attribution, or emergency guidance. Those require later evidence records and review.

## Official method references

- [ArcGIS Generate Radiometric Terrain Corrected Data](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/generate-radiometric-terrain-corrected-data.html)
- [ArcGIS Apply Radiometric Terrain Flattening](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/image-analyst/apply-radiometric-terrain-flattening.html)
- [ArcGIS Sentinel-1 GRD workflow](https://doc.esri.com/en/arcgis-pro/latest/help/analysis/image-analyst/analysis-ready-sentinel-1-grd-data-generation.html)
- [Copernicus DEM documentation](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html)
