# Projected imagery swipe viewer

## Open and use

The verified opening route is a loopback HTTP server from a complete local checkout. All renderer code and scene assets are bundled; there is no Internet imagery, basemap or account dependency. GitHub displays HTML source instead of running this viewer. Serve only the viewer directory:

```powershell
python -m http.server 8767 --bind 127.0.0.1 --directory docs/viewer
```

Then open `http://127.0.0.1:8767/index.html`. Stop this optional local server with Ctrl+C when finished.

Start with **Closer view**, drag the divider, and use **Blink dates** to compare one location. The native slider also supports arrow keys and Home/End. Use **16 Aug only** or **28 Aug only** for manual switching; **Overview** restores context. Zoom buttons and pan remain synchronized because both dates share one map. A URL fragment preserves the view without storing private data. Blinking does not autoplay and falls back to a manual date toggle when reduced motion is requested.

The two native display exports are 3,540 by 2,880 pixels each, 12,124,225 bytes combined, about 77.8 MiB decoded RGBA. Their render pixel size is approximately 11.72 projected meters, distinct from the source's 10 m posting. Rendering or enlarging them does not improve accuracy. No public website deployment is claimed; this is a local viewer and a reproducible public repository artifact.

Direct `file:` opening was not runtime-verified: the current testing browser permits HTTP/HTTPS only. No file-protocol workaround was attempted. The bundled viewer needs no Internet connection when served locally.

## Design and evidence scope

The job is spatial and temporal visual comparison: inspect the two existing radar displays in one shared viewport, rather than shrinking them into side-by-side panels. This is a presentation tool for an unofficial GIS demonstration, not a change detector or hazard product.

One Leaflet instance owns pan/zoom; two static PNG overlays share a north-up EPSG:32645 display grid. A swipe boundary clips the before image over the after image. Date-only modes and optional slow blinking are alternatives. No difference image, registration correction, feature boundary or event attribution is computed.

| Layer | Date and source | Encoding | Evidence limit |
|---|---|---|---|
| Before | 16 August 2026, M1-SRC-002, Sentinel-1D ASF HyP3 RTC | VV gamma0 dB; shared -30 to 0 grayscale | Partial display; registration unverified |
| After | 28 August 2026, M1-SRC-005, Sentinel-1D ASF HyP3 RTC | Same | Same |
| Distance/coordinates | Native map-frame PNG world files, EPSG:32645 | Projected meters; grid north up | Not positional accuracy or independently validated control |
| Context | No external basemap or thematic layer | Existing imagery only | Blank areas are exclusions, not unchanged terrain |

The source-area and upper-corridor common-valid VV/VH coverage remain 54.6721% and 75.7928%. VV alone is displayed. Both full-area QA dispositions remain defer. Radar brightness differences can reflect moisture, geometry, scattering, speckle or misalignment. This viewer deliberately makes no disaster-impact, human-harm or validated-change claim.

## Implementation contract

- Export the existing accepted map frames with their unchanged colorizer, camera and source TIFF identities. Use native PNG world files for pixel-center-to-outer-edge placement, unchanged. Export resolution changes presentation sampling, not the source grid or scientific criteria.
- Use Leaflet's planar CRS machinery with coordinates explicitly supplied as northing/easting in meters. Do not put UTM values into Web Mercator or relabel them as latitude/longitude. There is no WGS84 reprojection, basemap request, geolocation, account or network data source.
- Vendor pinned Leaflet 1.9.4 JS/CSS and its BSD 2-Clause license. This is a static browser dependency, not a software installation, and does not relicense project code or imagery.
- Keep two raster overlays in map space; date labels, divider, warning, controls and source credits remain screen-stable. No WebGL, animation pipeline, particle effects or derived change marks.
- Keep the swipe value, mode and finite projected camera coordinates in the URL hash. No cookies, analytics, account state or persistent private data. Invalid hashes fall back to the overview.
- Desktop and mobile portrait share the same comparison. Provide keyboard slider/zoom/reset controls, touch drag/pan/pinch, visible dates and an always-present registration warning. Blink is opt-in and slow; reduced-motion mode uses a manual date toggle.
- Missing Leaflet or imagery must show an explicit failure plus the static qualified panel. The native ArcGIS package/PDF remain the export fallback.
- Cap the two PNG assets at 32 MiB combined; use one map and no remote tiles. Enlarging a render cannot add source detail or accuracy. The decoded image footprint is recorded in the local export receipt.

## QA plan

Pure tests cover world-file axis order, outer-edge half-pixel handling, invalid dimensions, rotation rejection and non-finite inputs. Local native evidence binds source identity, unchanged camera/colorizer, identical display grids and unchanged input tree. Browser checks cover actual rendering, clipping at multiple boundaries, date-only and blink controls, synchronized pan/zoom, reset, keyboard use, narrow layout and failure/reduced-motion paths. Static DOM checks alone do not establish browser correctness.

The static qualified layout is the fallback when JavaScript is unavailable. Credit remains visible in every interactive mode: ASF DAAC HyP3 2026. Contains modified Copernicus Sentinel data 2026, processed by ESA. Processing DOIs: 10.5281/zenodo.3962581 and 10.5281/zenodo.3962936.

The first export candidate stopped on a development assertion that native world-file outer edges would equal the map camera extent. The observed difference is about half a render pixel, with a smaller scale difference. That failed candidate is retained. The viewer does not alter either origin or fit a correction: placement follows each native world file as supplied, both renders must use exactly the same display grid, and the camera must remain unchanged. Native extent deltas are recorded separately. No independent positional-accuracy or registration claim follows from those metadata.

## Verified result

The portable and installed-runtime focused suites each pass 16 tests. Browser checks pass actual image loading, both date-only modes, keyboard swipe increment and 0/100% endpoints, divider dragging, opt-in blink/stop, zoom, pan, overview and closer-view controls, URL-state restoration, and a 390-by-844 responsive layout with no horizontal overflow. Both image elements keep identical positions and dimensions after panning.

A disposable missing-metadata fixture shows the explicit static fallback. A boundary-mocked reduced-motion fixture switches dates manually with the same renderer. These fixtures are local test inputs, not part of the shipped viewer. Actual phone touch/pinch hardware and an OS reduced-motion preference change were not exercised. The scientific limits and source credit remain visible in the main and fallback pages. See the [sanitized result](../records/readiness/gis-demonstration-001-swipe-viewer-result.json).

## Primary references

[Leaflet planar coordinates and image overlays](https://leafletjs.com/examples/crs-simple/crs-simple.html), [Leaflet 1.9.4 reference](https://leafletjs.com/reference.html), [Leaflet BSD 2-Clause license](https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE), [Esri MapFrame PNG/world-file export](https://doc.esri.com/en/arcgis-pro/latest/arcpy/mapping/mapframe-class.html). Imagery rights and the existing scientific limits are recorded in the [demonstration guide](GIS_DEMONSTRATION.md).
