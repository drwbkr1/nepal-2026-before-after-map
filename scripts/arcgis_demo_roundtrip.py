"""Local ArcGIS Pro staging-project round trip; no source saves or publication."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha256(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def reject_links(path):
    for part in (Path(path).absolute(), *Path(path).absolute().parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('Linked paths are outside this local pilot capability')


def inside(path, root):
    return Path(path).resolve().is_relative_to(Path(root).resolve())


def local_source(value, root):
    text = str(value)
    if '://' in text or text.startswith(('\\\\', '//')) or not Path(text).is_absolute():
        raise ValueError('Only absolute local data sources are supported')
    reject_links(Path(text))
    if not inside(text, root):
        raise ValueError('Data source is outside the staging root')
    if any(p.suffix.lower() in {'.sde', '.acs', '.ags', '.odc'} for p in (Path(text), *Path(text).parents)):
        raise ValueError('Service/database connections are outside this local pilot capability')
    return Path(text)


def inventory(root):
    reject_links(root)
    result = {}
    for path in sorted(Path(root).rglob('*')):
        reject_links(path)
        if path.is_file() and not path.name.lower().endswith('.lock'):
            result[path.relative_to(root).as_posix()] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
    return result


def reserve(project, source_root, output):
    for path in (project, source_root, output):
        reject_links(path)
    if not source_root.is_dir() or not project.is_file() or project.suffix.lower() != '.aprx':
        raise ValueError('Existing staging root and APRX required')
    if not inside(project, source_root):
        raise ValueError('Project must be inside staging root')
    if inside(output, source_root) or inside(source_root, output):
        raise ValueError('Input and output trees must be disjoint')
    output.mkdir(parents=True, exist_ok=False)


def write_new(path, data):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2)
        handle.write('\n')


def pixel_digest(path):
    from PIL import Image
    with Image.open(path) as image:
        rgb = image.convert('RGB')
        return {'size': list(rgb.size), 'sha256': hashlib.sha256(rgb.tobytes()).hexdigest()}


def has_data_source(item):
    # ArcPy Layer has supports(); standalone Table exposes dataSource directly.
    supports = getattr(item, 'supports', None)
    return bool(supports('DATASOURCE')) if supports else hasattr(item, 'dataSource')


def snapshot(project_path, root, exports):
    import arcpy
    arcpy.SetLogHistory(False)
    arcpy.SetLogMetadata(False)
    project = arcpy.mp.ArcGISProject(str(project_path))
    if project.listBrokenDataSources():
        raise ValueError('Project contains broken sources; repair a staging copy first')
    local_source(project.defaultGeodatabase, root)
    local_source(project.defaultToolbox, root)
    local_source(project.homeFolder, root)
    maps = []
    item_count = 0
    for map_obj in project.listMaps():
        if map_obj.mapType != 'MAP':
            raise ValueError('3D scenes are outside this pilot capability')
        items = []
        for item in [*map_obj.listLayers(), *map_obj.listTables()]:
            if getattr(item, 'isGroupLayer', False):
                continue
            if getattr(item, 'isWebLayer', False) or getattr(item, 'isBasemapLayer', False):
                raise ValueError('Web/basemap layers need separate handling')
            if not has_data_source(item):
                raise ValueError('An item has no inspectable data source')
            local_source(item.dataSource, root)
            if not arcpy.Exists(item.dataSource):
                raise ValueError('A local data source does not exist')
            desc = arcpy.Describe(item.dataSource)
            sr = getattr(desc, 'spatialReference', None)
            info = {'name': item.name, 'type': desc.dataType,
                    'wkid': sr.factoryCode if sr else None,
                    'crs': sr.name if sr else None}
            if hasattr(desc, 'shapeType'):
                info['geometry'] = desc.shapeType
            if getattr(item, 'isRasterLayer', False):
                raster = arcpy.Raster(item.dataSource)
                info.update(rows=raster.height, columns=raster.width, bands=raster.bandCount,
                            cell_width=raster.meanCellWidth, cell_height=raster.meanCellHeight,
                            extent=[raster.extent.XMin, raster.extent.YMin,
                                    raster.extent.XMax, raster.extent.YMax])
                # Full existing-display cell equality is packaging QA, not a
                # cross-date comparison or a new scientific analysis.
                values = arcpy.RasterToNumPyArray(raster, nodata_to_value=-999999)
                info['packaging_cell_digest'] = {'dtype': str(values.dtype),
                                                'shape': list(values.shape),
                                                'sha256': hashlib.sha256(values.tobytes()).hexdigest()}
                del values
                colorizer = item.getDefinition('V3').colorizer
                info['display_settings'] = {'stretch': colorizer.stretchType,
                    'custom_min': colorizer.customStretchMin, 'custom_max': colorizer.customStretchMax,
                    'custom_min_max': colorizer.useCustomStretchMinMax,
                    'gamma_stretch': colorizer.useGammaStretch}
                del raster
            else:
                info['rows'] = int(arcpy.management.GetCount(item.dataSource)[0])
                info['fields'] = [(f.name, f.type) for f in arcpy.ListFields(item.dataSource)]
                if item.name == 'SourceManifest':
                    fields = ['Source_ID', 'Acquired', 'Use_Status']
                    with arcpy.da.SearchCursor(item.dataSource, fields) as cursor:
                        info['source_manifest_values'] = sorted(tuple(row) for row in cursor)
            items.append(info)
            item_count += 1
        maps.append({'name': map_obj.name, 'wkid': map_obj.spatialReference.factoryCode, 'items': items})
    if not item_count:
        raise ValueError('No data items to test')
    layouts = project.listLayouts()
    if not layouts:
        raise ValueError('At least one layout is required for this delivery pilot')
    exports.mkdir(exist_ok=False)
    renders = []
    for index, layout in enumerate(layouts):
        png = exports / f'layout-{index + 1:02}.png'
        pdf = exports / f'layout-{index + 1:02}.pdf'
        layout.exportToPNG(str(png), resolution=120, color_mode='24-BIT_TRUE_COLOR')
        layout.exportToPDF(str(pdf), resolution=120)
        if not pdf.is_file() or pdf.stat().st_size == 0:
            raise ValueError('Missing PDF export')
        renders.append({'name': layout.name, 'png': png.name, 'pdf': pdf.name, 'pixels': pixel_digest(png)})
    result = {'maps': maps, 'layouts': renders, 'item_count': item_count}
    del project
    gc.collect()
    # Normalize tuples to the same JSON representation used by the child process.
    return json.loads(json.dumps(result))


def compare(before, after):
    return {'structure_equal': before['maps'] == after['maps'],
            'layout_pixels_equal': before['layouts'] == after['layouts']}


def run(project, root, output):
    reserve(project, root, output)
    original = inventory(root)
    write_new(output / 'initial-source-inventory.json', original)
    receipt = {'status': 'failed', 'scope': 'same-machine fresh-process local staging round trip',
               'project': str(project), 'source_root': str(root),
               'clean_machine_tested': False, 'scientific_validity_tested': False}
    try:
        os.environ.setdefault('GDAL_PAM_ENABLED', 'NO')
        import arcpy
        arcpy.SetLogHistory(False)
        arcpy.SetLogMetadata(False)
        receipt['arcgis_version'] = arcpy.GetInstallInfo()['Version']
        before = snapshot(project, root, output / 'before')
        write_new(output / 'before.json', before)
        warmed = inventory(root)
        warmup_changes = [name for name in sorted(set(original) | set(warmed))
                          if original.get(name) != warmed.get(name)]
        receipt['render_warmup_changed_files'] = warmup_changes
        write_new(output / 'prepackage-source-inventory.json', warmed)
        # ArcGIS creates toolbox metadata and opens writable default-GDB
        # housekeeping files during the first render. Preserve that observation
        # separately; never allow an APRX or TIFF change to be hidden by warmup.
        if any(not (name.endswith('.pyt.xml') or name.endswith('.gdb/timestamps'))
               for name in warmup_changes):
            raise ValueError('Unexpected source mutation during render warmup')
        original = warmed
        package = output / 'delivery.ppkx'
        with arcpy.EnvManager(overwriteOutput=False, workspace=str(output), scratchWorkspace=str(output)):
            arcpy.management.PackageProject(
                in_project=str(project), output_file=str(package), sharing_internal='EXTERNAL',
                package_as_template='PROJECT_PACKAGE', summary='Local delivery verification',
                tags='delivery verification', version='CURRENT', include_toolboxes='NO_TOOLBOXES',
                include_history_items='NO_HISTORY_ITEMS', read_only='READ_WRITE')
            extracted = output / 'extracted'
            arcpy.management.ExtractPackage(str(package), str(extracted), 'NO_CACHE')
        projects = list(extracted.rglob('*.aprx'))
        if len(projects) != 1:
            raise ValueError('Expected exactly one extracted APRX')
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'inspect',
                                '--project', str(projects[0]), '--source-root', str(extracted),
                                '--output', str(output / 'after')], capture_output=True, text=True, timeout=240)
        if child.returncode:
            raise RuntimeError('Fresh-process inspect failed: ' + child.stderr[-1000:])
        after = json.loads((output / 'after' / 'snapshot.json').read_text(encoding='utf-8'))
        checks = compare(before, after)
        checks['source_stable_files_unchanged'] = original == inventory(root)
        checks['extracted_sources_local'] = True  # snapshot rejects anything outside extraction.
        receipt.update(checks=checks, package_sha256=sha256(package), extracted_project=str(projects[0]),
                       item_count=after['item_count'], status='passed' if all(checks.values()) else 'failed')
        if not all(checks.values()):
            receipt['error'] = 'A round-trip comparison failed; see snapshots and rendered outputs'
    except Exception as exc:
        receipt['error'] = str(exc)
    finally:
        final_inventory = inventory(root)
        write_new(output / 'final-source-inventory.json', final_inventory)
        receipt['changed_after_baseline'] = [name for name in sorted(set(original) | set(final_inventory))
                                             if original.get(name) != final_inventory.get(name)]
        receipt['source_stable_files_unchanged'] = original == final_inventory
        if not receipt['source_stable_files_unchanged']:
            receipt['status'] = 'failed'
        write_new(output / 'receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['status'] == 'passed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['run', 'inspect'])
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Check raw paths before resolve so linked ancestors cannot disappear.
    for value in (args.project, args.source_root, args.output):
        reject_links(value)
    project, root, output = (p.resolve() for p in (args.project, args.source_root, args.output))
    if args.mode == 'run':
        return run(project, root, output)
    reserve(project, root, output)
    report = snapshot(project, root, output / 'exports')
    write_new(output / 'snapshot.json', report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
