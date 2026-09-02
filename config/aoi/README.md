# Draft study areas

`draft-study-areas.geojson` contains the three rectangular planning bounds from the data and methods plan.

GeoJSON stores coordinates as RFC 7946 longitude/latitude in EPSG:4326. This is the interchange form for review. ArcGIS analysis must project the approved geometry to **WGS 1984 UTM Zone 45N (EPSG:32645)**.

After owner approval, `approved-study-areas.geojson` is the promoted EPSG:4326 interchange artifact and `approved-study-areas-epsg32645.json` is an ArcGIS FeatureSet JSON projected with ArcGIS Pro. In ArcGIS Pro, use **JSON To Features** to import the projected JSON into a geodatabase feature class without another reprojection.

These are search and review extents. They are not mapped change polygons or evidence of event attribution.

These features are drafts. They do not establish the event source, analysis extent, source acceptance, or acquisition authority.
