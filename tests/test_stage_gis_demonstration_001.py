"""Staging and public display-bundle integrity; no ArcPy or raw imagery access."""
import base64
import io
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage_gis_demonstration_001 import digest, preflight
from arcgis_demo_roundtrip import compare, has_data_source, run
from refine_gis_demonstration_layout_001 import camera_signature, require_same_view
from export_gis_swipe_renders_001 import world_bounds


class StagePreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "input"
        self.source.mkdir()
        self.project = self.source / "fixture.aprx"
        self.project.write_bytes(b"disposable project placeholder")
        self.rasters = self.source / "images"
        self.rasters.mkdir()
        self.raster = self.rasters / "fixture.tif"
        self.raster.write_bytes(b"disposable non-raster placeholder")
        self.output = self.root / "new"

    def check(self):
        return preflight(self.project, self.rasters, self.output, digest(self.project),
                         {"fixture.tif": digest(self.raster)})

    def test_exact_disjoint_inputs_leave_files_untouched(self):
        before = self.raster.read_bytes()
        self.assertEqual(len(self.check()), 2)
        self.assertEqual(self.raster.read_bytes(), before)
        self.assertFalse(self.output.exists())

    def test_collision_is_rejected(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "collision"):
            self.check()

    def test_nested_output_is_rejected(self):
        self.output = self.source / "new"
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.check()

    def test_hash_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "hash drift"):
            preflight(self.project, self.rasters, self.output, "0" * 64,
                      {"fixture.tif": digest(self.raster)})


class RoundTripComparison(unittest.TestCase):
    def test_invalid_sharing_mode_stops_before_output_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'output'
            with self.assertRaisesRegex(ValueError, 'sharing mode'):
                run(root / 'fixture.aprx', root / 'input', output, 'UNSUPPORTED')
            self.assertFalse(output.exists())

    def test_standalone_table_without_layer_supports_is_accepted(self):
        self.assertTrue(has_data_source(SimpleNamespace(dataSource="local-table")))

    def test_object_without_data_source_is_rejected(self):
        self.assertFalse(has_data_source(SimpleNamespace(name="no data")))

    def test_changed_map_structure_is_detected(self):
        before = {"maps": [{"wkid": 32645}], "layouts": []}
        after = {"maps": [{"wkid": 4326}], "layouts": []}
        result = compare(before, after)
        self.assertFalse(result["structure_equal"])
        self.assertTrue(result["layout_pixels_equal"])

    def test_changed_render_is_detected(self):
        before = {"maps": [], "layouts": [{"pixels": "before"}]}
        after = {"maps": [], "layouts": [{"pixels": "after"}]}
        self.assertFalse(compare(before, after)["layout_pixels_equal"])

    def test_changed_layout_metadata_is_distinct_from_pixel_change(self):
        before = {'maps': [], 'layouts': [{'pixels': 'same', 'frame': 'before'}]}
        after = {'maps': [], 'layouts': [{'pixels': 'same', 'frame': 'wrong frame'}]}
        result = compare(before, after)
        self.assertTrue(result['layout_pixels_equal'])
        self.assertFalse(result['layout_metadata_equal'])


class CartographicValidation(unittest.TestCase):
    def test_world_file_centers_become_projected_outer_edges(self):
        self.assertEqual(world_bounds([10, 0, 0, -10, 105, 195], 3, 2), [100, 180, 130, 200])

    def test_rotated_world_file_is_not_silently_relocated(self):
        with self.assertRaisesRegex(ValueError, 'north-up'):
            world_bounds([10, 1, 0, -10, 105, 195], 3, 2)

    def test_nonfinite_world_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            world_bounds([10, 0, 0, -10, float('nan'), 195], 3, 2)

    def test_empty_render_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            world_bounds([10, 0, 0, -10, 105, 195], 0, 2)

    def test_scale_change_is_not_hidden_as_presentation_only(self):
        with self.assertRaisesRegex(ValueError, 'viewport'):
            require_same_view({'before': {'scale': 1000}}, {'before': {'scale': 2000}})

    def test_duplicate_frame_maps_are_rejected(self):
        extent = SimpleNamespace(XMin=1, YMin=2, XMax=3, YMax=4)
        camera = SimpleNamespace(scale=1000, heading=0, X=2, Y=3, getExtent=lambda: extent)
        frame = SimpleNamespace(map=SimpleNamespace(name='same map'), camera=camera,
                                elementWidth=2, elementHeight=3)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            camera_signature([frame, frame])


