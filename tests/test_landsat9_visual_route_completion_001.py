import copy
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import landsat9_grouped_visual_metadata_001 as adapter
import run_m2_landsat9_visual_route_completion_001 as completion

PRODUCT = completion.frozen.PRODUCTS["before"][0]
SCENE = completion.frozen.PRODUCTS["before"][1]


def fixture_groups(product=PRODUCT, scene=SCENE):
    l1 = product.replace("_L2SP_", "_L1TP_")
    coefficients = [(f"REFLECTANCE_{kind}_BAND_{band}", str(value))
                    for kind, value in (("MULT", .0000275), ("ADD", -.2)) for band in range(3, 8)]
    return [
        ("PRODUCT_CONTENTS", [("LANDSAT_PRODUCT_ID", product), ("PROCESSING_LEVEL", "L2SP")]),
        ("IMAGE_ATTRIBUTES", [("DATE_ACQUIRED", product.split("_")[3][:4] + "-" + product.split("_")[3][4:6] + "-" + product.split("_")[3][6:]),
                              ("SCENE_CENTER_TIME", "04:35:12.1234560Z")]),
        ("LEVEL2_PROCESSING_RECORD", [("LANDSAT_PRODUCT_ID", product), ("PROCESSING_LEVEL", "L2SP")]),
        ("LEVEL2_SURFACE_REFLECTANCE_PARAMETERS", coefficients),
        ("LEVEL1_PROCESSING_RECORD", [("LANDSAT_PRODUCT_ID", l1), ("LANDSAT_SCENE_ID", scene), ("PROCESSING_LEVEL", "L1TP")]),
        ("LEVEL1_RADIOMETRIC_RESCALING", [(key, "0.000020" if "MULT" in key else "-0.1") for key, _ in coefficients]),
    ]


def fixture_bytes(groups):
    lines = ["GROUP = LANDSAT_METADATA_FILE"]
    xml = ET.Element("LANDSAT_METADATA_FILE")
    for name, fields in groups:
        lines.append("  GROUP = " + name)
        node = ET.SubElement(xml, name)
        for key, value in fields:
            lines.append(f'    {key} = "{value}"')
            ET.SubElement(node, key).text = value
        lines.append("  END_GROUP = " + name)
    lines.extend(("END_GROUP = LANDSAT_METADATA_FILE", "END"))
    return ("\n".join(lines) + "\n").encode(), ET.tostring(xml)


