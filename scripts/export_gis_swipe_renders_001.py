"""Export existing accepted map frames for a projected, display-only swipe viewer."""
from __future__ import annotations

import argparse
import gc
import json
import math
from pathlib import Path

from arcgis_demo_roundtrip import inventory, local_source, reject_links, sha256, write_new
from stage_gis_demonstration_001 import EXPECTED_RASTERS
from refine_gis_demonstration_layout_001 import camera_signature, require_same_view


def world_bounds(values, width, height):
    """Use pixel-center world-file coefficients to return outer-edge E/N bounds."""
    if len(values) != 6 or width <= 0 or height <= 0 or not all(math.isfinite(v) for v in values):
        raise ValueError('Invalid world file or image dimensions')
    a, d, b, e, c, f = values
    if a <= 0 or e >= 0 or b != 0 or d != 0:
        raise ValueError('Only the existing north-up projected frames are supported')
    west, north = c - a / 2, f - e / 2
    return [west, north + height * e, west + width * a, north]


def utc_now():
    # ArcGIS initialization can change names in a top-level script namespace.
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def export(project_path, source_root, output, expected_project_hash):
    for value in (project_path, source_root, output):
        reject_links(value)
    project_path, source_root, output = (p.resolve() for p in (project_path, source_root, output))
    local_source(project_path, source_root)
    if output.exists() or output.is_relative_to(source_root) or source_root.is_relative_to(output):
        raise ValueError('Output collision or overlapping trees')
    if sha256(project_path) != expected_project_hash:
        raise ValueError('Project identity drift')
    for name, expected in EXPECTED_RASTERS.items():
        if sha256(source_root / 'imagery' / name) != expected:
            raise ValueError('Existing display TIFF identity drift')
    before = inventory(source_root)
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'status': 'failed', 'at_utc': utc_now(), 'source_project_sha256': expected_project_hash,
               'scope': 'render existing accepted imagery; no new source processing or scientific comparison',
               'scientific_admission': False, 'registration_verified': False, 'project_saved': False}
    try:
        import arcpy
        from PIL import Image
        arcpy.SetLogHistory(False)
        arcpy.SetLogMetadata(False)
        project = arcpy.mp.ArcGISProject(str(project_path))
        if project.listBrokenDataSources():
            raise ValueError('Broken project sources')
        layouts = project.listLayouts()
        if len(layouts) != 1:
            raise ValueError('Unexpected layout count')
        frames = sorted(layouts[0].listElements('MAPFRAME_ELEMENT'), key=lambda f: f.elementPositionX)
        if len(frames) != 2:
            raise ValueError('Unexpected frame count')
        initial_camera = camera_signature(frames)
        renders = []
        for frame, key, source_id, date in zip(frames, ['before', 'after'],
                ['M1-SRC-002', 'M1-SRC-005'], ['2026-08-16', '2026-08-28']):
            if frame.map.spatialReference.factoryCode != 32645 or frame.camera.heading != 0:
                raise ValueError('Unexpected projection or rotation')
            if not frame.map.name.startswith('16 Aug 2026' if key == 'before' else '28 Aug 2026'):
                raise ValueError('Unexpected date association')
            rasters = [layer for layer in frame.map.listLayers() if layer.isRasterLayer]
            if len(rasters) != 1:
                raise ValueError('Unexpected imagery layer count')
            raster = rasters[0]
            local_source(raster.dataSource, source_root)
            expected_name = key + '_common_valid_vv_db.tif'
            if Path(raster.dataSource).name != expected_name or sha256(raster.dataSource) != EXPECTED_RASTERS[expected_name]:
                raise ValueError('Unexpected display raster')
            colorizer = raster.getDefinition('V3').colorizer
            if not colorizer.useCustomStretchMinMax or (colorizer.customStretchMin, colorizer.customStretchMax) != (-30, 0) or colorizer.useGammaStretch:
                raise ValueError('Shared display contract changed')
            png = output / (key + '.png')
            frame.exportToPNG(str(png), resolution=600, world_file=True, color_mode='24-BIT_TRUE_COLOR')
            worlds = [p for p in output.iterdir() if p.stem == key and p.suffix.lower() in {'.pgw', '.pgwx', '.pngw', '.wld'}]
            if len(worlds) != 1:
                raise ValueError('Expected one PNG world file')
            values = [float(line) for line in worlds[0].read_text(encoding='utf-8').splitlines()]
            with Image.open(png) as image:
                width, height = image.size
            bounds = world_bounds(values, width, height)
            extent = frame.camera.getExtent()
            expected_bounds = [extent.XMin, extent.YMin, extent.XMax, extent.YMax]
            renders.append({'key': key, 'source_id': source_id, 'date': date, 'file': png.name,
                'bytes': png.stat().st_size, 'sha256': sha256(png), 'size': [width, height],
                'world_file': worlds[0].name, 'world_file_sha256': sha256(worlds[0]),
                'world_coefficients': values, 'bounds_easting_northing': bounds,
                'frame_camera_extent': expected_bounds,
                'native_world_extent_minus_camera_extent_m': [a - b for a, b in zip(bounds, expected_bounds)],
                'placement': 'Native PNG world-file outer edges, unchanged; not a registration correction'})
        if renders[0]['size'] != renders[1]['size'] or renders[0]['world_coefficients'] != renders[1]['world_coefficients']:
            raise ValueError('Viewer renders do not use exactly the same display grid')
        if sum(r['bytes'] for r in renders) > 32 * 1024 * 1024:
            raise ValueError('Browser asset byte cap exceeded')
        require_same_view(initial_camera, camera_signature(frames))
        receipt.update(status='passed_projected_display_export', renders=renders,
            wkid=32645, range_db=[-30, 0], gamma_stretch=False,
            decoded_RGBA_bytes=sum(r['size'][0] * r['size'][1] * 4 for r in renders),
            source_posting_m=10, render_pixel_size_m=renders[0]['world_coefficients'][0],
            map_viewport_unchanged=True, source_raster_values_unchanged=True,
            arcgis_version=arcpy.GetInstallInfo()['Version'])
        del project
        gc.collect()
    except Exception as exc:
        receipt['error'] = str(exc)
    finally:
        receipt['source_tree_unchanged'] = before == inventory(source_root)
        if not receipt['source_tree_unchanged']:
            receipt['status'] = 'failed'
        write_new(output / 'export-receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['status'] == 'passed_projected_display_export' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--project-sha256', required=True)
    args = parser.parse_args()
    raise SystemExit(export(args.project, args.source_root, args.output, args.project_sha256))