class PublishedViewerIntegrity(unittest.TestCase):
    root = Path(__file__).resolve().parents[1] / 'docs' / 'viewer'

    def test_display_files_and_native_world_grid_match_viewer_metadata(self):
        source = json.loads((self.root / 'renders' / 'SOURCE.json').read_text(encoding='utf-8'))
        script = (self.root / 'data.js').read_text(encoding='utf-8').strip()
        data = json.loads(script.removeprefix('window.NEPAL_VIEWER = Object.freeze(').removesuffix(');'))
        for render in source['renders']:
            with self.subTest(date=render['date']):
                png = self.root / 'renders' / render['file']
                world = self.root / 'renders' / render['world_file']
                self.assertEqual(digest(png), render['sha256'])
                self.assertEqual(digest(world), render['world_file_sha256'])
                self.assertEqual(png.stat().st_size, render['bytes'])
                with png.open('rb') as stream:
                    header = stream.read(24)
                self.assertEqual(header[:8], b'\x89PNG\r\n\x1a\n')
                dimensions = list(struct.unpack('>II', header[16:24]))
                self.assertEqual(dimensions, render['size'])
                values = [float(v) for v in world.read_text(encoding='utf-8').splitlines()]
                self.assertEqual(world_bounds(values, *dimensions), data['bounds'])
                scene = data[render['key']]
                self.assertEqual(scene['source_id'], render['source_id'])
                self.assertEqual(scene['date'], render['date'])
                self.assertEqual(scene['sha256'], render['sha256'])
                self.assertEqual(scene['size'], dimensions)
                self.assertEqual(self.root / scene['file'], png)

    def test_vendored_distribution_preserves_pinned_download_bytes(self):
        vendor = self.root / 'vendor' / 'leaflet'
        source = json.loads((vendor / 'SOURCE.json').read_text(encoding='utf-8'))
        for asset in source['assets']:
            with self.subTest(file=asset['file']):
                path = vendor / asset['file']
                self.assertEqual(digest(path), asset['sha256'])
                self.assertEqual(path.stat().st_size, asset['bytes'])

    def test_fallback_is_the_published_qualified_cartographic_preview(self):
        repo = self.root.parents[1]
        record = json.loads((repo / 'records' / 'readiness' /
                             'gis-demonstration-001-cartography-result.json').read_text(encoding='utf-8'))
        expected = record['public_preview']['sha256']
        self.assertEqual(digest(self.root / 'fallback-panel.png'), expected)
        self.assertEqual(digest(repo / record['public_preview']['ref']), expected)


