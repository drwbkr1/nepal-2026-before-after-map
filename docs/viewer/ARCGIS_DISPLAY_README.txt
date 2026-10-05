NEPAL IMAGERY - UNVERIFIED GIS EXPERIMENT
Visual comparison only.

Open in ArcGIS Pro
1. Extract the complete ZIP into a writable folder.
2. Keep each PNG, its PGW and its PNG.AUX.XML together.
3. Add before.png and after.png to the same map with Add Data.
4. Toggle layer visibility to compare the two dates at the same location.
   Use the editable APRX/PPKX handoff for the existing cartographic layout.

before.png: 16 August 2026, M1-SRC-002, Sentinel-1D ASF HyP3 RTC.
after.png:  28 August 2026, M1-SRC-005, Sentinel-1D ASF HyP3 RTC.
CRS: WGS 84 / UTM zone 45N (EPSG:32645), meters; grid north up.
Both layers use the original full display extent, not the browser's zoomed view.
Both PNGs are 3540 x 2880 pixels, with the same native PGW placement.
Display: VV gamma0, shared -30 to 0 dB grayscale.

These are unchanged rendered display images, not scientific measurement rasters.
PNG color values are NOT VV gamma0 or dB measurements. Resampling/stretching
the display cannot add detail. Blank areas are exclusions. Registration is
unverified; no difference, event boundary, change finding or attribution is
included. SOURCE.json retains dates, hashes and native extent.
Common valid VV/VH coverage: source area 54.6721%; upper corridor 75.7928%.

Image credit: ASF DAAC HyP3 2026. Contains modified Copernicus Sentinel data
2026, processed by ESA.
HyP3 environment: https://doi.org/10.5281/zenodo.3962581
GAMMA plugin: https://doi.org/10.5281/zenodo.3962936
Independent experiment; no agency endorsement.

Viewer and editable ArcGIS handoff guide:
https://github.com/drwbkr1/nepal-2026-before-after-map/blob/main/docs/GIS_SWIPE_VIEWER.md
World-file format:
https://pro.arcgis.com/en/pro-app/latest/help/data/imagery/world-files-for-raster-datasets.htm
Auxiliary spatial-reference metadata:
https://pro.arcgis.com/en/pro-app/latest/help/data/imagery/auxiliary-files.htm
