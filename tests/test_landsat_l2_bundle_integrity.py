from __future__ import annotations

import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "landsat_l2_bundle_integrity", ROOT / "scripts" / "landsat_l2_bundle_integrity.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PRODUCT = "LC09_L2SP_141040_20260810_20260811_02_T1"
SCENE = "LC91410402026222LGN00"


def fixtures(product: str = PRODUCT, scene: str = SCENE) -> list[tuple[str, bytes]]:
    text = (
        f'GROUP = PRODUCT_CONTENTS\n  LANDSAT_PRODUCT_ID = "{product}"\n'
        f'  LANDSAT_SCENE_ID = "{scene}"\nEND_GROUP = PRODUCT_CONTENTS\nEND\n'
    ).encode()
    xml = (
        f"<LANDSAT_METADATA_FILE><PRODUCT_CONTENTS>"
        f"<LANDSAT_PRODUCT_ID>{product}</LANDSAT_PRODUCT_ID>"
        f"</PRODUCT_CONTENTS><LEVEL1_PROCESSING_RECORD>"
        f"<LANDSAT_SCENE_ID>{scene}</LANDSAT_SCENE_ID>"
        f"</LEVEL1_PROCESSING_RECORD></LANDSAT_METADATA_FILE>"
    ).encode()
    return [
        (product + suffix, text if suffix == "_MTL.txt" else xml if suffix == "_MTL.xml" else b"synthetic-not-a-tiff")
        for suffix in MODULE.REQUIRED_SUFFIXES
    ]


def write_tar(path: Path, entries: list[tuple[str, bytes]], special: tarfile.TarInfo | None = None) -> None:
    with tarfile.open(path, "w") as archive:
        for name, content in entries:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
        if special is not None:
            archive.addfile(special)


class LandsatL2BundleIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "synthetic.tar"

    def test_exact_bundle_passes_container_and_identity_only(self) -> None:
        write_tar(self.path, fixtures())
        result = MODULE.inspect_bundle(self.path, PRODUCT, SCENE)
        self.assertEqual(result["status"], "pass_container_and_mtl_identity_only")
        self.assertEqual(result["member_count"], len(MODULE.REQUIRED_SUFFIXES))
        self.assertEqual(result["archive_size_bytes"], self.path.stat().st_size)
        self.assertEqual(len(result["archive_sha256"]), 64)
        self.assertTrue(all(len(member["sha256"]) == 64 for member in result["members"]))
        self.assertIn("No TIFF header, CRS, pixel, AOI, registration, or change check was performed.", result["limitations"])

    def test_mtl_text_or_xml_identity_drift_fails(self) -> None:
        for suffix in ("_MTL.txt", "_MTL.xml"):
            with self.subTest(suffix=suffix):
                entries = fixtures()
                index = next(i for i, (name, _) in enumerate(entries) if name.endswith(suffix))
                entries[index] = (entries[index][0], entries[index][1].replace(SCENE.encode(), b"WRONG-SCENE"))
                write_tar(self.path, entries)
                with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_.*_identity_mismatch"):
                    MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_missing_required_member_fails(self) -> None:
        write_tar(self.path, [(name, data) for name, data in fixtures() if not name.endswith("_SR_B7.TIF")])
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "required_archive_member_missing"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_empty_required_member_fails_without_reading_pixels(self) -> None:
        entries = [
            (name, b"" if name.endswith("_SR_B7.TIF") else data)
            for name, data in fixtures()
        ]
        write_tar(self.path, entries)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "required_archive_member_empty"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_traversal_link_and_duplicate_are_rejected(self) -> None:
        traversal = fixtures() + [("../" + PRODUCT + "_ST_B10.TIF", b"x")]
        write_tar(self.path, traversal)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "unsafe_archive_member_path"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

        link = tarfile.TarInfo(PRODUCT + "_ST_B10.TIF")
        link.type = tarfile.SYMTYPE
        link.linkname = "outside"
        write_tar(self.path, fixtures(), special=link)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "unsafe_archive_member_type"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

        write_tar(self.path, fixtures() + [(PRODUCT + "_MTL.txt", b"duplicate")])
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "duplicate_archive_member"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_other_product_member_and_missing_tar_end_are_rejected(self) -> None:
        wrong = fixtures() + [("LC09_L2SP_141040_20260826_20260827_02_T1_SR_B3.TIF", b"x")]
        write_tar(self.path, wrong)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "archive_member_identity_mismatch"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

        write_tar(self.path, fixtures())
        self.path.write_bytes(self.path.read_bytes()[:-1] + b"x")
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "tar_end_marker_missing"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_hidden_payload_after_tar_end_is_rejected(self) -> None:
        write_tar(self.path, fixtures())
        content = self.path.read_bytes()
        self.path.write_bytes(content + b"hidden" + b"\0" * (512 - 6) + b"\0" * 1024)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "tar_trailing_payload_invalid"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_same_required_basename_in_flat_and_rooted_forms_is_rejected(self) -> None:
        write_tar(self.path, fixtures() + [(PRODUCT + "/" + PRODUCT + "_MTL.txt", b"other")])
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "duplicate_archive_basename"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)

    def test_xml_entity_declaration_is_rejected(self) -> None:
        entries = fixtures()
        index = next(i for i, (name, _) in enumerate(entries) if name.endswith("_MTL.xml"))
        entries[index] = (entries[index][0], b'<!DOCTYPE x [<!ENTITY e "bad">]>' + entries[index][1])
        write_tar(self.path, entries)
        with self.assertRaisesRegex(MODULE.BundleIntegrityError, "mtl_xml_unsafe_declaration"):
            MODULE.inspect_bundle(self.path, PRODUCT, SCENE)


if __name__ == "__main__":
    unittest.main()
