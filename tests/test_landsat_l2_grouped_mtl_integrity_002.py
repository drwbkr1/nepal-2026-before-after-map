from __future__ import annotations

import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("landsat_l2_grouped_mtl_integrity_002", ROOT / "scripts/landsat_l2_grouped_mtl_integrity_002.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PRODUCT = "LC09_L2SP_141040_20260810_20260811_02_T1"
SCENE = "LC91410402026222LGN00"
L1 = "LC09_L1TP_141040_20260810_20260811_02_T1"


def metadata(product=PRODUCT, scene=SCENE, l1=L1):
    text = f'''GROUP = LANDSAT_METADATA_FILE
  GROUP = PRODUCT_CONTENTS
    LANDSAT_PRODUCT_ID = "{product}"
    PROCESSING_LEVEL = "L2SP"
  END_GROUP = PRODUCT_CONTENTS
  GROUP = LEVEL2_PROCESSING_RECORD
    LANDSAT_PRODUCT_ID = "{product}"
    PROCESSING_LEVEL = "L2SP"
  END_GROUP = LEVEL2_PROCESSING_RECORD
  GROUP = LEVEL1_PROCESSING_RECORD
    LANDSAT_SCENE_ID = "{scene}"
    LANDSAT_PRODUCT_ID = "{l1}"
    PROCESSING_LEVEL = "L1TP"
  END_GROUP = LEVEL1_PROCESSING_RECORD
END_GROUP = LANDSAT_METADATA_FILE
END
'''.encode()
    xml = f'''<LANDSAT_METADATA_FILE><PRODUCT_CONTENTS>
<LANDSAT_PRODUCT_ID>{product}</LANDSAT_PRODUCT_ID><PROCESSING_LEVEL>L2SP</PROCESSING_LEVEL>
</PRODUCT_CONTENTS><LEVEL2_PROCESSING_RECORD>
<LANDSAT_PRODUCT_ID>{product}</LANDSAT_PRODUCT_ID><PROCESSING_LEVEL>L2SP</PROCESSING_LEVEL>
</LEVEL2_PROCESSING_RECORD><LEVEL1_PROCESSING_RECORD>
<LANDSAT_SCENE_ID>{scene}</LANDSAT_SCENE_ID><LANDSAT_PRODUCT_ID>{l1}</LANDSAT_PRODUCT_ID>
<PROCESSING_LEVEL>L1TP</PROCESSING_LEVEL></LEVEL1_PROCESSING_RECORD></LANDSAT_METADATA_FILE>'''.encode()
    return text, xml


def entries(text=None, xml=None):
    original_text, original_xml = metadata()
    return [(PRODUCT + suffix,
             (text if text is not None else original_text) if suffix == "_MTL.txt" else
             (xml if xml is not None else original_xml) if suffix == "_MTL.xml" else
             b"synthetic-not-a-tiff") for suffix in MODULE.REQUIRED_SUFFIXES]


def write_tar(path: Path, items):
    with tarfile.open(path, "w") as archive:
        for name, content in items:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


class GroupedMTLIntegrityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "synthetic.tar"

    def inspect(self, items=None):
        write_tar(self.path, entries() if items is None else items)
        return MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_exact_three_group_form_passes_without_pixel_claim(self):
        result = self.inspect()
        self.assertEqual(result["status"], "pass_container_and_grouped_mtl_identity_only")
        self.assertEqual(result["member_count"], len(MODULE.REQUIRED_SUFFIXES))
        self.assertIn("No TIFF header, CRS, pixel, AOI, registration, or change check was performed.", result["limitations"])

    def test_old_global_verifier_rejects_documented_level1_id(self):
        from landsat_l2_bundle_integrity import BundleIntegrityError, inspect_bundle
        write_tar(self.path, entries())
        with self.assertRaisesRegex(BundleIntegrityError, "mtl_text_identity_mismatch"):
            inspect_bundle(self.path, PRODUCT, SCENE)

    def test_wrong_group_or_duplicate_identity_stops(self):
        text, xml = metadata()
        for modified, code in (
            (text.replace(b"GROUP = LEVEL2_PROCESSING_RECORD", b"GROUP = OTHER_PROCESSING_RECORD"), "mtl_required_group_missing_or_duplicate"),
            (text.replace(b'LANDSAT_PRODUCT_ID = "' + PRODUCT.encode() + b'"', b'LANDSAT_PRODUCT_ID = "' + PRODUCT.encode() + b'"\n    LANDSAT_PRODUCT_ID = "' + PRODUCT.encode() + b'"', 1), "mtl_level2_or_scene_identity_mismatch"),
        ):
            with self.subTest(code=code):
                with self.assertRaisesRegex(MODULE.BundleIntegrityError, code):
                    self.inspect(entries(text=modified, xml=xml))

    def test_wrong_level1_lineage_or_scene_stops(self):
        for bad_l1, bad_scene, code in (
            ("LC09_L1TP_142040_20260810_20260811_02_T1", SCENE, "mtl_level1_provenance_invalid"),
            (L1, "LC91410402026223LGN00", "mtl_level2_or_scene_identity_mismatch"),
        ):
            with self.subTest(code=code):
                text, xml = metadata(l1=bad_l1, scene=bad_scene)
                with self.assertRaisesRegex(MODULE.BundleIntegrityError, code):
                    self.inspect(entries(text=text, xml=xml))

    def test_xml_disagreement_or_entity_stops(self):
        text, xml = metadata()
        changed = xml.replace(L1.encode(), b"LC09_L1TP_141040_20260810_20260812_02_T1")
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_text_xml_identity_disagree"):
            self.inspect(entries(text=text, xml=changed))
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_xml_unsafe_declaration"):
            self.inspect(entries(text=text, xml=b'<!DOCTYPE x [<!ENTITY e "bad">]>' + xml))

    def test_missing_group_and_unknown_identity_path_stop(self):
        text, xml = metadata()
        changed = text.replace(b"GROUP = LEVEL2_PROCESSING_RECORD", b"GROUP = OTHER_PROCESSING_RECORD").replace(b"END_GROUP = LEVEL2_PROCESSING_RECORD", b"END_GROUP = OTHER_PROCESSING_RECORD")
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_required_group_missing_or_duplicate"):
            self.inspect(entries(text=changed, xml=xml))
        extra = text.replace(b"END_GROUP = LANDSAT_METADATA_FILE", b'  LANDSAT_SCENE_ID = "' + SCENE.encode() + b'"\nEND_GROUP = LANDSAT_METADATA_FILE')
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_identity_path_missing_or_unexpected"):
            self.inspect(entries(text=extra, xml=xml))

    def test_duplicate_group_missing_level1_and_malformed_value_stop(self):
        text, xml = metadata()
        group = (b"  GROUP = LEVEL2_PROCESSING_RECORD\n"
                 b'    LANDSAT_PRODUCT_ID = "' + PRODUCT.encode() + b'"\n'
                 b'    PROCESSING_LEVEL = "L2SP"\n'
                 b"  END_GROUP = LEVEL2_PROCESSING_RECORD\n")
        duplicate = text.replace(group, group + group)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_required_group_missing_or_duplicate"):
            self.inspect(entries(text=duplicate, xml=xml))
        missing_l1 = text.replace(b"LEVEL1_PROCESSING_RECORD", b"OTHER_PROCESSING_RECORD")
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_required_group_missing_or_duplicate"):
            self.inspect(entries(text=missing_l1, xml=xml))
        malformed = text.replace(b'LANDSAT_PRODUCT_ID = "' + PRODUCT.encode() + b'"',
                                 b'LANDSAT_PRODUCT_ID = "' + PRODUCT.encode(), 1)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_odl_identity_syntax_invalid"):
            self.inspect(entries(text=malformed, xml=xml))

    def test_unknown_odl_object_construct_stops(self):
        text, xml = metadata()
        changed = text.replace(b"END_GROUP = LANDSAT_METADATA_FILE",
                               b"  OBJECT = UNREVIEWED\n  END_OBJECT = UNREVIEWED\n"
                               b"END_GROUP = LANDSAT_METADATA_FILE")
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_odl_structure_invalid"):
            self.inspect(entries(text=changed, xml=xml))

    def test_unsafe_tar_wrong_product_and_source_drift_still_stop(self):
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "unsafe_archive_member_path"):
            self.inspect(entries() + [("../other", b"x")])
        write_tar(self.path, entries())
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "archive_member_identity_mismatch"):
            MODULE.inspect_bundle(self.path, "LC09_L2SP_141040_20260826_20260827_02_T1", "LC91410402026238LGN00")
        original = MODULE._sha256_file
        calls = 0
        def changing_digest(path):
            nonlocal calls
            calls += 1
            size, digest = original(path)
            return size, digest if calls == 1 else "0" * 64
        with patch.object(MODULE, "_sha256_file", side_effect=changing_digest):
            with self.assertRaisesRegex(MODULE.BundleIntegrityError, "bundle_changed_during_inspection"):
                MODULE.inspect_bundle(self.path, PRODUCT, SCENE)


if __name__ == "__main__":
    unittest.main()
