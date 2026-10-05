"""Add native map cues to a fresh local copy; never alter source raster values."""
from __future__ import annotations

import argparse
import gc
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil

from arcgis_demo_roundtrip import inventory, local_source, reject_links, sha256, write_new
from stage_gis_demonstration_001 import EXPECTED_RASTERS, WARNING


def camera_signature(frames):
    result = {}
    for frame in frames:
        if frame.map.name in result:
            raise ValueError('Duplicate frame map')
        camera = frame.camera
        extent = camera.getExtent()
        result[frame.map.name] = {
            'scale': camera.scale, 'heading': camera.heading,
            'x': camera.X, 'y': camera.Y,
            'extent': [extent.XMin, extent.YMin, extent.XMax, extent.YMax],
            'frame_width': frame.elementWidth, 'frame_height': frame.elementHeight,
        }
    return result


def require_same_view(before, after):
    if before != after:
        raise ValueError('Cartography changed the existing map viewport')


def rectangle(arcpy, x, y, width, height):
    return arcpy.Polygon(arcpy.Array([arcpy.Point(x, y), arcpy.Point(x, y + height),
        arcpy.Point(x + width, y + height), arcpy.Point(x + width, y), arcpy.Point(x, y)]))


def style(project, style_class, name):
    matches = [s for s in project.listStyleItems('ArcGIS 2D', style_class, name) if s.name == name]
    if len(matches) != 1:
        raise ValueError('Expected exact installed style: ' + name)
    return matches[0]


