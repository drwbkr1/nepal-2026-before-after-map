from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("mtl_diag", ROOT / "scripts/landsat_l2_mtl_identity_diagnostic_001.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PRODUCT = MODULE.PRODUCT
SCENE = MODULE.SCENE


def entries(text_scene: str = SCENE, xml_scene: str = SCENE):
    return [
        (PRODUCT + "_MTL.txt", f'LANDSAT_PRODUCT_ID = "{PRODUCT}"\nLANDSAT_SCENE_ID = "{text_scene}"\n'.encode()),
        (PRODUCT + "_MTL.xml", f'<x><LANDSAT_PRODUCT_ID>{PRODUCT}</LANDSAT_PRODUCT_ID><LANDSAT_SCENE_ID>{xml_scene}</LANDSAT_SCENE_ID></x>'.encode()),
        (PRODUCT + "_SR_B4.TIF", b"disposable-not-a-tiff"),
    ]


def write_tar(path: Path, members: list[tuple[str, bytes]]) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w") as archive:
        for name, data in members:
            header = tarfile.TarInfo(name)
            header.size = len(data)
            archive.addfile(header, io.BytesIO(data))
    return path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()


class MTLDiagnosticTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "source.tar.part"

    def inspect(self, members=None):
        size, digest = write_tar(self.source, entries() if members is None else members)
        return MODULE.inspect_metadata(self.source, size, digest)

    def test_exact_identity_is_classification_only(self):
        result = self.inspect()
        self.assertEqual(result["status"], "classified_metadata_only")
        self.assertTrue(all(field["exact_expected_match"] for group in result["identity"].values() for field in group.values()))
        self.assertEqual(result["tar_member_count"], 3)

    def test_text_scene_mismatch_preserves_only_valid_identifier(self):
        wrong = "LC91410402026223LGN00"
        result = self.inspect(entries(text_scene=wrong))
        self.assertEqual(result["status"], "identity_discrepancy_classified_source_unaccepted")
        field = result["identity"]["text"]["LANDSAT_SCENE_ID"]
        self.assertEqual(field["allowlisted_values"], [wrong])
        self.assertFalse(field["exact_expected_match"])
        self.assertTrue(result["identity"]["xml"]["LANDSAT_SCENE_ID"]["exact_expected_match"])

    def test_malformed_value_is_never_echoed(self):
        marker = "SECRET_OR_PRIVATE_VALUE"
        result = self.inspect(entries(text_scene=marker))
        self.assertNotIn(marker, json.dumps(result))
        self.assertFalse(result["identity"]["text"]["LANDSAT_SCENE_ID"]["all_syntactically_valid"])

    def test_missing_and_duplicate_key_counts(self):
        members = entries()
        members[0] = (members[0][0], f'LANDSAT_PRODUCT_ID = "{PRODUCT}"\n'.encode())
        result = self.inspect(members)
        self.assertEqual(result["identity"]["text"]["LANDSAT_SCENE_ID"]["presence_count"], 0)
        members[0] = (members[0][0], members[0][1] + f'LANDSAT_SCENE_ID = "{SCENE}"\n' .encode() * 2)
        result = self.inspect(members)
        self.assertEqual(result["identity"]["text"]["LANDSAT_SCENE_ID"]["presence_count"], 2)
        self.assertFalse(result["identity"]["text"]["LANDSAT_SCENE_ID"]["exact_expected_match"])

    def test_no_tiff_payload_read(self):
        size, digest = write_tar(self.source, entries())
        original = tarfile.TarFile.extractfile
        def guarded(archive, member):
            if member.name.endswith(".TIF"):
                raise AssertionError("TIFF payload read")
            return original(archive, member)
        with patch.object(tarfile.TarFile, "extractfile", guarded):
            self.assertEqual(MODULE.inspect_metadata(self.source, size, digest)["status"], "classified_metadata_only")

    def test_unsafe_member_duplicate_and_oversized_mtl_stop(self):
        for members, code in (
            (entries() + [("../bad", b"x")], "unsafe_archive_member_path"),
            (entries() + [(PRODUCT + "/" + PRODUCT + "_MTL.txt", b"x")], "duplicate_mtl_member"),
            ([(PRODUCT + "_MTL.txt", b"x" * (MODULE.MAX_MTL + 1))] + entries()[1:], "mtl_member_size_invalid"),
        ):
            with self.subTest(code=code):
                with self.assertRaisesRegex(MODULE.DiagnosticStop, code):
                    self.inspect(members)

    def test_xml_unsafe_declaration_and_digest_drift_stop(self):
        members = entries()
        members[1] = (members[1][0], b'<!DOCTYPE x [<!ENTITY e "bad">]>' + members[1][1])
        with self.assertRaisesRegex(MODULE.DiagnosticStop, "mtl_xml_unsafe_declaration"):
            self.inspect(members)
        size, digest = write_tar(self.source, entries())
        with self.assertRaisesRegex(MODULE.DiagnosticStop, "source_digest_mismatch"):
            MODULE.inspect_metadata(self.source, size, "0" * 64)

    def test_one_shot_receipts_and_collision(self):
        data = self.root / "data"
        source = data / MODULE.SOURCE_REL
        size, digest = write_tar(source, entries())
        gate = self.root / "gate.json"
        gate.write_text(json.dumps({"status": "pass", "diagnostic_id": MODULE.ATTEMPT_REL.name,
                                    "public_ci_success": True}), encoding="utf-8")
        with patch.object(MODULE, "SOURCE_BYTES", size), patch.object(MODULE, "SOURCE_SHA256", digest):
            result = MODULE.run_once(data, gate)
            self.assertEqual(result["status"], "classified_metadata_only")
            event = data / MODULE.ATTEMPT_REL
            for name in ("reservation.json", "terminal.json", "cleanup.json"):
                self.assertTrue((event / name).is_file())
            before = (event / "terminal.json").read_bytes()
            with self.assertRaises(FileExistsError):
                MODULE.run_once(data, gate)
            self.assertEqual((event / "terminal.json").read_bytes(), before)

    def test_error_receipts_hide_exception_and_cleanup_survives(self):
        data = self.root / "data"
        data.mkdir()
        gate = self.root / "gate.json"
        gate.write_text(json.dumps({"status": "pass", "diagnostic_id": MODULE.ATTEMPT_REL.name,
                                    "public_ci_success": True}), encoding="utf-8")
        with patch.object(MODULE, "inspect_metadata", side_effect=RuntimeError("private-token")):
            result = MODULE.run_once(data, gate)
        event = data / MODULE.ATTEMPT_REL
        self.assertEqual(result["code"], "unexpected_diagnostic_error")
        self.assertNotIn("private-token", (event / "terminal.json").read_text())
        self.assertTrue((event / "cleanup.json").is_file())

    def test_interruption_consumes_identity_with_terminal_and_cleanup(self):
        data = self.root / "data"
        data.mkdir()
        gate = self.root / "gate.json"
        gate.write_text(json.dumps({"status": "pass", "diagnostic_id": MODULE.ATTEMPT_REL.name,
                                    "public_ci_success": True}), encoding="utf-8")
        with patch.object(MODULE, "inspect_metadata", side_effect=KeyboardInterrupt):
            result = MODULE.run_once(data, gate)
        event = data / MODULE.ATTEMPT_REL
        self.assertEqual(result["status"], "terminal_stop")
        self.assertEqual(result["code"], "unexpected_diagnostic_error")
        self.assertTrue((event / "cleanup.json").is_file())

    def test_source_stat_drift_stops_before_metadata(self):
        size, digest = write_tar(self.source, entries())
        original = MODULE.safe_regular
        calls = 0
        def changing(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                os.utime(path, ns=(self.source.stat().st_atime_ns, self.source.stat().st_mtime_ns + 2_000_000_000))
            return original(path)
        with patch.object(MODULE, "safe_regular", side_effect=changing):
            with self.assertRaisesRegex(MODULE.DiagnosticStop, "source_changed_during_hash"):
                MODULE.inspect_metadata(self.source, size, digest)

    def test_gate_and_symlink_stop_without_source_read(self):
        data = self.root / "data"
        data.mkdir()
        gate = self.root / "gate.json"
        gate.write_text('{"status":"block"}', encoding="utf-8")
        with self.assertRaisesRegex(MODULE.DiagnosticStop, "final_preflight_gate_invalid"):
            MODULE.run_once(data, gate)
        self.assertFalse((data / MODULE.ATTEMPT_REL).exists())
        target = self.root / "target"
        target.write_bytes(b"x")
        try:
            self.source.symlink_to(target)
        except OSError:
            self.skipTest("symlinks not permitted")
        with self.assertRaisesRegex(MODULE.DiagnosticStop, "source_reparse_or_symlink"):
            MODULE.inspect_metadata(self.source, 1, hashlib.sha256(b"x").hexdigest())


if __name__ == "__main__":
    unittest.main()