class GroupedVisualMetadataTests(unittest.TestCase):
    def inspect(self, groups=None, text=None, xml=None, product=PRODUCT, scene=SCENE):
        raw = fixture_bytes(groups or fixture_groups(product, scene))
        return adapter.inspect(text if text is not None else raw[0], xml if xml is not None else raw[1], product, scene)

    def test_realistic_repeated_group_names_and_l1_coefficients_select_exact_l2(self):
        result = self.inspect()
        self.assertEqual(result["reflectance_mult"], .0000275)
        self.assertEqual(result["reflectance_add"], -.2)
        self.assertEqual(len(result["validated_coefficients"]), 10)
        self.assertEqual(result["selected_group_paths"][1], "LANDSAT_METADATA_FILE/LEVEL2_SURFACE_REFLECTANCE_PARAMETERS")

    def test_different_date_and_time_in_other_group_are_not_selected(self):
        groups = fixture_groups()
        groups.append(("OTHER_METADATA", [("DATE_ACQUIRED", "2001-01-01"), ("SCENE_CENTER_TIME", "12:01:01Z")]))
        self.assertEqual(self.inspect(groups)["date_acquired"], "2026-08-10")

    def test_missing_or_duplicate_selected_group_rejected_in_both_formats(self):
        for group in ("IMAGE_ATTRIBUTES", "LEVEL2_SURFACE_REFLECTANCE_PARAMETERS"):
            for duplicate in (False, True):
                groups = fixture_groups()
                found = next(g for g in groups if g[0] == group)
                groups = groups + [found] if duplicate else [g for g in groups if g[0] != group]
                with self.subTest(group=group, duplicate=duplicate), self.assertRaisesRegex(adapter.MetadataError, "selected_group"):
                    self.inspect(groups)

    def test_duplicate_selected_field_even_equal_rejected(self):
        for index, key in ((1, "DATE_ACQUIRED"), (3, "REFLECTANCE_MULT_BAND_3")):
            groups = fixture_groups()
            value = next(v for k, v in groups[index][1] if k == key)
            groups[index][1].append((key, value))
            with self.assertRaisesRegex(adapter.MetadataError, "selected_field"):
                self.inspect(groups)

    def test_xml_only_and_odl_only_duplicate_rejected(self):
        valid = fixture_bytes(fixture_groups())
        bad = fixture_groups(); bad[3][1].append(bad[3][1][0])
        duplicate = fixture_bytes(bad)
        for text, xml in ((valid[0], duplicate[1]), (duplicate[0], valid[1])):
            with self.assertRaisesRegex(adapter.MetadataError, "selected_field"):
                self.inspect(text=text, xml=xml)

    def test_missing_selected_field_does_not_fall_back_to_l1(self):
        groups = fixture_groups(); groups[3][1].pop(0)
        with self.assertRaisesRegex(adapter.MetadataError, "selected_field"):
            self.inspect(groups)

    def test_unbalanced_group_missing_end_and_trailing_content_rejected(self):
        text, xml = fixture_bytes(fixture_groups())
        for bad in (text.replace(b"END_GROUP = IMAGE_ATTRIBUTES", b"END_GROUP = OTHER"),
                    text[:-4], text + b"FIELD = 1\n"):
            with self.assertRaises(adapter.identity.BundleIntegrityError):
                self.inspect(text=bad, xml=xml)

    def test_text_xml_disagreement_rejected(self):
        text, xml = fixture_bytes(fixture_groups())
        for bad in (xml.replace(b"04:35:12.1234560Z", b"04:35:13.1234560Z"),
                    xml.replace(b"2.75e-05", b"2.75000001e-05")):
            with self.assertRaisesRegex(adapter.MetadataError, "disagreement"):
                self.inspect(text=text, xml=bad)

    def test_numerical_normalization_accepts_equivalent_scalar(self):
        text, xml = fixture_bytes(fixture_groups())
        self.assertTrue(self.inspect(text=text, xml=xml.replace(b"2.75e-05", b"0.000027500"))["text_xml_selected_values_agree"])

    def test_nonfinite_wrong_scale_and_wrong_date_rejected(self):
        for val in ("NaN", "Infinity", "0.000020", "not-a-number"):
            groups = fixture_groups(); groups[3][1][0] = ("REFLECTANCE_MULT_BAND_3", val)
            with self.subTest(value=val), self.assertRaises(adapter.MetadataError):
                self.inspect(groups)
        groups = fixture_groups(); groups[1][1][0] = ("DATE_ACQUIRED", "2026-08-11")
        with self.assertRaisesRegex(adapter.MetadataError, "date_mismatch"):
            self.inspect(groups)

    def test_wrong_product_scene_and_processing_level_preserve_identity_checks(self):
        for index, position, val in ((0, 0, PRODUCT.replace("20260810", "20260811")),
                                      (4, 1, "LC91410402026223LGN00"), (2, 1, "L1TP")):
            groups = fixture_groups(); key = groups[index][1][position][0]
            groups[index][1][position] = (key, val)
            with self.assertRaises(adapter.identity.BundleIntegrityError):
                self.inspect(groups)

    def test_xml_unsafe_declaration_and_nested_selected_value_rejected(self):
        text, xml = fixture_bytes(fixture_groups())
        with self.assertRaises(adapter.identity.BundleIntegrityError):
            self.inspect(text=text, xml=b'<!DOCTYPE foo [<!ENTITY bar "secret">]>' + xml)
        with self.assertRaisesRegex(adapter.MetadataError, "syntax"):
            self.inspect(text=text, xml=xml.replace(b"<DATE_ACQUIRED>2026-08-10</DATE_ACQUIRED>", b"<DATE_ACQUIRED><VALUE>2026-08-10</VALUE></DATE_ACQUIRED>"))


class CompletionSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.gate = self.root / "gate.json"
        completion.write_new(self.gate, {"status": "pass_final_no_content_preflight",
            "approval_sha256": completion.APPROVAL_SHA, "recovery_approval_sha256": completion.APPROVAL_SHA,
            "recovery_attempt_root_absent": True, "independent_event_roots_absent": True,
            "implementation_hashes": completion.code_hashes(),
            "implementation_public_ci_commit": "a" * 40, "implementation_public_ci_run_id": "12345678"})
        self.calls = 0

    def run_supervisor(self, worker, **kw):
        return completion.supervise(self.gate, attempt=self.root / "attempt", events=self.root / "events",
                                    fallback=self.root / "fallback", worker=worker, **kw)

    def pass_worker(self, gate):
        self.calls += 1
        self.assertTrue((self.root / "events/intent.json").is_file())
        (self.root / "attempt").mkdir()
        completion.write_new(self.root / "attempt/terminal.json", {"status": "pass_pixel_qa_visual_only_no_panel_qualified"})
        return 0

    def test_fixed_supervision_once_and_consumed_attempt_rejected(self):
        result = self.run_supervisor(self.pass_worker)
        self.assertEqual(result["worker_invocations"], 1)
        with self.assertRaises(completion.frozen.RouteStop):
            self.run_supervisor(self.pass_worker)
        self.assertEqual(self.calls, 1)

    def test_unclassified_secret_error_has_no_retry_and_no_exposure(self):
        def fail(gate):
            self.calls += 1
            raise RuntimeError("synthetic_secret_never_publish")
        self.run_supervisor(fail)
        self.assertEqual(self.calls, 1)
        self.assertNotIn("synthetic_secret_never_publish", "".join(p.read_text() for p in self.root.rglob("*.json")))
        self.assertTrue((self.root / "events/cleanup.json").is_file())

    def test_interrupt_before_launch_preserves_evidence_without_content(self):
        def interrupt():
            raise KeyboardInterrupt()
        result = self.run_supervisor(self.pass_worker, after_intent=interrupt)
        self.assertEqual(result["worker_invocations"], 0)
        self.assertFalse((self.root / "attempt").exists())

    def test_binding_restores_frozen_metadata_and_controls(self):
        original = completion.frozen.mtl_fields
        with completion.binding(self.root / "attempt"):
            self.assertIs(completion.frozen.mtl_fields, completion.fields)
            self.assertEqual(completion.frozen.APPROVAL_SHA, completion.APPROVAL_SHA)
        self.assertIs(completion.frozen.mtl_fields, original)

    def test_parent_supervisor_binding_restored(self):
        original = completion.durable.APPROVAL_SHA
        self.run_supervisor(self.pass_worker)
        self.assertEqual(completion.durable.APPROVAL_SHA, original)

    def test_code_drift_stops_before_launch(self):
        gate = json.loads(self.gate.read_text()); gate["implementation_hashes"] = {}
        self.gate.write_text(json.dumps(gate))
        with self.assertRaisesRegex(completion.frozen.RouteStop, "preflight_gate_invalid"):
            self.run_supervisor(self.pass_worker)
        self.assertEqual(self.calls, 0)

    def audit(self, callback):
        gate = json.loads(self.gate.read_text()); gate["attempt_id"] = "real-003"
        self.gate.write_text(json.dumps(gate))
        with patch.object(completion, "AUDIT", self.root / "audit"), \
                patch.object(completion, "AUDIT_FALLBACK", self.root / "audit-fallback"), \
                patch.object(completion, "controls", return_value=None), \
                patch.object(completion, "audit_pair", side_effect=callback):
            return completion.metadata_audit(self.gate)

    def test_metadata_audit_fixed_order_reserved_before_content_and_no_replay(self):
        order = []
        def pair(role):
            self.assertTrue((self.root / "audit/intent.json").is_file())
            order.append(role)
            return {"role": role, "validated_metadata": {"test_only": True}}
        result = self.audit(pair)
        self.assertEqual(result["status"], "pass_exact_two_source_metadata_only")
        self.assertEqual(order, ["before", "after"])
        self.assertFalse(result["tiff_header_or_pixel_read"])
        with self.assertRaises(completion.frozen.RouteStop):
            self.audit(pair)
        self.assertEqual(order, ["before", "after"])

    def test_metadata_audit_failure_stops_before_after_and_preserves_safe_receipt(self):
        order = []
        def fail(role):
            order.append(role)
            raise adapter.MetadataError("mtl_reflectance_scale_mismatch")
        result = self.audit(fail)
        self.assertEqual(order, ["before"])
        self.assertEqual(result["status"], "blocked_metadata_audit")
        self.assertEqual(result["reason"], "mtl_reflectance_scale_mismatch")
        self.assertTrue((self.root / "audit/terminal.json").is_file())
        self.assertTrue((self.root / "audit-fallback/cleanup.json").is_file())


if __name__ == "__main__":
    unittest.main()