def refine(project_path, source_root, output, project_hash):
    for path in (project_path, source_root, output):
        reject_links(path)
    project_path, source_root, output = (p.resolve() for p in (project_path, source_root, output))
    local_source(project_path, source_root)
    if output.exists() or output.is_relative_to(source_root) or source_root.is_relative_to(output):
        raise ValueError('Output collision or overlapping trees')
    if sha256(project_path) != project_hash:
        raise ValueError('Project identity drift')
    for name, expected in EXPECTED_RASTERS.items():
        if sha256(source_root / 'imagery' / name) != expected:
            raise ValueError('Display raster identity drift')
    initial = inventory(source_root)
    shutil.copytree(source_root, output,
        ignore=shutil.ignore_patterns('*.lock', 'Index', 'stage-receipt.json'))
    receipt = {'status': 'failed', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'fresh-copy cartographic presentation only', 'source_project_sha256': project_hash,
        'raster_values_changed': False, 'scientific_admission': False, 'clean_machine_tested': False}
    try:
        import arcpy
        arcpy.SetLogHistory(False)
        arcpy.SetLogMetadata(False)
        copied_project = output / project_path.relative_to(source_root)
        project = arcpy.mp.ArcGISProject(str(copied_project))
        project.updateConnectionProperties(str(source_root), str(output), validate=True)
        project.homeFolder = str(output)
        project.defaultGeodatabase = str(output / 'Demonstration.gdb')
        project.defaultToolbox = str(output / 'Demonstration.pyt')
        project.updateFolderConnections([{'connectionString': str(output), 'isHomeFolder': True}])
        project.updateDatabases([{'databasePath': str(output / 'Demonstration.gdb'),
                                  'isDefaultDatabase': True}])
        if project.listBrokenDataSources():
            raise ValueError('Broken sources in the copy')
        maps, layouts = project.listMaps(), project.listLayouts()
        if len(maps) != 2 or len(layouts) != 1:
            raise ValueError('Unexpected map/layout structure')
        for map_obj in maps:
            if map_obj.spatialReference.factoryCode != 32645:
                raise ValueError('Unexpected CRS')
            for item in [*map_obj.listLayers(), *map_obj.listTables()]:
                local_source(item.dataSource, output)
                if getattr(item, 'isRasterLayer', False):
                    definition = item.getDefinition('V3')
                    colorizer = definition.colorizer
                    if not colorizer.useCustomStretchMinMax or (colorizer.customStretchMin, colorizer.customStretchMax) != (-30, 0):
                        raise ValueError('Unexpected display range')
                    classes = colorizer.stretchClasses
                    if len(classes) < 2:
                        raise ValueError('Missing native stretch legend classes')
                    for index, entry in enumerate(classes):
                        entry.value = -30 + 30 * index / (len(classes) - 1)
                        entry.label = '-30' if index == 0 else '0' if index == len(classes) - 1 else ''
                    colorizer.useAdvancedLabeling = True
                    item.setDefinition(definition)
        layout = layouts[0]
        if (layout.pageWidth, layout.pageHeight, layout.pageUnits) != (13.0, 7.5, 'INCH'):
            raise ValueError('Unexpected input page')
        frames = sorted(layout.listElements('MAPFRAME_ELEMENT'), key=lambda f: f.elementPositionX)
        if len(frames) != 2 or not frames[0].map.name.startswith('16 Aug 2026') or not frames[1].map.name.startswith('28 Aug 2026'):
            raise ValueError('Unexpected frame/date association')
        before = camera_signature(frames)
        elements = layout.listElements()
        layout.changePageSize(13.0, 8.5, False)
        for element in elements:
            if element.name != 'Credits and DOIs':
                element.elementPositionY += 1.0
        warnings = layout.listElements('TEXT_ELEMENT', 'Partial-data warning')
        if len(warnings) != 1 or warnings[0].text != WARNING:
            raise ValueError('Scientific limitations changed')
        warnings[0].elementHeight = 0.4
        arrow_style = style(project, 'NORTH_ARROW', 'ArcGIS North 1')
        bar_style = style(project, 'SCALE_BAR', 'Alternating Scale Bar 1 Metric')
        for index, frame in enumerate(frames, 1):
            x = frame.elementPositionX
            arrow = layout.createMapSurroundElement(arcpy.Point(x + 0.28, 1.35),
                'NORTH_ARROW', frame, arrow_style, f'True north {index}')
            arrow.elementWidth = 0.23
            arrow.elementHeight = 0.46
            definition = arrow.getDefinition('V3')
            definition.northType = 'TrueNorth'
            definition.calibrationAngle = 0.0
            arrow.setDefinition(definition)
            bar = layout.createMapSurroundElement(rectangle(arcpy, x + 0.8, 1.25, 1.8, 0.3),
                'SCALE_BAR', frame, bar_style, f'Projected distance {index}')
            definition = bar.getDefinition('V3')
            # ArcGIS Pro stores linear units as a structured WKID object.
            # Preserve the validated metric style instead of assigning a string.
            if definition.units != {'uwkid': 9036}:
                raise ValueError('Native scale style is not kilometers')
            definition.unitLabel = 'km'
            definition.division = 5.0
            definition.divisions = 2
            definition.divisionsBeforeZero = 0
            definition.subdivisions = 1
            definition.fittingStrategy = 'AdjustFrame'
            definition.labelSymbol.symbol.height = 9.0
            definition.unitLabelSymbol.symbol.height = 9.0
            bar.setDefinition(definition)
            project.createTextElement(layout, rectangle(arcpy, x + 0.8, 0.92, 2.2, 0.25),
                'POLYGON', 'Projected distance; not positional accuracy.',
                text_size=8, font_family_name='Arial', name=f'Scale qualification {index}')
        legend = layout.createMapSurroundElement(rectangle(arcpy, 3.65, 0.98, 2.4, 0.8),
            'LEGEND', frames[0], style(project, 'LEGEND', 'Transparent Background Legend'),
            'Shared VV display legend')
        definition = legend.getDefinition('V3')
        definition.title = 'VV gamma0 (dB) - both dates'
        definition.showTitle = True
        definition.titleSymbol.symbol.height = 9.0
        definition.fittingStrategy = 'AdjustSize'
        definition.minFontSize = 8.0
        for item in definition.items:
            item.showLayerName = False
            item.showHeading = False
            item.showDescription = False
            item.patchHeight = 8.0
            item.patchWidth = 70.0
            item.labelSymbol.symbol.height = 9.0
        legend.setDefinition(definition)
        project.createTextElement(layout, rectangle(arcpy, 3.65, 0.69, 3.0, 0.25),
            'POLYGON', 'Legend applies to displayed pixels; blank areas are exclusions.',
            text_size=8, font_family_name='Arial', name='Legend qualification')
        require_same_view(before, camera_signature(frames))
        for element in layout.listElements('TEXT_ELEMENT'):
            if element.isOverflowing:
                raise ValueError('Text overflow: ' + element.name)
        if legend.isOverflowing:
            raise ValueError('Shared display legend overflows')
        project.save()
        receipt.update(status='passed_cartographic_copy', page_inches=[13.0, 8.5],
            source_camera_signature=before, map_viewport_unchanged=True,
            native_north_arrows=2, native_scale_bars=2, native_shared_legends=1,
            scientific_limitations_unchanged=True, project_sha256=sha256(copied_project),
            arcgis_version=arcpy.GetInstallInfo()['Version'])
        del project
        gc.collect()
    except Exception as exc:
        receipt['error'] = str(exc)
    finally:
        receipt['source_tree_unchanged'] = initial == inventory(source_root)
        receipt['copied_raster_bytes_unchanged'] = all(
            sha256(output / 'imagery' / name) == h for name, h in EXPECTED_RASTERS.items())
        if not receipt['source_tree_unchanged'] or not receipt['copied_raster_bytes_unchanged']:
            receipt['status'] = 'failed'
        write_new(output / 'cartography-receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['status'] == 'passed_cartographic_copy' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--project-sha256', required=True)
    args = parser.parse_args()
    raise SystemExit(refine(args.project, args.source_root, args.output, args.project_sha256))