class BrowserExportPackaging(unittest.TestCase):
    """Exercise the real ZIP writer with disposable bytes, using an existing Node."""
    @classmethod
    def setUpClass(cls):
        bundled = (Path.home() / '.cache' / 'codex-runtimes' / 'codex-primary-runtime' /
                   'dependencies' / 'node' / 'bin' / 'node.exe')
        cls.node = shutil.which('node') or (str(bundled) if bundled.is_file() else None)
        if cls.node is None:
            raise unittest.SkipTest('Node is not available; no installation requested')
        cls.module = Path(__file__).resolve().parents[1] / 'docs' / 'viewer' / 'export-bundle.js'

    def execute(self, code):
        return subprocess.run([self.node, '-e', code, str(self.module)], check=True,
                              capture_output=True, text=True).stdout

    def test_zip_roundtrip_and_crc_preserve_member_bytes(self):
        encoded = self.execute("""
            const {zip} = require(process.argv[1]);
            const entries = [
              {name:'before.png', bytes:Uint8Array.from([0, 255, 128, 10])},
              {name:'before.pgw', bytes:new TextEncoder().encode('10\\r\\n0\\r\\n0\\r\\n-10\\r\\n105\\r\\n195\\r\\n')}
            ];
            process.stdout.write(Buffer.from(zip(entries)).toString('base64'));
        """)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), ['before.png', 'before.pgw'])
            self.assertEqual(archive.read('before.png'), bytes([0, 255, 128, 10]))
            self.assertEqual(archive.read('before.pgw'), b'10\r\n0\r\n0\r\n-10\r\n105\r\n195\r\n')

    def test_invalid_members_and_oversize_are_rejected(self):
        rejected = json.loads(self.execute("""
            const {zip} = require(process.argv[1]), bytes = new Uint8Array([1]);
            const cases = [[], [{name:'../escape', bytes}], [{name:'same', bytes}, {name:'same', bytes}],
              [{bytes}], [null], [{name:'invalid', bytes:'not bytes'}],
              [{name:'large', bytes:new Uint8Array(32 * 1024 * 1024 + 1)}]];
            process.stdout.write(JSON.stringify(cases.map(entries => {
              try {zip(entries); return false;} catch {return true;}
            })));
        """))
        self.assertEqual(rejected, [True] * 7)

    def test_display_packaging_keeps_files_and_rejects_identity_drift(self):
        result = json.loads(self.execute("""
            const {displayBundle} = require(process.argv[1]);
            const {createHash, webcrypto} = require('node:crypto');
            global.crypto = webcrypto;
            const enc = new TextEncoder(), files = new Map(), bounds = [100,180,130,200];
            const sha = bytes => createHash('sha256').update(bytes).digest('hex');
            const source = {wkid:32645, renders:[]}, data = {bounds};
            for (const key of ['before','after']) {
              const png = enc.encode('disposable ' + key), pgw = enc.encode('10\\n0\\n0\\n-10\\n105\\n195\\n');
              const row = {key, file:key+'.png', world_file:key+'.pgw', source_id:key, date:'fixture',
                sha256:sha(png), bytes:png.length, world_file_sha256:sha(pgw), bounds_easting_northing:bounds};
              source.renders.push(row); data[key] = row;
              files.set('renders/'+row.file,png); files.set('renders/'+row.world_file,pgw);
              files.set('renders/'+row.file+'.aux.xml',enc.encode('<fixture/>'));
            }
            files.set('ARCGIS_DISPLAY_README.txt',enc.encode('Unverified fixture'));
            const setSource = () => files.set('renders/SOURCE.json',enc.encode(JSON.stringify(source)));
            setSource();
            global.fetch = async path => {
              const bytes = files.get(path);
              return {ok:!!bytes, headers:{get:() => bytes?.length ?? 0}, arrayBuffer:async () => bytes.buffer};
            };
            (async () => {
              const original = Buffer.from(await displayBundle(data)).toString('base64');
              source.renders[0] = {...source.renders[0],source_id:'wrong'}; setSource();
              let identityRejected = false, bytesRejected = false;
              try {await displayBundle(data);} catch {identityRejected = true;}
              source.renders[0] = data.before; setSource();
              files.set('renders/before.png',enc.encode('wrong-byte-content'));
              try {await displayBundle(data);} catch {bytesRejected = true;}
              process.stdout.write(JSON.stringify({original,identityRejected,bytesRejected}));
            })().catch(error => {console.error(error); process.exitCode = 1;});
        """))
        self.assertTrue(result['identityRejected'])
        self.assertTrue(result['bytesRejected'])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(result['original']))) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.namelist()), 8)
            self.assertEqual(archive.read('before.png'), b'disposable before')
            self.assertEqual(archive.read('after.png'), b'disposable after')


if __name__ == "__main__":
    unittest.main()
